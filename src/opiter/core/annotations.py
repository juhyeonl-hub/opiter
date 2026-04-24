"""Annotation operations on a Document.

All annotations are written using PyMuPDF's standard ``/Annot`` types so
external PDF viewers (Adobe Reader, Foxit, browser PDF.js, evince, …)
render them natively.

Coordinates are PDF points (1/72 inch) in the page's **current/rotated**
orientation — i.e. the same coordinates the user sees on screen. PyMuPDF's
``page.add_*_annot`` APIs themselves take coordinates in the page's
**unrotated** original space, so each function here applies
``page.derotation_matrix`` before delegating. Without this the annotation
ends up displaced (visible only when the page has been rotated).

Each function marks the document modified via :py:meth:`Document.mark_modified`.
"""
from __future__ import annotations

from typing import Sequence

import fitz

from opiter.core.document import Document

Rect = tuple[float, float, float, float]
"""``(x0, y0, x1, y1)`` in PDF points (rotated/visible space)."""

Point = tuple[float, float]
"""``(x, y)`` in PDF points (rotated/visible space)."""

RGB = tuple[float, float, float]
"""Each channel in ``[0.0, 1.0]``."""


# ----------------------------------------------- coordinate transformation
def _to_unrotated_rect(page: fitz.Page, r: Rect) -> fitz.Rect:
    """Convert a rect in the page's current orientation to its unrotated form.

    PyMuPDF's annotation APIs expect unrotated page coordinates; UI clicks
    arrive in the rotated coordinate system the user is interacting with.
    """
    rect = fitz.Rect(*r)
    if page.rotation == 0:
        return rect
    # `Rect * Matrix` transforms then re-normalizes the corners.
    return rect * page.derotation_matrix


def _to_unrotated_point(page: fitz.Page, p: Point) -> fitz.Point:
    point = fitz.Point(*p)
    if page.rotation == 0:
        return point
    return point * page.derotation_matrix


def _to_unrotated_quad(page: fitz.Page, r: Rect) -> fitz.Quad:
    """Same as ``_to_unrotated_rect`` but returns a Quad (needed by the
    text-marking annotations which want quads, not rects)."""
    return _to_unrotated_rect(page, r).quad


# ------------------------------------------------------------ text marking
def add_highlight(
    doc: Document,
    page_index: int,
    rects: Sequence[Rect],
    color: RGB | None = None,
) -> None:
    """Highlight each rect (yellow if no color given)."""
    page = doc.page(page_index)
    quads = [_to_unrotated_quad(page, r) for r in rects]
    annot = page.add_highlight_annot(quads)
    if color is not None:
        annot.set_colors(stroke=color)
    annot.update()
    doc.mark_modified()


def add_underline(
    doc: Document,
    page_index: int,
    rects: Sequence[Rect],
    color: RGB | None = None,
) -> None:
    page = doc.page(page_index)
    quads = [_to_unrotated_quad(page, r) for r in rects]
    annot = page.add_underline_annot(quads)
    if color is not None:
        annot.set_colors(stroke=color)
    annot.update()
    doc.mark_modified()


def add_strikeout(
    doc: Document,
    page_index: int,
    rects: Sequence[Rect],
    color: RGB | None = None,
) -> None:
    page = doc.page(page_index)
    quads = [_to_unrotated_quad(page, r) for r in rects]
    annot = page.add_strikeout_annot(quads)
    if color is not None:
        annot.set_colors(stroke=color)
    annot.update()
    doc.mark_modified()


def find_words_in_rect(
    doc: Document, page_index: int, rect: Rect
) -> list[Rect]:
    """Return bounding rects of all words intersecting *rect* (rotated coords)
    on *page_index*. Consecutive words on the same line are MERGED into a
    single rect so that the resulting highlight / underline / strikeout
    appears as one continuous mark instead of a row of word-shaped boxes
    with V-notches in the spaces between them.

    Merging logic: words are grouped by ``(block_no, line_no)`` from
    PyMuPDF's word tuple; within each line they are sorted by ``word_no``
    and split into runs of consecutive ``word_no`` values; each run becomes
    one merged rect spanning the run's full bbox.
    """
    page = doc.page(page_index)
    sel = fitz.Rect(*rect)
    # page.get_text("words") returns rects in rotated/visible coords for a
    # rotated page (PyMuPDF docs), so the intersection test is consistent
    # with how the user sees the text.
    # Each tuple: (x0, y0, x1, y1, "word", block_no, line_no, word_no)
    words = page.get_text("words")

    # Group hit words by (block_no, line_no)
    by_line: dict[tuple[int, int], list[tuple[float, float, float, float, int]]] = {}
    for w in words:
        x0, y0, x1, y1 = w[0], w[1], w[2], w[3]
        if not fitz.Rect(x0, y0, x1, y1).intersects(sel):
            continue
        block_no, line_no, word_no = w[5], w[6], w[7]
        by_line.setdefault((block_no, line_no), []).append(
            (x0, y0, x1, y1, word_no)
        )

    out: list[Rect] = []
    for line_words in by_line.values():
        line_words.sort(key=lambda item: item[4])  # by word_no
        # Split into consecutive-word_no runs
        run: list[tuple[float, float, float, float, int]] = [line_words[0]]
        for item in line_words[1:]:
            if item[4] == run[-1][4] + 1:
                run.append(item)
            else:
                out.append(_merge_run(run))
                run = [item]
        out.append(_merge_run(run))
    return out


def _merge_run(run: list[tuple[float, float, float, float, int]]) -> Rect:
    return (
        min(w[0] for w in run),
        min(w[1] for w in run),
        max(w[2] for w in run),
        max(w[3] for w in run),
    )


# ----------------------------------------------------------------- sticky note
def add_sticky_note(
    doc: Document, page_index: int, point: Point, text: str
) -> None:
    """Pop-up text annotation anchored at *point*."""
    page = doc.page(page_index)
    annot = page.add_text_annot(_to_unrotated_point(page, point), text)
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
    fitz_strokes: list[list[tuple[float, float]]] = []
    for stroke in strokes:
        new_stroke: list[tuple[float, float]] = []
        for p in stroke:
            up = _to_unrotated_point(page, (float(p[0]), float(p[1])))
            new_stroke.append((up.x, up.y))
        fitz_strokes.append(new_stroke)
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
    annot = page.add_rect_annot(_to_unrotated_rect(page, rect))
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
    annot = page.add_circle_annot(_to_unrotated_rect(page, rect))
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
    annot = page.add_line_annot(
        _to_unrotated_point(page, start), _to_unrotated_point(page, end)
    )
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
    """Editable free-text annotation positioned within *rect*.

    The text content is counter-rotated against ``page.rotation`` so it
    reads upright in the user's currently-rotated view. Rationale: if the
    user rotated the page they did so for a reason; annotations placed
    while rotated should read naturally in that orientation, not in the
    unrotated baseline. (Sticky-note popup orientation is viewer-driven
    and cannot be controlled the same way.)

    PyMuPDF's ``rotate`` parameter is CCW; PDF page rotation is CW. To
    cancel the page's CW rotation visually, the text rotation must be the
    same number of degrees CCW — i.e. just pass ``page.rotation`` directly.
    Setting ``rotate = (360 - page.rotation)`` (the obvious-looking math)
    instead made text appear flipped 180° (verified on screen).
    """
    page = doc.page(page_index)
    text_rotate = page.rotation
    annot = page.add_freetext_annot(
        _to_unrotated_rect(page, rect),
        text,
        fontsize=fontsize,
        text_color=color,
        rotate=text_rotate,
    )
    annot.update()
    doc.mark_modified()


# --------------------------------------------------------------- introspection
def annotation_count(doc: Document, page_index: int) -> int:
    """Return the number of annotations on *page_index*."""
    return len(list(doc.page(page_index).annots()))


# ----------------------------------------------- selection / edit / delete
def find_annotation_at(
    doc: Document, page_index: int, point: Point
) -> int | None:
    """Return the xref of the topmost annotation containing *point*
    (in rotated/visible coords), or ``None``.

    "Topmost" = the LAST annot in iteration order (PDF z-order: later
    annots draw on top of earlier ones).
    """
    page = doc.page(page_index)
    if page.rotation != 0:
        p = fitz.Point(*point) * page.derotation_matrix
        px, py = p.x, p.y
    else:
        px, py = point
    hit: int | None = None
    for annot in page.annots():
        r = annot.rect
        if r.x0 <= px <= r.x1 and r.y0 <= py <= r.y1:
            hit = annot.xref
    return hit


def get_annotation_rect(
    doc: Document, page_index: int, xref: int
) -> Rect | None:
    """Return the annot's bounding rect in **rotated/visible** coords."""
    page = doc.page(page_index)
    for annot in page.annots():
        if annot.xref != xref:
            continue
        r = annot.rect
        if page.rotation != 0:
            rotated = fitz.Rect(r) * page.rotation_matrix
            return (rotated.x0, rotated.y0, rotated.x1, rotated.y1)
        return (r.x0, r.y0, r.x1, r.y1)
    return None


def delete_annotation(doc: Document, page_index: int, xref: int) -> bool:
    page = doc.page(page_index)
    for annot in page.annots():
        if annot.xref == xref:
            page.delete_annot(annot)
            doc.mark_modified()
            return True
    return False


def move_annotation(
    doc: Document,
    page_index: int,
    xref: int,
    dx: float,
    dy: float,
) -> bool:
    """Translate annot by ``(dx, dy)`` given in rotated/visible coords.
    Returns True if the annot was found and moved.

    Ink annotations get special handling: PyMuPDF refuses ``set_rect`` on
    them ("Ink annotations have no Rect property") because they are
    defined by their per-stroke point lists, not a bounding box. We
    translate the vertices and recreate the annot.
    """
    page = doc.page(page_index)
    # Convert visible-space delta to unrotated-space delta. The translation
    # part of the matrix doesn't affect a delta vector — subtract the
    # transformed origin.
    if page.rotation != 0:
        p0 = fitz.Point(0, 0) * page.derotation_matrix
        p1 = fitz.Point(dx, dy) * page.derotation_matrix
        ux, uy = p1.x - p0.x, p1.y - p0.y
    else:
        ux, uy = dx, dy
    for annot in page.annots():
        if annot.xref != xref:
            continue
        atype = annot.type[1]
        if atype == "Ink":
            return _move_ink_annot(page, annot, doc, ux, uy)
        r = annot.rect
        new_rect = fitz.Rect(r.x0 + ux, r.y0 + uy, r.x1 + ux, r.y1 + uy)
        annot.set_rect(new_rect)
        annot.update()
        doc.mark_modified()
        return True
    return False


def _move_ink_annot(page, annot, doc: Document, dx: float, dy: float) -> bool:
    """Special-case translation for Ink: read vertices, translate, recreate.

    Returns True on success. Preserves stroke color and border width
    where readable; the new annot will have a different ``xref``, so any
    UI selection state pointing at the old xref must be refreshed by
    the caller.
    """
    raw = annot.vertices  # may be flat [Point...] or nested [[Point...]...]
    if not raw:
        return False
    # Normalize to nested list of strokes.
    first = raw[0]
    if isinstance(first, (list, tuple)) and first and not isinstance(
        first[0], (int, float)
    ):
        nested = raw
    elif hasattr(first, "x") and hasattr(first, "y"):
        # Flat list of fitz.Points → single stroke
        nested = [raw]
    else:
        # Flat list of (x, y) tuples → single stroke
        nested = [raw]

    # Translate each point. fitz.Point and tuple/list both supported.
    translated: list[list[tuple[float, float]]] = []
    for stroke in nested:
        new_stroke: list[tuple[float, float]] = []
        for p in stroke:
            if hasattr(p, "x") and hasattr(p, "y"):
                new_stroke.append((float(p.x) + dx, float(p.y) + dy))
            else:
                new_stroke.append((float(p[0]) + dx, float(p[1]) + dy))
        if new_stroke:
            translated.append(new_stroke)

    # Preserve stroke color + border width if available.
    try:
        colors = annot.colors or {}
        stroke_color = colors.get("stroke") or (0.0, 0.0, 0.0)
    except Exception:
        stroke_color = (0.0, 0.0, 0.0)
    try:
        border = annot.border or {}
        width = border.get("width") or 1.5
    except Exception:
        width = 1.5

    page.delete_annot(annot)
    new_annot = page.add_ink_annot(translated)
    new_annot.set_colors(stroke=stroke_color)
    new_annot.set_border(width=width)
    new_annot.update()
    doc.mark_modified()
    return True
