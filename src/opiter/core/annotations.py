"""Annotation operations on a Document.

All annotations are written using PyMuPDF's standard ``/Annot`` types so
external PDF viewers (Adobe Reader, Foxit, browser PDF.js, evince, …)
render them natively.

Each function marks the document modified via :py:meth:`Document.mark_modified`.
Coordinates are PDF points (1/72 inch); UI code is responsible for
translating viewport pixels via the current zoom factor before calling.
"""
from __future__ import annotations

from typing import Sequence

import fitz

from opiter.core.document import Document

Rect = tuple[float, float, float, float]
"""``(x0, y0, x1, y1)`` in PDF points."""

Point = tuple[float, float]
"""``(x, y)`` in PDF points."""

RGB = tuple[float, float, float]
"""Each channel in ``[0.0, 1.0]``."""


# ------------------------------------------------------------ text marking
def add_highlight(doc: Document, page_index: int, rects: Sequence[Rect]) -> None:
    """Yellow highlight covering each rect (typically one per word)."""
    page = doc.page(page_index)
    quads = [fitz.Rect(*r).quad for r in rects]
    annot = page.add_highlight_annot(quads)
    annot.update()
    doc.mark_modified()


def add_underline(doc: Document, page_index: int, rects: Sequence[Rect]) -> None:
    page = doc.page(page_index)
    quads = [fitz.Rect(*r).quad for r in rects]
    annot = page.add_underline_annot(quads)
    annot.update()
    doc.mark_modified()


def add_strikeout(doc: Document, page_index: int, rects: Sequence[Rect]) -> None:
    page = doc.page(page_index)
    quads = [fitz.Rect(*r).quad for r in rects]
    annot = page.add_strikeout_annot(quads)
    annot.update()
    doc.mark_modified()


def find_words_in_rect(
    doc: Document, page_index: int, rect: Rect
) -> list[Rect]:
    """Return bounding rects of all words intersecting *rect* on *page_index*.

    Useful for translating a user's drag-selection rectangle into the per-word
    rectangles required by the highlight / underline / strikeout annotations.
    """
    page = doc.page(page_index)
    sel = fitz.Rect(*rect)
    words = page.get_text("words")  # list of (x0, y0, x1, y1, "w", b, l, w_no)
    out: list[Rect] = []
    for w in words:
        x0, y0, x1, y1 = w[0], w[1], w[2], w[3]
        if fitz.Rect(x0, y0, x1, y1).intersects(sel):
            out.append((x0, y0, x1, y1))
    return out


# ----------------------------------------------------------------- sticky note
def add_sticky_note(
    doc: Document, page_index: int, point: Point, text: str
) -> None:
    """Pop-up text annotation anchored at *point*."""
    page = doc.page(page_index)
    annot = page.add_text_annot(fitz.Point(*point), text)
    annot.update()
    doc.mark_modified()


# ----------------------------------------------------------------- pen / ink
def add_ink(
    doc: Document,
    page_index: int,
    strokes: Sequence[Sequence[Point]],
    color: RGB = (0.0, 0.0, 0.0),
    width: float = 1.5,
) -> None:
    """Freehand ink annotation. Each stroke is a list of consecutive points."""
    page = doc.page(page_index)
    # PyMuPDF expects "seq of seq of float pairs" — plain tuples work, fitz.Point doesn't.
    fitz_strokes = [[(float(p[0]), float(p[1])) for p in stroke] for stroke in strokes]
    annot = page.add_ink_annot(fitz_strokes)
    annot.set_colors(stroke=color)
    annot.set_border(width=width)
    annot.update()
    doc.mark_modified()


# ---------------------------------------------------------------- shapes
def add_rect(
    doc: Document,
    page_index: int,
    rect: Rect,
    color: RGB = (1.0, 0.0, 0.0),
    width: float = 1.5,
) -> None:
    page = doc.page(page_index)
    annot = page.add_rect_annot(fitz.Rect(*rect))
    annot.set_colors(stroke=color)
    annot.set_border(width=width)
    annot.update()
    doc.mark_modified()


def add_ellipse(
    doc: Document,
    page_index: int,
    rect: Rect,
    color: RGB = (1.0, 0.0, 0.0),
    width: float = 1.5,
) -> None:
    page = doc.page(page_index)
    annot = page.add_circle_annot(fitz.Rect(*rect))
    annot.set_colors(stroke=color)
    annot.set_border(width=width)
    annot.update()
    doc.mark_modified()


def add_arrow(
    doc: Document,
    page_index: int,
    start: Point,
    end: Point,
    color: RGB = (1.0, 0.0, 0.0),
    width: float = 1.5,
) -> None:
    """Line annotation from *start* → *end* with arrow head at the end."""
    page = doc.page(page_index)
    annot = page.add_line_annot(fitz.Point(*start), fitz.Point(*end))
    annot.set_colors(stroke=color)
    annot.set_border(width=width)
    annot.set_line_ends(fitz.PDF_ANNOT_LE_NONE, fitz.PDF_ANNOT_LE_OPEN_ARROW)
    annot.update()
    doc.mark_modified()


# -------------------------------------------------------------- free text box
def add_text_box(
    doc: Document,
    page_index: int,
    rect: Rect,
    text: str,
    fontsize: float = 12.0,
    color: RGB = (0.0, 0.0, 0.0),
) -> None:
    """Editable free-text annotation positioned within *rect*."""
    page = doc.page(page_index)
    annot = page.add_freetext_annot(
        fitz.Rect(*rect), text, fontsize=fontsize, text_color=color
    )
    annot.update()
    doc.mark_modified()


# --------------------------------------------------------------- introspection
def annotation_count(doc: Document, page_index: int) -> int:
    """Return the number of annotations on *page_index*."""
    return len(list(doc.page(page_index).annots()))
