"""Page viewer widget — displays a single rendered PDF page in a scroll area."""
from __future__ import annotations

from typing import Literal

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap, QWheelEvent
from PySide6.QtWidgets import QLabel, QScrollArea, QWidget

from opiter.core.document import Document
from opiter.core.renderer import RenderedPage, render_page

ScrollPosition = Literal["top", "bottom"]

# Discrete zoom stops (monotonic). zoom_in/zoom_out step through these;
# set_zoom accepts arbitrary values within [_ZOOM_MIN, _ZOOM_MAX].
_ZOOM_PRESETS: tuple[float, ...] = (
    0.25, 0.33, 0.50, 0.67, 0.75, 1.00,
    1.25, 1.50, 2.00, 3.00, 4.00,
)
_ZOOM_MIN = 0.10
_ZOOM_MAX = 10.00


class ViewerWidget(QScrollArea):
    """Scrollable widget showing the current PDF page as a rasterized image."""

    page_changed = Signal(int, int)
    """``(current_index, total_count)`` — page or document changed."""

    zoom_changed = Signal(float)
    """New zoom factor (e.g. 1.0 for 100%)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._page_label = QLabel()
        self._page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._page_label.setText("(No document loaded — File → Open to begin)")
        self.setWidget(self._page_label)
        self.setWidgetResizable(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._doc: Document | None = None
        self._current_page: int = 0
        self._zoom: float = 1.0
        self._highlights_by_page: dict[int, list[tuple[float, float, float, float]]] = {}
        self._current_highlight: tuple[int, int] | None = None  # (page_idx, match_idx)

    # -------------------------------------------------------------- accessors
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
        """Replace the current document and render its first page."""
        if self._doc is not None:
            self._doc.close()
        self._doc = doc
        self._current_page = 0
        self._render_current(scroll_to="top")
        self.page_changed.emit(self._current_page, self.page_count)

    # ---------------------------------------------------------- navigation
    def goto_page(self, index: int, scroll_to: ScrollPosition = "top") -> None:
        """Jump to *index* (0-based). Out-of-range values are clamped silently."""
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
        """Re-render the current page and emit page_changed.

        Use after the underlying document is mutated externally (delete /
        insert page, etc.) so the viewer picks up the new content and the
        UI's indicators (page count, thumbnail selection) refresh. Clamps
        ``current_page`` if the page count shrank below it.
        """
        if self._doc is None:
            return
        if self._current_page >= self.page_count:
            self._current_page = max(0, self.page_count - 1)
        self._render_current(scroll_to="top")
        self.page_changed.emit(self._current_page, self.page_count)

    # ----------------------------------------------------------------- zoom
    def set_zoom(self, zoom: float) -> None:
        """Set an arbitrary zoom factor, clamped to [0.1, 10.0]."""
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
        """Set zoom to 100% (actual size)."""
        self.set_zoom(1.0)

    def fit_width(self) -> None:
        """Scale so the page width matches the viewport width."""
        if self._doc is None:
            return
        page_w, _ = self._doc.page_size(self._current_page)
        viewport_w = self.viewport().width()
        if page_w > 0 and viewport_w > 0:
            self.set_zoom(viewport_w / page_w)

    def fit_page(self) -> None:
        """Scale so the entire page fits within the viewport."""
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
        """Replace highlight overlays.

        ``rects_by_page`` maps page index → list of (x0, y0, x1, y1) in PDF points.
        ``current`` is an optional ``(page_idx, match_idx_within_page)`` to render
        with a stronger color.
        """
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
        rendered = render_page(self._doc, self._current_page, zoom=self._zoom)
        image = _to_qimage(rendered)
        pixmap = QPixmap.fromImage(image)
        self._overlay_highlights(pixmap)
        self._page_label.setPixmap(pixmap)
        self._page_label.adjustSize()
        sb = self.verticalScrollBar()
        sb.setValue(sb.maximum() if scroll_to == "bottom" else sb.minimum())

    def _overlay_highlights(self, pixmap: QPixmap) -> None:
        rects = self._highlights_by_page.get(self._current_page)
        if not rects:
            return
        cur_idx = (
            self._current_highlight[1]
            if self._current_highlight and self._current_highlight[0] == self._current_page
            else -1
        )
        painter = QPainter(pixmap)
        try:
            painter.setPen(Qt.PenStyle.NoPen)
            for i, (x0, y0, x1, y1) in enumerate(rects):
                color = (
                    QColor(255, 140, 0, 140) if i == cur_idx else QColor(255, 240, 0, 110)
                )
                painter.setBrush(color)
                painter.drawRect(
                    QRectF(
                        x0 * self._zoom,
                        y0 * self._zoom,
                        (x1 - x0) * self._zoom,
                        (y1 - y0) * self._zoom,
                    )
                )
        finally:
            painter.end()


def _to_qimage(rp: RenderedPage) -> QImage:
    """Convert a RenderedPage to a detached QImage."""
    fmt = QImage.Format.Format_RGBA8888 if rp.has_alpha else QImage.Format.Format_RGB888
    return QImage(rp.samples, rp.width, rp.height, rp.stride, fmt).copy()
