# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 juhyeonl
"""Page viewer widget — displays a single rendered PDF page in a scroll area."""
from __future__ import annotations

from typing import Literal

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap, QWheelEvent
from PySide6.QtWidgets import QScrollArea, QWidget

from opiter.core.document import Document
from opiter.core.renderer import RenderedPage, render_page
from opiter.ui.page_canvas import PageCanvas

ScrollPosition = Literal["top", "bottom", "keep"]

_ZOOM_PRESETS: tuple[float, ...] = (
    0.25, 0.33, 0.50, 0.67, 0.75, 1.00,
    1.25, 1.50, 2.00, 3.00, 4.00,
)
_ZOOM_MIN = 0.10
_ZOOM_MAX = 10.00


class ViewerWidget(QScrollArea):
    """Scrollable widget hosting a :class:`PageCanvas` for the current PDF page."""

    page_changed = Signal(int, int)
    """``(current_index, total_count)`` — page or document changed."""

    zoom_changed = Signal(float)
    """New zoom factor (e.g. 1.0 for 100%)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._page_canvas = PageCanvas()
        self.setWidget(self._page_canvas)
        self.setWidgetResizable(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._doc: Document | None = None
        self._current_page: int = 0
        self._zoom: float = 1.0
        self._highlights_by_page: dict[int, list[tuple[float, float, float, float]]] = {}
        self._current_highlight: tuple[int, int] | None = None  # (page_idx, match_idx)

    # -------------------------------------------------------------- accessors
    @property
    def page_canvas(self) -> PageCanvas:
        return self._page_canvas

    def has_document(self) -> bool:
        return self._doc is not None

    @property
    def page_count(self) -> int:
        return self._doc.page_count if self._doc is not None else 0

    @property
    def current_page(self) -> int:
        return self._current_page

    @property
    def zoom(self) -> float:
        return self._zoom

    # ----------------------------------------------------------- document ops
    def set_document(self, doc: Document) -> None:
        """Replace the current document and render its first page.
        Closes the previous document if any (single-doc-owning callers)."""
        if self._doc is not None:
            self._doc.close()
        self._doc = doc
        self._current_page = 0
        self._render_current(scroll_to="top")
        self.page_changed.emit(self._current_page, self.page_count)

    def swap_document(self, doc: Document) -> None:
        """Switch which document the viewer renders WITHOUT closing the
        previous one — used by the multi-PDF tab system where each tab
        owns its own ``Document`` and lifecycle is handled at tab close."""
        self._doc = doc
        self._current_page = 0
        self._render_current(scroll_to="top")
        self.page_changed.emit(self._current_page, self.page_count)

    def close_document(self) -> None:
        """Release the current document and show an empty canvas."""
        if self._doc is not None:
            self._doc.close()
        self.detach_document()

    def detach_document(self) -> None:
        """Drop the document reference and show an empty canvas WITHOUT
        closing it — used when something else (a tab holder) owns the
        document's lifecycle."""
        self._doc = None
        self._current_page = 0
        self.page_canvas.clear_page()
        self.page_changed.emit(0, 0)

    # ---------------------------------------------------------- navigation
    def goto_page(self, index: int, scroll_to: ScrollPosition = "top") -> None:
        if self._doc is None:
            return
        clamped = max(0, min(index, self.page_count - 1))
        if clamped == self._current_page:
            return
        self._current_page = clamped
        self._render_current(scroll_to=scroll_to)
        self.page_changed.emit(self._current_page, self.page_count)

    def next_page(self) -> None:
        self.goto_page(self._current_page + 1)

    def prev_page(self) -> None:
        self.goto_page(self._current_page - 1)

    def first_page(self) -> None:
        self.goto_page(0)

    def last_page(self) -> None:
        self.goto_page(self.page_count - 1)

    def reload_current(self) -> None:
        """Re-render the current page **without moving the viewport**.

        Used after in-place mutations (annotations, undo/redo, etc.) where
        the user has been scrolled to some position on the page and does
        not want the viewer to jump back to the top every time.
        """
        if self._doc is None:
            return
        if self._current_page >= self.page_count:
            self._current_page = max(0, self.page_count - 1)
        self._render_current(scroll_to="keep")
        self.page_changed.emit(self._current_page, self.page_count)

    # ----------------------------------------------------------------- zoom
    def set_zoom(self, zoom: float) -> None:
        zoom = max(_ZOOM_MIN, min(_ZOOM_MAX, zoom))
        if abs(zoom - self._zoom) < 1e-6:
            return
        self._zoom = zoom
        if self._doc is not None:
            self._render_current(scroll_to="top")
        self.zoom_changed.emit(self._zoom)

    def zoom_in(self) -> None:
        for z in _ZOOM_PRESETS:
            if z > self._zoom + 1e-6:
                self.set_zoom(z)
                return
        self.set_zoom(self._zoom * 1.25)

    def zoom_out(self) -> None:
        for z in reversed(_ZOOM_PRESETS):
            if z < self._zoom - 1e-6:
                self.set_zoom(z)
                return
        self.set_zoom(self._zoom / 1.25)

    def reset_zoom(self) -> None:
        self.set_zoom(1.0)

    def fit_width(self) -> None:
        if self._doc is None:
            return
        page_w, _ = self._doc.page_size(self._current_page)
        viewport_w = self.viewport().width()
        if page_w > 0 and viewport_w > 0:
            self.set_zoom(viewport_w / page_w)

    def fit_page(self) -> None:
        if self._doc is None:
            return
        page_w, page_h = self._doc.page_size(self._current_page)
        vw = self.viewport().width()
        vh = self.viewport().height()
        if page_w > 0 and page_h > 0 and vw > 0 and vh > 0:
            self.set_zoom(min(vw / page_w, vh / page_h))

    # ----------------------------------------------------------- search highlights
    def set_search_highlights(
        self,
        rects_by_page: dict[int, list[tuple[float, float, float, float]]],
        current: tuple[int, int] | None = None,
    ) -> None:
        self._highlights_by_page = dict(rects_by_page)
        self._current_highlight = current
        if self._doc is not None:
            self._render_current(scroll_to="top")

    def clear_search_highlights(self) -> None:
        if not self._highlights_by_page and self._current_highlight is None:
            return
        self._highlights_by_page = {}
        self._current_highlight = None
        if self._doc is not None:
            self._render_current(scroll_to="top")

    # ------------------------------------------------------------ wheel/events
    def wheelEvent(self, event: QWheelEvent) -> None:
        """Ctrl+wheel → zoom. Plain wheel at page edges → advance/retreat page."""
        if self._doc is None:
            super().wheelEvent(event)
            return

        delta_y = event.angleDelta().y()
        if delta_y == 0:
            super().wheelEvent(event)
            return

        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if delta_y > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
            return

        sb = self.verticalScrollBar()
        at_top = sb.value() <= sb.minimum()
        at_bottom = sb.value() >= sb.maximum()

        if delta_y < 0 and at_bottom and self._current_page < self.page_count - 1:
            self.goto_page(self._current_page + 1, scroll_to="top")
            event.accept()
            return
        if delta_y > 0 and at_top and self._current_page > 0:
            self.goto_page(self._current_page - 1, scroll_to="bottom")
            event.accept()
            return

        super().wheelEvent(event)

    # -------------------------------------------------------------- rendering
    def _render_current(self, scroll_to: ScrollPosition = "top") -> None:
        if self._doc is None:
            return
        # Capture scroll position before re-rendering so "keep" can restore it
        # after the pixmap (and therefore the scrollbar range) is replaced.
        sb_v = self.verticalScrollBar()
        sb_h = self.horizontalScrollBar()
        prev_v = sb_v.value()
        prev_h = sb_h.value()

        rendered = render_page(self._doc, self._current_page, zoom=self._zoom)
        image = _to_qimage(rendered)
        pixmap = QPixmap.fromImage(image)
        self._overlay_highlights(pixmap)
        self._page_canvas.set_page_pixmap(pixmap, self._zoom)

        if scroll_to == "bottom":
            sb_v.setValue(sb_v.maximum())
        elif scroll_to == "top":
            sb_v.setValue(sb_v.minimum())
        else:  # "keep"
            sb_v.setValue(max(sb_v.minimum(), min(sb_v.maximum(), prev_v)))
            sb_h.setValue(max(sb_h.minimum(), min(sb_h.maximum(), prev_h)))

    def _overlay_highlights(self, pixmap: QPixmap) -> None:
        rects = self._highlights_by_page.get(self._current_page)
        if not rects:
            return
        cur_idx = (
            self._current_highlight[1]
            if self._current_highlight and self._current_highlight[0] == self._current_page
            else -1
        )
        # Search results come back in unrotated PDF coordinates; the pixmap
        # we draw on is already rotated to match the page's visible
        # orientation, so rects must be transformed through the page's
        # rotation matrix before scaling by zoom.
        import fitz  # local import to avoid broadening module deps
        page = self._doc.page(self._current_page) if self._doc else None
        rot_matrix = page.rotation_matrix if page is not None else fitz.Matrix(1, 1)
        painter = QPainter(pixmap)
        try:
            painter.setPen(Qt.PenStyle.NoPen)
            for i, (x0, y0, x1, y1) in enumerate(rects):
                color = (
                    QColor(255, 140, 0, 140) if i == cur_idx else QColor(255, 240, 0, 110)
                )
                painter.setBrush(color)
                rot = fitz.Rect(x0, y0, x1, y1) * rot_matrix
                painter.drawRect(
                    QRectF(
                        rot.x0 * self._zoom,
                        rot.y0 * self._zoom,
                        (rot.x1 - rot.x0) * self._zoom,
                        (rot.y1 - rot.y0) * self._zoom,
                    )
                )
        finally:
            painter.end()


def _to_qimage(rp: RenderedPage) -> QImage:
    fmt = QImage.Format.Format_RGBA8888 if rp.has_alpha else QImage.Format.Format_RGB888
    return QImage(rp.samples, rp.width, rp.height, rp.stride, fmt).copy()
