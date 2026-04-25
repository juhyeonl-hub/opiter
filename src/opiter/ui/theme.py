# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 juhyeonl
"""Application-wide theme switching (light and dark).

Built on ``QPalette`` so all standard Qt widgets pick up the new colors
automatically. A small QSS supplement covers a few elements that the
palette does not fully control (menu separators, tooltips).
"""
from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

# --- Dark theme palette --------------------------------------------------
_DARK_WINDOW = QColor(40, 40, 40)
_DARK_BASE = QColor(28, 28, 28)
_DARK_ALT_BASE = QColor(50, 50, 50)
_DARK_BUTTON = QColor(50, 50, 50)
_DARK_TEXT = QColor(230, 230, 230)
_DARK_DISABLED_TEXT = QColor(120, 120, 120)
_DARK_HIGHLIGHT = QColor(0, 120, 215)
_DARK_LINK = QColor(80, 160, 255)

_DARK_QSS = """
QToolTip {
    color: #e6e6e6;
    background-color: #282828;
    border: 1px solid #555;
}
QMenu::separator {
    background: #555;
    height: 1px;
    margin: 4px 8px;
}
"""


def apply_light(app: QApplication) -> None:
    """Restore the platform default palette and clear any custom QSS."""
    app.setPalette(app.style().standardPalette())
    app.setStyleSheet("")


def apply_dark(app: QApplication) -> None:
    """Switch the application to a dark color scheme."""
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, _DARK_WINDOW)
    palette.setColor(QPalette.ColorRole.WindowText, _DARK_TEXT)
    palette.setColor(QPalette.ColorRole.Base, _DARK_BASE)
    palette.setColor(QPalette.ColorRole.AlternateBase, _DARK_ALT_BASE)
    palette.setColor(QPalette.ColorRole.Text, _DARK_TEXT)
    palette.setColor(QPalette.ColorRole.Button, _DARK_BUTTON)
    palette.setColor(QPalette.ColorRole.ButtonText, _DARK_TEXT)
    palette.setColor(QPalette.ColorRole.Highlight, _DARK_HIGHLIGHT)
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.ToolTipBase, _DARK_WINDOW)
    palette.setColor(QPalette.ColorRole.ToolTipText, _DARK_TEXT)
    palette.setColor(QPalette.ColorRole.Link, _DARK_LINK)

    for role in (
        QPalette.ColorRole.Text,
        QPalette.ColorRole.ButtonText,
        QPalette.ColorRole.WindowText,
    ):
        palette.setColor(QPalette.ColorGroup.Disabled, role, _DARK_DISABLED_TEXT)

    app.setPalette(palette)
    app.setStyleSheet(_DARK_QSS)
