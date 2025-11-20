from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Sequence, Tuple

from solution.block_builder import BlockBuilder
from solution.config import (
    CONFIDENCE_FINAL_THRESHOLD,
    MAX_ITERATIONS,
    OCR_QUALITY_THRESHOLD,
    VISION_LOW_CONFIDENCE,
    VISION_MAX_PAGES,
    ALLOWED_LABELS,
    MAX_PARALLEL_REQUESTS,
)
from solution.debug_logger import DebugLogger
from solution.llm_client import LLMClient, LLMClientError
from solution.page_info import PageInfo
from solution.vision_client import VisionClient, VisionClientError
from solution.pdf_image_renderer import page_to_base64


def _normalize_label_text(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


_ALLOWED_LABEL_SET = set(ALLOWED_LABELS)
_NORMALIZED_ALLOWED_LABELS = [
    (label, _normalize_label_text(label)) for label in ALLOWED_LABELS
]


class PageClassifier:
    """Runs multi-iteration classification until all pages are finalized or max iterations reached."""

    def __init__(
        self,
        block_builder: BlockBuilder,
        llm_client: LLMClient,
        vision_client: Optional[VisionClient] = None,
        max_iterations: int = MAX_ITERATIONS,
        final_threshold: float = CONFIDENCE_FINAL_THRESHOLD,
        max_parallel_requests: int = MAX_PARALLEL_REQUESTS,
        debug_logger: Optional[DebugLogger] = None,
    ):
        self.block_builder = block_builder
        self.llm_client = llm_client
        self.vision_client = vision_client
        self.max_iterations = max(1, max_iterations)
        self.final_threshold = final_threshold
        self.max_parallel_requests = max(1, max_parallel_requests)
        self.debug_logger = debug_logger

    def run_classification(self, pages: Sequence[PageInfo], pdf_path: Optional[str] = None) -> None:
        iteration = 0
        while iteration < self.max_iterations:
            pending = [page for page in pages if not page.is_final]
            if not pending:
                break

            if iteration == 0:
                # First pass
                blocks = self.block_builder.build_initial_blocks(pages)
                for b in blocks:
                    b["engine"] = "ask"
            else:
                # Subsequent passes
                reasons_map: Dict[int, List[str]] = {}
                for p in pages:
                    if p.is_final:
                        continue
                    reasons: List[str] = []
                    if p.needs_vision:
                        reasons.append("incoherent_by_llm=true")
                    if p.ocr_quality < OCR_QUALITY_THRESHOLD:
                        reasons.append(f"low_quality={p.ocr_quality:.1f}<{OCR_QUALITY_THRESHOLD:.1f}")
                    if p.confidence < VISION_LOW_CONFIDENCE:
                        reasons.append(f"low_confidence={p.confidence:.1f}<{VISION_LOW_CONFIDENCE:.1f}")
                    if reasons:
                        reasons_map[p.index] = reasons

                vision_indices = list(reasons_map.keys())[: max(0, VISION_MAX_PAGES)]
                vision_blocks = []
                for idx in vision_indices:
                    vb = self.block_builder.build_single_page_block(pages, idx)
                    if vb:
                        vb["engine"] = "vision"
                        vb["visionReasons"] = reasons_map.get(idx, [])
                        vision_blocks.append(vb)

                ask_blocks = self.block_builder.build_label_blocks_excluding(pages, set(vision_indices))
                for b in ask_blocks:
                    b["engine"] = "ask"

                blocks = ask_blocks + vision_blocks

            if not blocks:
                break

            if self.debug_logger:
                self.debug_logger.log_pass_blocks(iteration + 1, blocks)

            self._execute_blocks(blocks, pages, pdf_path)

            iteration += 1

    def _execute_blocks(
        self,
        blocks: Sequence[Dict],
        pages: Sequence[PageInfo],
        pdf_path: Optional[str],
    ) -> None:
        if not blocks:
            return

        results: List[Tuple[int, Dict, List[Dict], Optional[Dict]]] = []
        if self.max_parallel_requests <= 1 or len(blocks) == 1:
            for order, block in enumerate(blocks):
                result = self._process_block(block, pdf_path, order)
                if result:
                    results.append(result)
        else:
            max_workers = min(self.max_parallel_requests, len(blocks))
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [
                    executor.submit(self._process_block, block, pdf_path, order)
                    for order, block in enumerate(blocks)
                ]
                for future in as_completed(futures):
                    try:
                        result = future.result()
                    except Exception as exc:  # pragma: no cover - defensive guard
                        print(f"[WARN] Block classification task failed: {exc}")
                        continue
                    if result:
                        results.append(result)

        for _, block, predictions, vision_meta in sorted(results, key=lambda entry: entry[0]):
            if not predictions:
                continue
            engine = block.get("engine", "ask")
            if engine == "vision" and vision_meta:
                idx = vision_meta.get("pageIndex")
                if isinstance(idx, int) and 0 <= idx < len(pages):
                    try:
                        pages[idx].needs_vision = False
                    except Exception:
                        pass
                if self.debug_logger:
                    self.debug_logger.log_vision_block_result(
                        block,
                        block.get("visionReasons") or [],
                        idx,
                        vision_meta.get("label") or "UNKNOWN",
                        float(vision_meta.get("confidence") or 0.0),
                    )
            else:
                if self.debug_logger:
                    self.debug_logger.log_block_predictions(block, predictions)
            self._apply_predictions(pages, predictions)

    def _process_block(
        self,
        block: Dict,
        pdf_path: Optional[str],
        order: int,
    ) -> Optional[Tuple[int, Dict, List[Dict], Optional[Dict]]]:
        engine = block.get("engine", "ask")
        if engine == "vision":
            if not self.vision_client or not pdf_path:
                print("[WARN] Vision block encountered but vision client or pdf_path missing; skipping.")
                return None
            target = block.get("targetInterval") or {}
            start_idx = target.get("startPageIndex")
            if not isinstance(start_idx, (int, str)):
                print("[WARN] Vision block missing startPageIndex; skipping.")
                return None
            try:
                idx = int(start_idx)
            except (TypeError, ValueError):
                print("[WARN] Vision block has invalid startPageIndex; skipping.")
                return None

            try:
                img_b64 = page_to_base64(pdf_path, idx)
                result = self.vision_client.classify_page_image(img_b64)
                label = result.get("label")
                conf = float(result.get("confidencePercent", 0))
                predictions = [
                    {"pageIndex": idx, "label": label, "confidencePercent": conf}
                ]
                meta = {"pageIndex": idx, "label": label, "confidence": conf}
                return order, block, predictions, meta
            except (VisionClientError, Exception) as exc:
                print(f"[WARN] Vision classification failed for page {idx}: {exc}")
                return None

        predictions = None
        for attempt in range(2):
            try:
                predictions = self.llm_client.classify_block(block)
                break
            except LLMClientError as exc:
                if attempt == 0:
                    print(
                        f"[WARN] Failed to classify block {block.get('targetInterval')} (retrying): {exc}"
                    )
                    continue
                print(
                    f"[WARN] Failed to classify block {block.get('targetInterval')}: {exc}"
                )
                break

        if not predictions:
            return None

        return order, block, predictions, None

    def _apply_predictions(self, pages: Sequence[PageInfo], predictions: List[dict]) -> None:
        for prediction in predictions:
            page_index = prediction.get("pageIndex")
            label = prediction.get("label")
            confidence = float(prediction.get("confidencePercent", 0))
            incoherent = bool(prediction.get("isTextIncoherent", False))

            if page_index is None or not (0 <= page_index < len(pages)):
                continue

            canonical_label = self._canonicalize_label(label)
            if not canonical_label:
                print(
                    f"[WARN] Page {page_index + 1}: Ignoring unsupported label '{label}'."
                )
                continue

            page = pages[page_index]
            if incoherent:
                if not page.needs_vision:
                    print(f"[INFO] Page {page_index + 1}: LLM flagged text as incoherent — scheduling vision fallback.")
                page.needs_vision = True
            if page.is_final and confidence <= page.confidence:
                continue

            page.label = canonical_label
            page.confidence = confidence
            if confidence >= self.final_threshold:
                page.is_final = True
                page.needs_vision = False

    @staticmethod
    def _canonicalize_label(label: Optional[str]) -> Optional[str]:
        if not label:
            return None

        trimmed = label.strip()
        if trimmed in _ALLOWED_LABEL_SET:
            return trimmed

        normalized = _normalize_label_text(trimmed)
        if not normalized:
            return None

        for allowed, allowed_norm in _NORMALIZED_ALLOWED_LABELS:
            if allowed_norm and allowed_norm in normalized:
                return allowed

        return None


