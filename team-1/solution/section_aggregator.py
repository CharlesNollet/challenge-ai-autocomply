from __future__ import annotations

from typing import List, Sequence

from solution.page_info import PageInfo


class SectionAggregator:
    """Aggregates consecutive pages with the same label into sections."""

    def aggregate(self, pages: Sequence[PageInfo]) -> List[dict]:
        sections: List[dict] = []
        current_label = None
        start_index = None

        for page in pages:
            if not page.label:
                if current_label is not None:
                    sections.append(self._section_dict(current_label, start_index, page.index - 1))
                    current_label = None
                    start_index = None
                continue

            if current_label is None:
                current_label = page.label
                start_index = page.index
                continue

            if page.label != current_label:
                sections.append(self._section_dict(current_label, start_index, page.index - 1))
                current_label = page.label
                start_index = page.index

        if current_label is not None and start_index is not None:
            sections.append(self._section_dict(current_label, start_index, pages[-1].index))

        return sections

    @staticmethod
    def _section_dict(label: str, start_index: int, end_index: int) -> dict:
        return {
            "name": label,
            "startPage": start_index + 1,
            "endPage": end_index + 1,
        }


