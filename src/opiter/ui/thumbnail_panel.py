"""Sidebar panel showing thumbnail previews of every page in the document."""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QListWidget,
    QListWidgetItem,
    QWidget,
)

from opiter.core.document import Document
from opiter.core.renderer import render_page

THUMB_WIDTH_PX = 140


class ThumbnailPanel(QListWidget):
    """Vertical list of rendered page thumbnails. Click to jump, drag to reorder."""

    page_clicked = Signal(int)
    """0-based index of the page the user activated."""

    pages_reordered = Signal(list)
    """List of original page indices in their new visual order, after a
    drag-drop. The handler should apply this to the document model."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setIconSize(QSize(THUMB_WIDTH_PX, int(THUMB_WIDTH_PX * 1.5)))
        self.setSpacing(6)
        self.setUniformItemSizes(False)
        self.itemClicked.connect(self._on_item_activated)
        self.itemActivated.connect(self._on_item_activated)

        # Let Qt own the visual drag-drop (insert + remove). We listen to
        # rowsMoved AFTER Qt has consistently moved the item, then sync
        # to the document — this avoids the desync caused by mutating the
        # list during dropEvent.
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.model().rowsMoved.connect(self._on_rows_moved)

    # ------------------------------------------------------------ public API
    def set_document(self, doc: Document) -> None:
        """Render thumbnails for every page in *doc* and replace the list contents."""
        self.clear()
        for i in range(doc.page_count):
            pixmap = self._render_thumbnail(doc, i)
            item = QListWidgetItem(QIcon(pixmap), f"Page {i + 1}")
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.addItem(item)

    def select_page(self, index: int) -> None:
        """Highlight the row matching *index* (0-based) without emitting page_clicked."""
        if 0 <= index < self.count():
            self.blockSignals(True)
            try:
                self.setCurrentRow(index)
            finally:
                self.blockSignals(False)

    def relabel_after_reorder(self) -> None:
        """Reset each item's text and UserRole to match its new row index.

        Call after the document has been re-selected so item ↔ doc-page
        mapping becomes the identity again.
        """
        for i in range(self.count()):
            item = self.item(i)
            item.setText(f"Page {i + 1}")
            item.setData(Qt.ItemDataRole.UserRole, i)

    # --------------------------------------------------------------- helpers
    @staticmethod
    def _render_thumbnail(doc: Document, page_index: int) -> QPixmap:
        page_w, _ = doc.page_size(page_index)
        zoom = (THUMB_WIDTH_PX / page_w) if page_w > 0 else 0.2
        rp = render_page(doc, page_index, zoom=zoom)
        image = QImage(
            rp.samples, rp.width, rp.height, rp.stride, QImage.Format.Format_RGB888
        ).copy()
        return QPixmap.fromImage(image)

    def _on_item_activated(self, item: QListWidgetItem) -> None:
        idx = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(idx, int):
            self.page_clicked.emit(idx)

    def _on_rows_moved(self, _parent, _start, _end, _dest_parent, _dest_row) -> None:
        # Read the post-move order from each item's stored original index.
        new_order = [
            self.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.count())
        ]
        # Skip if Qt fired the signal but the order didn't actually change
        # (defensive — shouldn't normally happen).
        if new_order == sorted(new_order):
            return
        self.pages_reordered.emit(new_order)
