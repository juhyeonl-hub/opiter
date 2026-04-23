"""Tests for opiter.core.renderer."""
from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from opiter.core.document import Document
from opiter.core.renderer import render_page


@pytest.fixture
def letter_pdf(tmp_path: Path) -> Path:
    """Generate a 1-page US Letter PDF (612x792 pts)."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((50, 100), "Render test", fontsize=24)
    out = tmp_path / "letter.pdf"
    doc.save(out)
    doc.close()
    return out


def test_render_at_unit_zoom_matches_page_dimensions(letter_pdf: Path) -> None:
    with Document.open(letter_pdf) as doc:
        rp = render_page(doc, 0, zoom=1.0)
        assert rp.width == 612
        assert rp.height == 792
        assert len(rp.samples) == rp.stride * rp.height
        assert rp.has_alpha is False


def test_render_at_2x_zoom_doubles_dimensions(letter_pdf: Path) -> None:
    with Document.open(letter_pdf) as doc:
        rp = render_page(doc, 0, zoom=2.0)
        assert rp.width == 1224
        assert rp.height == 1584


def test_render_invalid_index_raises(letter_pdf: Path) -> None:
    with Document.open(letter_pdf) as doc:
        with pytest.raises(IndexError):
            render_page(doc, 5)
