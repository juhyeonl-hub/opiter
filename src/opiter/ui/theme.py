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

# --- Light theme palette -------------------------------------------------
# Explicit values rather than ``style().standardPalette()`` because the
# default on Windows 11 ships washed-out grays with poor contrast for
# Qt widgets — toolbar/tab/menu text becomes nearly invisible. The
# palette below mirrors Qt's traditional Fusion light look but with
# stronger text contrast.
_LIGHT_WINDOW = QColor(245, 245, 245)
_LIGHT_BASE = QColor(255, 255, 255)
_LIGHT_ALT_BASE = QColor(235, 235, 235)
_LIGHT_BUTTON = QColor(240, 240, 240)
_LIGHT_TEXT = QColor(20, 20, 20)
_LIGHT_DISABLED_TEXT = QColor(140, 140, 140)
_LIGHT_HIGHLIGHT = QColor(0, 120, 215)
_LIGHT_LINK = QColor(0, 102, 204)

_LIGHT_QSS = """
QToolTip {
    color: #141414;
    background-color: #fdfdfd;
    border: 1px solid #aaa;
}
QMenu::separator {
    background: #c8c8c8;
    height: 1px;
    margin: 4px 8px;
}
/* Windows native style sometimes ignores palette WindowText for the
 * menu bar; pin the menubar foreground explicitly. */
QMenuBar { background-color: #f5f5f5; color: #141414; }
QMenuBar::item { background: transparent; color: #141414; padding: 4px 10px; }
QMenuBar::item:selected { background: #d8d8d8; color: #141414; }
QMenu { background-color: #ffffff; color: #141414; border: 1px solid #c0c0c0; }
QMenu::item:selected { background: #d8d8d8; color: #141414; }
QToolBar { background: #f5f5f5; border: 0; }
QTabBar::tab { color: #141414; background: #e8e8e8; padding: 4px 10px; }
QTabBar::tab:selected { background: #ffffff; }
"""


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


def _force_fusion_style(app: QApplication) -> None:
    """Make our explicit palette actually take effect.

    Windows' native ``windowsvista`` style ignores most palette colors
    (it pulls them from the OS theme), so toolbar / menu bar text ends
    up unreadable when our light palette is installed. Fusion respects
    palettes fully and looks identical across platforms.
    """
    from PySide6.QtWidgets import QStyleFactory

    if app.style().objectName().lower() != "fusion":
        fusion = QStyleFactory.create("Fusion")
        if fusion is not None:
            app.setStyle(fusion)


def apply_light(app: QApplication) -> None:
    """Apply an explicit light palette with crisp text contrast."""
    _force_fusion_style(app)
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, _LIGHT_WINDOW)
    palette.setColor(QPalette.ColorRole.WindowText, _LIGHT_TEXT)
    palette.setColor(QPalette.ColorRole.Base, _LIGHT_BASE)
    palette.setColor(QPalette.ColorRole.AlternateBase, _LIGHT_ALT_BASE)
    palette.setColor(QPalette.ColorRole.Text, _LIGHT_TEXT)
    palette.setColor(QPalette.ColorRole.Button, _LIGHT_BUTTON)
    palette.setColor(QPalette.ColorRole.ButtonText, _LIGHT_TEXT)
    palette.setColor(QPalette.ColorRole.Highlight, _LIGHT_HIGHLIGHT)
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.ToolTipBase, _LIGHT_BASE)
    palette.setColor(QPalette.ColorRole.ToolTipText, _LIGHT_TEXT)
    palette.setColor(QPalette.ColorRole.Link, _LIGHT_LINK)

    for role in (
        QPalette.ColorRole.Text,
        QPalette.ColorRole.ButtonText,
        QPalette.ColorRole.WindowText,
    ):
        palette.setColor(QPalette.ColorGroup.Disabled, role, _LIGHT_DISABLED_TEXT)

    app.setPalette(palette)
    app.setStyleSheet(_LIGHT_QSS)


def apply_dark(app: QApplication) -> None:
    """Switch the application to a dark color scheme."""
    _force_fusion_style(app)
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
