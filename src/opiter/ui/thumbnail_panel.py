"""Sidebar panel showing thumbnail previews of every page in the document."""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QDropEvent, QIcon, QImage, QPixmap
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

    page_moved = Signal(int, int)
    """``(from_index, to_index)`` after a drag-drop reorder."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setIconSize(QSize(THUMB_WIDTH_PX, int(THUMB_WIDTH_PX * 1.5)))
        self.setSpacing(6)
        self.setUniformItemSizes(False)
        self.itemClicked.connect(self._on_item_activated)
        self.itemActivated.connect(self._on_item_activated)

        # Drag-drop reorder configuration. We override dropEvent to keep
        # the model (Document) authoritative — Qt's default reorder would
        # diverge from the document until we rebuild thumbnails anyway.
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

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

    # ------------------------------------------------------------ drag-drop
    def dropEvent(self, event: QDropEvent) -> None:
        """Translate the drop into a ``page_moved`` signal.

        We do *not* call ``super().dropEvent`` because the parent will be
        rebuilding the list from the (now-mutated) document immediately
        afterwards. Letting Qt also reorder would briefly desynchronize
        the visual list from the document.
        """
        src_items = self.selectedItems()
        if not src_items:
            event.ignore()
            return
        from_index = self.row(src_items[0])

        drop_pos = event.position().toPoint()
        target_index = self.indexAt(drop_pos)
        if target_index.isValid():
            to_index = target_index.row()
        else:
            to_index = self.count() - 1

        if from_index != to_index:
            self.page_moved.emit(from_index, to_index)

        event.accept()
