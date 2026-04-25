# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 juhyeonl
"""Sidebar panel showing thumbnail previews of every page in the document."""
from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QListWidget,
    QListWidgetItem,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QWidget,
)

from opiter.core.document import Document
from opiter.core.renderer import render_page
from opiter.core.thumbnail_cache import get_or_render as cache_get_or_render

THUMB_WIDTH_PX = 140
THUMB_WIDTH_MIN = 60
THUMB_WIDTH_MAX = 300

_NUM_COL_WIDTH = 32  # px reserved for the page-number column on the left
_PAD = 6


class _ThumbItemDelegate(QStyledItemDelegate):
    """Paints each thumbnail row as ``[N]  [image]`` with the page number
    in a fixed left column and the thumbnail pixmap on the right.

    We paint the background ourselves via the current style so alternating
    row colors, selection highlight, and hover states all keep working.
    """

    def paint(
        self, painter, option: QStyleOptionViewItem, index
    ) -> None:
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        # Suppress the default text + icon rendering; we draw both below.
        opt.text = ""
        opt.icon = QIcon()
        style = opt.widget.style() if opt.widget else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, opt.widget)

        rect = option.rect
        painter.save()
        painter.setPen(opt.palette.color(opt.palette.ColorRole.Text))
        num_rect = QRect(rect.x() + _PAD, rect.y(), _NUM_COL_WIDTH, rect.height())
        painter.drawText(
            num_rect,
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight),
            str(index.row() + 1),
        )
        painter.restore()

        icon = index.data(Qt.ItemDataRole.DecorationRole)
        if isinstance(icon, QIcon):
            pm = icon.pixmap(option.decorationSize)
            if not pm.isNull():
                x = rect.x() + _PAD + _NUM_COL_WIDTH + _PAD
                y = rect.y() + (rect.height() - pm.height()) // 2
                painter.drawPixmap(x, y, pm)

    def sizeHint(
        self, option: QStyleOptionViewItem, index
    ) -> QSize:
        icon_sz = option.decorationSize
        return QSize(
            _PAD + _NUM_COL_WIDTH + _PAD + icon_sz.width() + _PAD,
            icon_sz.height() + 4,
        )


class ThumbnailPanel(QListWidget):
    """Vertical list of rendered page thumbnails. Click to jump, drag to reorder."""

    page_clicked = Signal(int)
    """0-based index of the page the user activated."""

    pages_reordered = Signal(list)
    """List of original page indices in their new visual order, after a
    drag-drop. The handler should apply this to the document model."""

    def __init__(
        self, parent: QWidget | None = None, thumb_width: int = THUMB_WIDTH_PX
    ) -> None:
        super().__init__(parent)
        self._thumb_width: int = thumb_width
        self.setIconSize(QSize(self._thumb_width, int(self._thumb_width * 1.5)))
        self.setSpacing(4)
        self.setUniformItemSizes(False)
        # Zebra stripes make adjacent thumbnails (especially near-blank
        # ones) easier to tell apart at a glance.
        self.setAlternatingRowColors(True)
        # Custom delegate: "[N]  [image]" with a fixed number column on
        # the left instead of Qt's default icon-then-text layout.
        self.setItemDelegate(_ThumbItemDelegate(self))
        self.itemClicked.connect(self._on_item_activated)
        self.itemActivated.connect(self._on_item_activated)

        # Let Qt own the visual drag-drop (insert + remove). We listen to
        # rowsMoved AFTER Qt has consistently moved the item, then sync
        # to the document — this avoids the desync caused by mutating the
        # list during dropEvent.
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        # ExtendedSelection: Ctrl-click toggles items, Shift-click picks a
        # range — the user can grab several thumbnails at once and drag
        # them as a block.
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        # A generous auto-scroll margin so dragging near the top/bottom
        # edge moves the list reliably — the default 16px was too picky.
        self.setAutoScroll(True)
        self.setAutoScrollMargin(80)
        # Multi-item drops fire rowsMoved once per item. Coalesce those
        # bursts into a single pages_reordered emit by deferring with a
        # 0ms single-shot timer; each extra signal just restarts it, so
        # only one command lands on the undo stack per drag.
        self._reorder_sync_timer = QTimer(self)
        self._reorder_sync_timer.setSingleShot(True)
        self._reorder_sync_timer.setInterval(0)
        self._reorder_sync_timer.timeout.connect(self._emit_reordered)
        self.model().rowsMoved.connect(self._on_rows_moved)

    # ------------------------------------------------------------ input
    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        """Short-circuit drag-drop for Shift+click so range selection sticks.

        With ``DragDropMode.InternalMove`` the base class treats any
        press on an item as a potential drag origin. A Shift+click then
        extends the selection correctly for a frame, but the next small
        mouse move starts a drag that re-emits selection signals and
        collapses the range back to a single item. We handle the
        Shift+click case ourselves and don't propagate to the drag
        machinery — the user can still drag the resulting block by
        clicking (without Shift) on any selected item afterward.
        """
        from PySide6.QtCore import Qt as _Qt

        mods = event.modifiers()
        is_shift = bool(mods & _Qt.KeyboardModifier.ShiftModifier)
        is_ctrl = bool(mods & _Qt.KeyboardModifier.ControlModifier)
        if is_shift and not is_ctrl:
            clicked = self.itemAt(event.pos())
            if clicked is not None:
                anchor = self.currentItem() or clicked
                a = self.row(anchor)
                c = self.row(clicked)
                lo, hi = (a, c) if a <= c else (c, a)
                self.clearSelection()
                for i in range(lo, hi + 1):
                    it = self.item(i)
                    if it is not None:
                        it.setSelected(True)
                self.setCurrentItem(clicked)
                event.accept()
                return
        super().mousePressEvent(event)

    # ------------------------------------------------------------ public API
    def set_document(self, doc: Document) -> None:
        """Render thumbnails for every page in *doc* and replace the list contents."""
        self.clear()
        self._current_doc = doc
        for i in range(doc.page_count):
            pixmap = self._render_thumbnail(doc, i)
            # No display text — the delegate paints the page number.
            item = QListWidgetItem(QIcon(pixmap), "")
            item.setToolTip(f"Page {i + 1}")
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.addItem(item)

    def set_thumbnail_width(self, width: int) -> None:
        """Change the thumbnail width (px, clamped to min/max) and re-render."""
        clamped = max(THUMB_WIDTH_MIN, min(THUMB_WIDTH_MAX, int(width)))
        if clamped == self._thumb_width:
            return
        self._thumb_width = clamped
        self.setIconSize(QSize(self._thumb_width, int(self._thumb_width * 1.5)))
        # Re-render if we have a doc
        doc = getattr(self, "_current_doc", None)
        if doc is not None:
            current_row = self.currentRow()
            self.set_document(doc)
            if current_row >= 0:
                self.select_page(current_row)

    def thumbnail_width(self) -> int:
        return self._thumb_width

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
    def _render_thumbnail(self, doc: Document, page_index: int) -> QPixmap:
        try:
            png = cache_get_or_render(doc, page_index, self._thumb_width)
            pixmap = QPixmap()
            if pixmap.loadFromData(png, "PNG"):
                return pixmap
        except Exception:
            pass  # fall through to direct render
        # Fallback path: direct in-memory render (no caching).
        page_w, _ = doc.page_size(page_index)
        zoom = (self._thumb_width / page_w) if page_w > 0 else 0.2
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
        # Defer the reorder emit so a multi-item drag (which fires one
        # rowsMoved per item) collapses into a single pages_reordered.
        self._reorder_sync_timer.start()

    def _emit_reordered(self) -> None:
        new_order = [
            self.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.count())
        ]
        # Skip if Qt fired the signal but the order didn't actually change.
        if new_order == sorted(new_order):
            return
        self.pages_reordered.emit(new_order)
