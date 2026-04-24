"""Application entry point: bootstraps QApplication and shows the main window."""
from __future__ import annotations

import os
import sys

from PySide6.QtCore import qInstallMessageHandler, QtMsgType
from PySide6.QtWidgets import QApplication

# HiDPI: enable high-DPI pixmaps + per-monitor scaling. Must run before
# QApplication is constructed.
os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

from opiter.ui.main_window import MainWindow  # noqa: E402  (import after env)


# Known-benign Qt warnings we silently drop. Full message text on Linux/XCB:
#   "This plugin supports grabbing the mouse only for popup windows"
# (fires on rapid menu-bar hover under WSLg). Suppressing it keeps the
# terminal clean without hiding genuine Qt warnings.
_BENIGN_QT_WARNINGS: tuple[str, ...] = (
    "This plugin supports grabbing the mouse only for popup windows",
    "This plugin does not support propagateSizeHints",
)


def _qt_message_handler(msg_type, _context, message: str) -> None:
    if any(pat in message for pat in _BENIGN_QT_WARNINGS):
        return
    # Default-style passthrough.
    print(message, file=sys.stderr)


def main() -> None:
    qInstallMessageHandler(_qt_message_handler)

    app = QApplication(sys.argv)
    app.setApplicationName("Opiter")
    app.setOrganizationName("Opiter")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
