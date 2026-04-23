"""Page viewer widget — displays a single rendered PDF page in a scroll area."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel, QScrollArea, QWidget

from opiter.core.document import Document
from opiter.core.renderer import RenderedPage, render_page


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
        self._render_current()
        self.page_changed.emit(self._current_page, self.page_count)

    def goto_page(self, index: int) -> None:
        """Jump to *index* (0-based). Out-of-range values are clamped silently."""
        if self._doc is None:
            return
        clamped = max(0, min(index, self.page_count - 1))
        if clamped == self._current_page:
            return
        self._current_page = clamped
        self._render_current()
        self.page_changed.emit(self._current_page, self.page_count)

    def next_page(self) -> None:
        self.goto_page(self._current_page + 1)

    def prev_page(self) -> None:
        self.goto_page(self._current_page - 1)

    def first_page(self) -> None:
        self.goto_page(0)

    def last_page(self) -> None:
        self.goto_page(self.page_count - 1)

    def _render_current(self) -> None:
        if self._doc is None:
            return
        rendered = render_page(self._doc, self._current_page, zoom=self._zoom)
        image = _to_qimage(rendered)
        self._page_label.setPixmap(QPixmap.fromImage(image))
        self._page_label.adjustSize()
        # Reset scroll on page change so the user always lands at the top.
        self.verticalScrollBar().setValue(0)


def _to_qimage(rp: RenderedPage) -> QImage:
    """Convert a RenderedPage to a detached QImage."""
    fmt = QImage.Format.Format_RGBA8888 if rp.has_alpha else QImage.Format.Format_RGB888
    return QImage(rp.samples, rp.width, rp.height, rp.stride, fmt).copy()
