"""
Data structure representing a single PDF page within the classification pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class PageInfo:
    """Holds extracted text, labels and metadata for a page."""

    index: int
    text: str
    label: Optional[str] = None
    confidence: float = 0.0
    is_final: bool = False
    ocr_quality: float = 0.0
    needs_vision: bool = False

    def to_block_entry(self, is_target: bool) -> dict:
        """
        Represent the page in the structure expected by the LLM prompt.

        Args:
            is_target: Whether this page must be labeled in the current block.

        Returns:
            A dictionary compatible with the prompt schema.
        """
        return {
            "pageIndex": self.index,
            "isTarget": is_target,
            "isFinal": self.is_final,
            "text": self.text or "",
            "finalLabel": self.label if self.is_final and self.label else None,
        }


