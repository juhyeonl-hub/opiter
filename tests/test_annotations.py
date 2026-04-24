"""Tests for opiter.core.annotations."""
from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from opiter.core import annotations as anno
from opiter.core.document import Document


@pytest.fixture
def text_pdf(tmp_path: Path) -> Path:
    """1-page PDF with a known text layout for find_words_in_rect tests."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((50, 100), "Hello world test page", fontsize=14)
    out = tmp_path / "text.pdf"
    doc.save(out)
    doc.close()
    return out


@pytest.fixture
def blank_pdf(tmp_path: Path) -> Path:
    """1-page blank PDF (no text)."""
    doc = fitz.open()
    doc.new_page(width=612, height=792)
    out = tmp_path / "blank.pdf"
    doc.save(out)
    doc.close()
    return out


# --------------------------------------------------------------- find words
def test_find_words_returns_intersecting_words(text_pdf: Path) -> None:
    """A rect covering the whole top of the page should find the inserted text."""
    with Document.open(text_pdf) as doc:
        # Inserted text at (50, 100). PyMuPDF's text origin is the baseline,
        # so the actual word rects sit slightly above and below y=100.
        rects = anno.find_words_in_rect(doc, 0, (40, 80, 300, 120))
    assert len(rects) >= 1


def test_find_words_returns_empty_for_no_overlap(text_pdf: Path) -> None:
    with Document.open(text_pdf) as doc:
        rects = anno.find_words_in_rect(doc, 0, (0, 700, 100, 750))
    assert rects == []


# ------------------------------------------------------------------ highlight
def test_add_highlight_marks_modified_and_persists(text_pdf: Path) -> None:
    with Document.open(text_pdf) as doc:
        rects = anno.find_words_in_rect(doc, 0, (40, 80, 300, 120))
        anno.add_highlight(doc, 0, rects)
        assert doc.is_modified is True
        assert anno.annotation_count(doc, 0) == 1
        doc.save()

    with Document.open(text_pdf) as reopened:
        assert anno.annotation_count(reopened, 0) == 1
        page = reopened.page(0)
        annot = next(page.annots())
        assert annot.type[1] == "Highlight"


def test_add_underline_writes_underline_annot(text_pdf: Path) -> None:
    with Document.open(text_pdf) as doc:
        rects = anno.find_words_in_rect(doc, 0, (40, 80, 300, 120))
        anno.add_underline(doc, 0, rects)
        page = doc.page(0)
        annot = next(page.annots())
        assert annot.type[1] == "Underline"


def test_add_strikeout_writes_strikeout_annot(text_pdf: Path) -> None:
    with Document.open(text_pdf) as doc:
        rects = anno.find_words_in_rect(doc, 0, (40, 80, 300, 120))
        anno.add_strikeout(doc, 0, rects)
        page = doc.page(0)
        annot = next(page.annots())
        assert annot.type[1] == "StrikeOut"


# ------------------------------------------------------------------ note
def test_add_sticky_note_persists(blank_pdf: Path) -> None:
    with Document.open(blank_pdf) as doc:
        anno.add_sticky_note(doc, 0, (100.0, 100.0), "Hello!")
        doc.save()

    with Document.open(blank_pdf) as reopened:
        assert anno.annotation_count(reopened, 0) == 1
        page = reopened.page(0)
        annot = next(page.annots())
        assert annot.type[1] == "Text"  # sticky note is "Text" annot type
        assert "Hello" in annot.info.get("content", "")


# ------------------------------------------------------------------ ink
def test_add_ink_persists_with_stroke(blank_pdf: Path) -> None:
    stroke = [(100.0, 100.0), (110.0, 110.0), (120.0, 105.0), (130.0, 120.0)]
    with Document.open(blank_pdf) as doc:
        anno.add_ink(doc, 0, [stroke])
        doc.save()

    with Document.open(blank_pdf) as reopened:
        assert anno.annotation_count(reopened, 0) == 1
        page = reopened.page(0)
        annot = next(page.annots())
        assert annot.type[1] == "Ink"


# ------------------------------------------------------------------ shapes
def test_add_rect_persists(blank_pdf: Path) -> None:
    with Document.open(blank_pdf) as doc:
        anno.add_rect(doc, 0, (50, 50, 200, 200))
        doc.save()
    with Document.open(blank_pdf) as r:
        page = r.page(0)
        annot = next(page.annots())
        assert annot.type[1] == "Square"  # PDF rect = "Square" annot type


def test_add_ellipse_persists(blank_pdf: Path) -> None:
    with Document.open(blank_pdf) as doc:
        anno.add_ellipse(doc, 0, (50, 50, 200, 200))
        doc.save()
    with Document.open(blank_pdf) as r:
        page = r.page(0)
        annot = next(page.annots())
        assert annot.type[1] == "Circle"  # PDF ellipse = "Circle" annot type


def test_add_arrow_writes_line_annot(blank_pdf: Path) -> None:
    with Document.open(blank_pdf) as doc:
        anno.add_arrow(doc, 0, (50, 50), (200, 200))
        doc.save()
    with Document.open(blank_pdf) as r:
        page = r.page(0)
        annot = next(page.annots())
        assert annot.type[1] == "Line"


# ------------------------------------------------------------------ textbox
def test_add_text_box_persists(blank_pdf: Path) -> None:
    with Document.open(blank_pdf) as doc:
        anno.add_text_box(doc, 0, (50, 50, 300, 100), "Free text content")
        doc.save()
    with Document.open(blank_pdf) as r:
        page = r.page(0)
        annot = next(page.annots())
        assert annot.type[1] == "FreeText"
        # Content text is embedded in the annot stream; not always in info,
        # but the annot type is sufficient regression evidence.


# ----------------------------------------------------------- multiple on page
def test_multiple_annotations_coexist_on_same_page(blank_pdf: Path) -> None:
    with Document.open(blank_pdf) as doc:
        anno.add_rect(doc, 0, (10, 10, 50, 50))
        anno.add_ellipse(doc, 0, (60, 60, 100, 100))
        anno.add_sticky_note(doc, 0, (200, 200), "note")
        assert anno.annotation_count(doc, 0) == 3
        doc.save()
    with Document.open(blank_pdf) as r:
        assert anno.annotation_count(r, 0) == 3


def test_annotations_marked_modified_until_saved(blank_pdf: Path) -> None:
    with Document.open(blank_pdf) as doc:
        assert doc.is_modified is False
        anno.add_rect(doc, 0, (10, 10, 50, 50))
        assert doc.is_modified is True
        doc.save()
        assert doc.is_modified is False
