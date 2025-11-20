"""
Helpers to generate LLM-ready block payloads with the desired context pages.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Sequence, Tuple, Set

from solution.config import ALLOWED_LABELS, BLOCK_SIZE, CONTEXT_PAGES
from solution.page_info import PageInfo


class BlockBuilder:
    """Builds classification blocks optimized for the iterative strategy."""

    def __init__(self, block_size: int = BLOCK_SIZE, context_pages: int = CONTEXT_PAGES):
        self.block_size = max(1, block_size)
        self.context_pages = max(0, context_pages)

    def build_initial_blocks(self, pages: Sequence[PageInfo]) -> List[Dict]:
        """First pass — split pages into fixed-size chunks."""
        target_indices = [page.index for page in pages if not page.is_final]
        ranges = self._contiguous_ranges(target_indices)
        return self._build_blocks_from_ranges(pages, ranges)

    def build_label_blocks(self, pages: Sequence[PageInfo]) -> List[Dict]:
        """Subsequent passes — group by existing labels."""
        ranges: List[Tuple[int, int]] = []
        i = 0
        total_pages = len(pages)

        while i < total_pages:
            page = pages[i]
            if page.is_final:
                i += 1
                continue

            label = page.label
            start = i
            i += 1
            while i < total_pages:
                next_page = pages[i]
                if next_page.is_final or next_page.label != label:
                    break
                i += 1
            end = i - 1
            ranges.append((start, end))

        return self._build_blocks_from_ranges(pages, ranges)

    def build_label_blocks_excluding(self, pages: Sequence[PageInfo], exclude_indices: Set[int]) -> List[Dict]:
        """Like build_label_blocks, but skip pages whose indices are in exclude_indices."""
        ranges: List[Tuple[int, int]] = []
        i = 0
        total_pages = len(pages)

        while i < total_pages:
            page = pages[i]
            if page.is_final or page.index in exclude_indices:
                i += 1
                continue

            label = page.label
            start = i
            i += 1
            while i < total_pages:
                next_page = pages[i]
                if next_page.is_final or next_page.index in exclude_indices or next_page.label != label:
                    break
                i += 1
            end = i - 1
            ranges.append((start, end))

        return self._build_blocks_from_ranges(pages, ranges)

    def build_single_page_block(self, pages: Sequence[PageInfo], page_index: int) -> Dict:
        """Build a block targeting exactly one page with surrounding context."""
        return self._build_block_payload(pages, page_index, page_index)

    def _build_blocks_from_ranges(
        self,
        pages: Sequence[PageInfo],
        ranges: Iterable[Tuple[int, int]],
    ) -> List[Dict]:
        blocks: List[Dict] = []
        for start, end in ranges:
            chunk_start = start
            while chunk_start <= end:
                chunk_end = min(chunk_start + self.block_size - 1, end)
                block = self._build_block_payload(pages, chunk_start, chunk_end)
                if block:
                    blocks.append(block)
                chunk_start = chunk_end + 1
        return blocks

    def _build_block_payload(
        self, pages: Sequence[PageInfo], target_start: int, target_end: int
    ) -> Dict:
        target_start = max(0, target_start)
        target_end = min(len(pages) - 1, target_end)
        if target_start > target_end:
            return {}

        context_start = max(0, target_start - self.context_pages)
        context_end = min(len(pages), target_end + self.context_pages + 1)

        pages_payload = []
        for idx in range(context_start, context_end):
            page = pages[idx]
            is_target = target_start <= idx <= target_end and not page.is_final
            pages_payload.append(page.to_block_entry(is_target=is_target))

        if not any(entry["isTarget"] for entry in pages_payload):
            return {}

        return {
            "targetInterval": {
                "startPageIndex": target_start,
                "endPageIndex": target_end,
            },
            "pages": pages_payload,
            "allowedLabels": ALLOWED_LABELS,
        }

    @staticmethod
    def _contiguous_ranges(indices: Sequence[int]) -> List[Tuple[int, int]]:
        if not indices:
            return []
        sorted_indices = sorted(indices)
        ranges: List[Tuple[int, int]] = []
        start = sorted_indices[0]
        prev = start
        for idx in sorted_indices[1:]:
            if idx == prev + 1:
                prev = idx
                continue
            ranges.append((start, prev))
            start = idx
            prev = idx
        ranges.append((start, prev))
        return ranges


