"""Tests for opiter.core.document."""
from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from opiter.core.document import Document
from opiter.utils.errors import CorruptedPDFError


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """Generate a 3-page PDF in tmp_path and return its path."""
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page()
        page.insert_text((50, 100), f"Sample page {i + 1}", fontsize=24)
    out = tmp_path / "sample.pdf"
    doc.save(out)
    doc.close()
    return out


def test_open_valid_pdf_reports_page_count(sample_pdf: Path) -> None:
    with Document.open(sample_pdf) as doc:
        assert doc.page_count == 3


def test_open_missing_file_raises_corrupted(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist.pdf"
    with pytest.raises(CorruptedPDFError):
        Document.open(missing)


def test_open_garbage_file_raises_corrupted(tmp_path: Path) -> None:
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"not a pdf")
    with pytest.raises(CorruptedPDFError):
        Document.open(bad)


def test_page_index_bounds(sample_pdf: Path) -> None:
    with Document.open(sample_pdf) as doc:
        doc.page(0)
        doc.page(2)
        with pytest.raises(IndexError):
            doc.page(3)
        with pytest.raises(IndexError):
            doc.page(-1)


def test_page_size_returns_width_and_height(tmp_path: Path) -> None:
    doc = fitz.open()
    doc.new_page(width=612, height=792)  # US Letter
    out = tmp_path / "letter.pdf"
    doc.save(out)
    doc.close()
    with Document.open(out) as d:
        w, h = d.page_size(0)
        assert w == 612
        assert h == 792
