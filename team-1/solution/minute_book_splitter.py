"""
High-level orchestrator that ties together extraction, classification and output writing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from solution.block_builder import BlockBuilder
from solution.llm_client import LLMClient
from solution.page_classifier import PageClassifier
from solution.pdf_text_extractor import PDFTextExtractor
from solution.section_aggregator import SectionAggregator


class MinuteBookSplitter:
    """End-to-end splitter that produces the final sections JSON file."""

    def __init__(
        self,
        extractor: PDFTextExtractor,
        block_builder: BlockBuilder,
        llm_client: LLMClient,
        classifier: PageClassifier,
        aggregator: SectionAggregator,
    ):
        self.extractor = extractor
        self.block_builder = block_builder
        self.llm_client = llm_client
        self.classifier = classifier
        self.aggregator = aggregator

    def run(self, pdf_path: str, output_path: str) -> Dict:
        pages = self.extractor.extract(pdf_path)
        if not pages:
            raise ValueError("No pages extracted from PDF.")

        # Iterative classification now internally handles vision blocks in later passes
        self.classifier.run_classification(pages, pdf_path=pdf_path)
        sections = self.aggregator.aggregate(pages)
        self._write_output(output_path, sections)

        return {
            "totalPages": len(pages),
            "sections": sections,
            "requests": self.llm_client.request_count,
        }

    @staticmethod
    def _write_output(output_path: str, sections: List[dict]) -> None:
        payload = {"sections": sections}
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


