from __future__ import annotations

import base64
import fitz  # PyMuPDF


def page_to_base64(pdf_path: str, page_index: int, dpi: int = 200) -> str:
    """
    Render a PDF page to PNG and return base64 encoding.
    """
    doc = fitz.open(pdf_path)
    try:
        page = doc.load_page(page_index)
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")
        return base64.b64encode(img_bytes).decode("utf-8")
    finally:
        doc.close()


