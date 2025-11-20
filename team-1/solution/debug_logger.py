"""
Utility for dumping detailed debugging information about classification passes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple


class DebugLogger:
    """Emits verbose classification traces to stdout and (optionally) a log file."""

    def __init__(self, log_path: Optional[str] = None, enabled: bool = True):
        self.enabled = enabled
        self.path = Path(log_path) if log_path else None
        if self.enabled and self.path:
            self.reset()

    def reset(self) -> None:
        if not self.enabled or not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("", encoding="utf-8")

    def log_pass_blocks(self, iteration: int, blocks: List[Dict]) -> None:
        if not self.enabled:
            return
        lines = [f"######## PASS {iteration} ########"]
        for idx, block in enumerate(blocks, 1):
            context_start, context_end = self._context_span(block)
            target_interval = block.get("targetInterval", {})
            start_idx = target_interval.get("startPageIndex")
            end_idx = target_interval.get("endPageIndex")
            suffix = ""
            if block.get("engine") == "vision":
                suffix = " VISION"
            lines.append(
                f"- Block {idx}: Context ({context_start} - {context_end}) "
                f"Target ({start_idx} - {end_idx}){suffix}"
            )
        lines.append("")
        self._write("\n".join(lines) + "\n")

    def log_block_predictions(self, block: Dict, predictions: List[Dict]) -> None:
        if not self.enabled:
            return
        context_start, context_end = self._context_span(block)
        target_interval = block.get("targetInterval", {})
        start_idx = target_interval.get("startPageIndex")
        end_idx = target_interval.get("endPageIndex")

        lines = [
            "=" * 43,
            f"Contexte ({context_start} - {context_end})",
            f"Bloc ({start_idx} - {end_idx})",
            "",
        ]

        for prediction in sorted(predictions, key=lambda x: x.get("pageIndex", 0)):
            page_idx = prediction.get("pageIndex")
            label = prediction.get("label", "UNKNOWN")
            confidence = prediction.get("confidencePercent")
            confidence_str = "UNKNOWN" if confidence is None else f"{float(confidence):.2f}"
            lines.append(f"Page {page_idx} : Label : {label} --- Confidence : {confidence_str}")

        lines.append("")
        lines.append("=" * 43)
        lines.append("")
        self._write("\n".join(lines) + "\n")

    def log_vision_block_result(self, block: Dict, reasons: List[str], page_index: int, label: str, confidence: float) -> None:
        if not self.enabled:
            return
        context_start, context_end = self._context_span(block)
        target_interval = block.get("targetInterval", {})
        start_idx = target_interval.get("startPageIndex")
        end_idx = target_interval.get("endPageIndex")

        lines = [
            "=" * 43,
            f"Contexte ({context_start} - {context_end})",
            f"Bloc ({start_idx} - {end_idx})",
            "",
            "USED VISION",
            f"Reason : {', '.join(reasons) if reasons else 'N/A'}",
            "",
            f"Page {page_index} : Label : {label} --- Confidence : {float(confidence):.2f}",
            "",
            "=" * 43,
            "",
        ]
        self._write("\n".join(lines) + "\n")

    def _context_span(self, block: Dict) -> Tuple[Optional[int], Optional[int]]:
        pages = block.get("pages") or []
        if not pages:
            return None, None
        start = pages[0].get("pageIndex")
        end = pages[-1].get("pageIndex")
        return start, end

    def _write(self, text: str) -> None:
        if not self.enabled:
            return
        print(text, end="", flush=True)
        if self.path:
            with self.path.open("a", encoding="utf-8") as file:
                file.write(text)


