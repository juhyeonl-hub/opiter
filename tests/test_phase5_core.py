"""Tests for Phase 5 core conversion modules (pdf_to_docx, pdf_to_hwp)."""
from __future__ import annotations

from pathlib import Path

import fitz
import pytest


@pytest.fixture
def small_pdf(tmp_path: Path) -> Path:
    d = fitz.open()
    for i in range(2):
        p = d.new_page(width=400, height=500)
        p.insert_text((50, 100), f"Phase5 page {i + 1} content", fontsize=14)
    out = tmp_path / "src.pdf"
    d.save(out)
    d.close()
    return out


# ----------------------------------------------------------- pdf → docx
def test_pdf_to_docx_produces_readable_docx(small_pdf: Path, tmp_path: Path) -> None:
    from opiter.core.pdf_to_docx import pdf_to_docx

    out = tmp_path / "out.docx"
    pdf_to_docx(small_pdf, out)
    assert out.exists()
    assert out.stat().st_size > 500  # non-trivial

    # Verify it's a valid docx — python-docx must open it and read paragraphs.
    from docx import Document as DocxDocument

    doc = DocxDocument(str(out))
    all_text = "\n".join(p.text for p in doc.paragraphs)
    assert "Phase5" in all_text
    assert "page" in all_text.lower()


# ----------------------------------------------------------- pdf → hwp
def test_hwp_availability_check_is_boolean(tmp_path: Path) -> None:
    from opiter.core.pdf_to_hwp import hwp_conversion_available

    # The function is defined and returns a bool either way.
    assert isinstance(hwp_conversion_available(), bool)


def test_pdf_to_hwp_raises_when_soffice_missing(
    small_pdf: Path, tmp_path: Path, monkeypatch
) -> None:
    """If soffice is not on PATH the helper raises RuntimeError before any
    conversion begins."""
    from opiter.core import pdf_to_hwp as mod

    monkeypatch.setattr(mod, "_soffice_binary", lambda: None)
    with pytest.raises(RuntimeError):
        mod.pdf_to_hwp(small_pdf, tmp_path / "out.hwp")
