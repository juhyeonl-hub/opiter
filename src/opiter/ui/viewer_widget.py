"""Page viewer widget — displays a single rendered PDF page in a scroll area."""
from __future__ import annotations

from typing import Literal

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap, QWheelEvent
from PySide6.QtWidgets import QLabel, QScrollArea, QWidget

from opiter.core.document import Document
from opiter.core.renderer import RenderedPage, render_page

ScrollPosition = Literal["top", "bottom"]


class ViewerWidget(QScrollArea):
    """Scrollable widget showing the current PDF page as a rasterized image."""

    page_changed = Signal(int, int)
    """Emitted as ``(current_index, total_count)`` whenever the displayed page changes
    or a new document is loaded."""

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

    def has_document(self) -> bool:
        return self._doc is not None

    @property
    def page_count(self) -> int:
        return self._doc.page_count if self._doc is not None else 0

    @property
    def current_page(self) -> int:
        return self._current_page

    def set_document(self, doc: Document) -> None:
        """Replace the current document and render its first page."""
        if self._doc is not None:
            self._doc.close()
        self._doc = doc
        self._current_page = 0
        self._render_current(scroll_to="top")
        self.page_changed.emit(self._current_page, self.page_count)

    def goto_page(self, index: int, scroll_to: ScrollPosition = "top") -> None:
        """Jump to *index* (0-based). Out-of-range values are clamped silently.

        ``scroll_to`` controls where the viewport lands on the new page:
        ``"top"`` (default) for keyboard/button nav, ``"bottom"`` for wheel-up
        past the current page's top so the user sees the preceding page's
        bottom — preserving reading continuity.
        """
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

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Advance/retreat page when the wheel scrolls past the viewport edge."""
        if self._doc is None:
            super().wheelEvent(event)
            return

        delta_y = event.angleDelta().y()
        if delta_y == 0:
            super().wheelEvent(event)
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

    def _render_current(self, scroll_to: ScrollPosition = "top") -> None:
        if self._doc is None:
            return
        rendered = render_page(self._doc, self._current_page, zoom=self._zoom)
        image = _to_qimage(rendered)
        self._page_label.setPixmap(QPixmap.fromImage(image))
        self._page_label.adjustSize()
        sb = self.verticalScrollBar()
        sb.setValue(sb.maximum() if scroll_to == "bottom" else sb.minimum())


def _to_qimage(rp: RenderedPage) -> QImage:
    """Convert a RenderedPage to a detached QImage."""
    fmt = QImage.Format.Format_RGBA8888 if rp.has_alpha else QImage.Format.Format_RGB888
    return QImage(rp.samples, rp.width, rp.height, rp.stride, fmt).copy()
