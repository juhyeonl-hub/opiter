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


def test_rect_on_rotated_page_lands_visually_at_clicked_position(
    tmp_path: Path,
) -> None:
    """Regression: annotations were appearing displaced on rotated pages
    because PyMuPDF's add_*_annot uses unrotated original-page coords
    while the UI passes rotated/visible coords. Each helper now applies
    page.derotation_matrix.

    Probe: rotate a page 90°, then add a small filled rect at "rotated
    visible top-left" (rotated coords (0,0,200,100)). After rendering,
    that area of the rendered pixmap should contain the red fill.
    """
    pdf = tmp_path / "rot.pdf"
    d = fitz.open()
    d.new_page(width=612, height=792)
    d.save(pdf)
    d.close()

    with Document.open(pdf) as doc:
        page = doc.page(0)
        page.set_rotation(90)
        anno.add_rect(doc, 0, (0.0, 0.0, 200.0, 100.0), color=(1.0, 0.0, 0.0))
        # Re-fetch page to ensure a stable handle for rendering
        page = doc.page(0)
        pix = page.get_pixmap(matrix=fitz.Matrix(1, 1))

    def red_count(p: fitz.Pixmap, xs: range, ys: range) -> int:
        n = p.n
        c = 0
        for y in ys:
            for x in xs:
                idx = y * p.stride + x * n
                if p.samples[idx] > 200 and p.samples[idx + 1] < 100 and p.samples[idx + 2] < 100:
                    c += 1
        return c

    w, h = pix.width, pix.height
    tl = red_count(pix, range(0, w // 4), range(0, h // 4))
    tr = red_count(pix, range(3 * w // 4, w), range(0, h // 4))
    # Annotation at rotated-TL should produce red in the TL quadrant.
    # Without the derotation fix it landed in the TR quadrant.
    assert tl > 0
    assert tr == 0


def test_freetext_rotation_zero_when_page_unrotated(blank_pdf: Path) -> None:
    with Document.open(blank_pdf) as doc:
        anno.add_text_box(doc, 0, (10, 10, 200, 50), "hello")
        page = doc.page(0)
        annot = next(page.annots())
        # PyMuPDF returns -1 for "no explicit rotation" (which is equivalent
        # to 0 visually); accept either.
        assert annot.rotation in (0, -1)


def test_freetext_rotation_counter_matches_page_rotation(tmp_path: Path) -> None:
    """Regression: when the user rotates the page and adds a text box,
    the text inside should read upright in the rotated view. This is
    achieved by setting annot.rotate = (360 - page.rotation) % 360 so
    the page's own rotation transform cancels it out at render time."""
    pdf = tmp_path / "rot_text.pdf"
    d = fitz.open()
    d.new_page(width=612, height=792)
    d.save(pdf)
    d.close()

    # page_rotation → expected annot.rotation values (multiple OK because
    # PyMuPDF stores 0 as -1 "unset"). PyMuPDF's rotate param is CCW
    # while page rotation is CW; passing page.rotation directly cancels
    # them visually (verified by user screenshot: 270 was upside-down).
    expected = {
        0: {0, -1},
        90: {90},
        180: {180},
        270: {270},
    }
    for page_rot, allowed in expected.items():
        with Document.open(pdf) as doc:
            doc.page(0).set_rotation(page_rot)
            anno.add_text_box(doc, 0, (10, 10, 200, 50), f"r{page_rot}")
            page = doc.page(0)
            annots = list(page.annots())
            assert annots[-1].rotation in allowed, (
                f"page_rot={page_rot}: expected annot.rotate in {allowed}, "
                f"got {annots[-1].rotation}"
            )


def test_pen_on_rotated_page_uses_derotation(tmp_path: Path) -> None:
    """Same fix must apply to ink (point lists)."""
    pdf = tmp_path / "rot_ink.pdf"
    d = fitz.open()
    d.new_page(width=612, height=792)
    d.save(pdf)
    d.close()

    with Document.open(pdf) as doc:
        doc.page(0).set_rotation(90)
        # Single horizontal stroke at "rotated" top-left
        anno.add_ink(doc, 0, [[(20.0, 20.0), (180.0, 20.0)]],
                     color=(1.0, 0.0, 0.0), width=4.0)
        page = doc.page(0)
        pix = page.get_pixmap(matrix=fitz.Matrix(1, 1))

    # Sample around the stroke's expected visual position
    w, h = pix.width, pix.height
    n = pix.n
    found_red_in_tl = False
    for y in range(0, h // 4):
        for x in range(0, w // 4):
            idx = y * pix.stride + x * n
            if pix.samples[idx] > 200 and pix.samples[idx + 1] < 100 and pix.samples[idx + 2] < 100:
                found_red_in_tl = True
                break
        if found_red_in_tl:
            break
    assert found_red_in_tl


def test_annotations_marked_modified_until_saved(blank_pdf: Path) -> None:
    with Document.open(blank_pdf) as doc:
        assert doc.is_modified is False
        anno.add_rect(doc, 0, (10, 10, 50, 50))
        assert doc.is_modified is True
        doc.save()
        assert doc.is_modified is False
