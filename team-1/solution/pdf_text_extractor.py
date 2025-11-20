from __future__ import annotations

from typing import List

import fitz  # PyMuPDF

from solution.page_info import PageInfo


class PDFTextExtractor:
    """Extracts raw text from each PDF page."""

    def extract(self, pdf_path: str) -> List[PageInfo]:
        """
        Convert every page of the PDF into a PageInfo instance.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            List of PageInfo ordered by page index.
        """
        doc = fitz.open(pdf_path)
        try:
            pages: List[PageInfo] = []
            for index in range(doc.page_count):
                page = doc.load_page(index)
                text = page.get_text().strip()
                # Heuristic OCR sanity check to decide on potential vision fallback
                from solution.ocr_quality import needs_vision_fallback
                needs_vision, quality = needs_vision_fallback(text)
                pages.append(PageInfo(index=index, text=text, ocr_quality=quality, needs_vision=needs_vision))
            return pages
        finally:
            doc.close()


