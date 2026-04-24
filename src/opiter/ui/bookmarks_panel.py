"""Bookmarks / Table-of-Contents sidebar panel."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from opiter.core.toc import TocEntry


class BookmarksPanel(QWidget):
    """Tree view of the document's TOC plus Add/Rename/Remove controls."""

    page_jump_requested = Signal(int)  # 0-based page index
    toc_changed = Signal(list)  # list[TocEntry] — caller applies to document

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(4)

        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Title", "Page"])
        self._tree.setColumnCount(2)
        self._tree.itemDoubleClicked.connect(self._on_double_click)
        outer.addWidget(self._tree, stretch=1)

        row = QHBoxLayout()
        self._btn_add = QPushButton("Add")
        self._btn_rename = QPushButton("Rename")
        self._btn_remove = QPushButton("Remove")
        row.addWidget(self._btn_add)
        row.addWidget(self._btn_rename)
        row.addWidget(self._btn_remove)
        outer.addLayout(row)

        self._btn_add.clicked.connect(self._on_add)
        self._btn_rename.clicked.connect(self._on_rename)
        self._btn_remove.clicked.connect(self._on_remove)

        self._current_page_idx: int = 0  # for Add default
        self._total_pages: int = 0

    # ------------------------------------------------------------ public API
    def set_toc(self, entries: list[TocEntry]) -> None:
        """Populate the tree from a flat list (levels define nesting)."""
        self._tree.clear()
        stack: list[tuple[int, QTreeWidgetItem]] = []
        for e in entries:
            item = QTreeWidgetItem([e.title, str(e.page)])
            item.setData(0, Qt.ItemDataRole.UserRole, e.page - 1)  # 0-based
            # Pop stack until parent level < current level
            while stack and stack[-1][0] >= e.level:
                stack.pop()
            if stack:
                stack[-1][1].addChild(item)
            else:
                self._tree.addTopLevelItem(item)
            stack.append((e.level, item))
        self._tree.expandAll()

    def set_page_context(self, current_page: int, total_pages: int) -> None:
        """Inform the panel of the viewer's current page (for Add default)
        and the valid page range (for validation)."""
        self._current_page_idx = max(0, current_page)
        self._total_pages = max(0, total_pages)

    def clear(self) -> None:  # noqa: A003  (QWidget.clear is not a thing here)
        self._tree.clear()

    def to_entries(self) -> list[TocEntry]:
        """Flatten the tree back to TocEntry list (reading level from depth)."""
        result: list[TocEntry] = []

        def visit(item: QTreeWidgetItem, level: int) -> None:
            title = item.text(0)
            try:
                page = int(item.text(1))
            except ValueError:
                page = 1
            result.append(TocEntry(level=level, title=title, page=page))
            for i in range(item.childCount()):
                visit(item.child(i), level + 1)

        for i in range(self._tree.topLevelItemCount()):
            visit(self._tree.topLevelItem(i), 1)
        return result

    # -------------------------------------------------------------- slots
    def _on_double_click(self, item: QTreeWidgetItem, _column: int) -> None:
        target = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(target, int):
            self.page_jump_requested.emit(target)

    def _on_add(self) -> None:
        if self._total_pages == 0:
            QMessageBox.information(self, "No Document", "Open a PDF first.")
            return
        title, ok = QInputDialog.getText(self, "New Bookmark", "Title:")
        if not ok or not title.strip():
            return
        page, ok = QInputDialog.getInt(
            self,
            "New Bookmark",
            f"Page (1 – {self._total_pages}):",
            value=self._current_page_idx + 1,
            minValue=1,
            maxValue=self._total_pages,
        )
        if not ok:
            return
        # Add as a sibling of the currently-selected item (or top-level)
        new_item = QTreeWidgetItem([title.strip(), str(page)])
        new_item.setData(0, Qt.ItemDataRole.UserRole, page - 1)
        selected = self._tree.currentItem()
        if selected and selected.parent():
            selected.parent().addChild(new_item)
        else:
            self._tree.addTopLevelItem(new_item)
        self.toc_changed.emit(self.to_entries())

    def _on_rename(self) -> None:
        item = self._tree.currentItem()
        if item is None:
            return
        new_title, ok = QInputDialog.getText(
            self, "Rename Bookmark", "Title:", text=item.text(0)
        )
        if not ok or not new_title.strip():
            return
        item.setText(0, new_title.strip())
        self.toc_changed.emit(self.to_entries())

    def _on_remove(self) -> None:
        item = self._tree.currentItem()
        if item is None:
            return
        parent = item.parent()
        if parent:
            parent.removeChild(item)
        else:
            idx = self._tree.indexOfTopLevelItem(item)
            self._tree.takeTopLevelItem(idx)
        self.toc_changed.emit(self.to_entries())
