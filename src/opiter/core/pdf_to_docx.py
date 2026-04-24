"""PDF → DOCX conversion via ``pdf2docx`` (pure-Python, PyMuPDF-based)."""
from __future__ import annotations

from pathlib import Path


def pdf_to_docx(pdf_path: str | Path, docx_path: str | Path) -> Path:
    """Convert the PDF at *pdf_path* to a DOCX file at *docx_path*.

    Returns the output path. Raises any exception from ``pdf2docx``
    (most commonly: unreadable/encrypted PDFs).
    """
    from pdf2docx import Converter

    pdf = Path(pdf_path)
    out = Path(docx_path)
    cv = Converter(str(pdf))
    try:
        cv.convert(str(out))
    finally:
        cv.close()
    return out
