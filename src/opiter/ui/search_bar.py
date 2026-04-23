"""Bottom-docked search bar (Firefox/Chrome-style)."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QToolButton,
    QWidget,
)


class SearchBar(QWidget):
    """Inline find UI: input, match counter, prev/next/close buttons."""

    query_changed = Signal(str)
    """Emitted on each keystroke (live-find)."""

    next_requested = Signal()
    prev_requested = Signal()
    close_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(6)

        layout.addWidget(QLabel("Find:"))

        self._input = QLineEdit()
        self._input.setMinimumWidth(220)
        self._input.setPlaceholderText("Type to search…")
        self._input.textChanged.connect(self.query_changed.emit)
        self._input.returnPressed.connect(self.next_requested.emit)
        layout.addWidget(self._input, stretch=1)

        self._counter = QLabel("")
        self._counter.setMinimumWidth(80)
        self._counter.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._counter)

        prev_btn = QPushButton("Previous")
        prev_btn.clicked.connect(self.prev_requested.emit)
        layout.addWidget(prev_btn)

        next_btn = QPushButton("Next")
        next_btn.clicked.connect(self.next_requested.emit)
        layout.addWidget(next_btn)

        close_btn = QToolButton()
        close_btn.setText("✕")
        close_btn.setToolTip("Close (Esc)")
        close_btn.clicked.connect(self.close_requested.emit)
        layout.addWidget(close_btn)

        # Esc must work even when the QLineEdit child has focus.
        # WidgetWithChildrenShortcut covers focus on either the bar or the line edit.
        self._esc_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self._esc_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self._esc_shortcut.activated.connect(self.close_requested.emit)

    # --------------------------------------------------------------- public
    def focus_input(self) -> None:
        """Show, focus, and select-all the input field."""
        self.show()
        self._input.setFocus()
        self._input.selectAll()

    def query(self) -> str:
        return self._input.text()

    def set_status(self, current_index: int, total: int) -> None:
        """Update the match counter. ``current_index`` is 0-based; total may be 0."""
        if total == 0:
            self._counter.setText("Not found" if self._input.text().strip() else "")
        else:
            self._counter.setText(f"{current_index + 1} of {total}")
