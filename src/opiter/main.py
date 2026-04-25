# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 juhyeonl
"""Application entry point: bootstraps QApplication and shows the main window."""
from __future__ import annotations

import logging
import os
import sys
import traceback
from pathlib import Path

from PySide6.QtCore import qInstallMessageHandler, QtMsgType
from PySide6.QtWidgets import QApplication, QMessageBox

# HiDPI: enable high-DPI pixmaps + per-monitor scaling. Must run before
# QApplication is constructed.
os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")


def _log_dir() -> Path:
    """Best-effort writable log location per platform.

    Windows: %LOCALAPPDATA%\\Opiter\\
    macOS:   ~/Library/Logs/Opiter/
    Linux:   ${XDG_STATE_HOME:-~/.local/state}/opiter/
    """
    if sys.platform.startswith("win"):
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        d = Path(base) / "Opiter"
    elif sys.platform == "darwin":
        d = Path.home() / "Library" / "Logs" / "Opiter"
    else:
        d = Path(
            os.environ.get("XDG_STATE_HOME") or (Path.home() / ".local" / "state")
        ) / "opiter"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _setup_logging() -> Path:
    log_path = _log_dir() / "startup.log"
    logging.basicConfig(
        filename=str(log_path),
        filemode="w",  # truncate on each launch — only the latest run matters
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    return log_path


# Known-benign Qt warnings we silently drop. Full message text on Linux/XCB:
#   "This plugin supports grabbing the mouse only for popup windows"
# (fires on rapid menu-bar hover under WSLg). Suppressing it keeps the
# terminal clean without hiding genuine Qt warnings.
_BENIGN_QT_WARNINGS: tuple[str, ...] = (
    "This plugin supports grabbing the mouse only for popup windows",
    "This plugin does not support propagateSizeHints",
)


def _qt_message_handler(_msg_type, _context, message: str) -> None:
    if any(pat in message for pat in _BENIGN_QT_WARNINGS):
        return
    logging.getLogger("Qt").warning(message)


def main() -> None:
    log_path = _setup_logging()
    log = logging.getLogger("opiter")
    log.info("=== startup === platform=%s python=%s", sys.platform, sys.version)
    log.info("argv=%r", sys.argv)
    log.info("frozen=%s executable=%s", getattr(sys, "frozen", False), sys.executable)
    log.info("log_path=%s", log_path)

    # Hard backstop: any exception that escapes here would otherwise
    # silently exit on Windows windowed mode. Catch it, log it, then
    # surface a message box so the user knows something happened.
    def _excepthook(exc_type, exc, tb):
        msg = "".join(traceback.format_exception(exc_type, exc, tb))
        log.error("UNCAUGHT:\n%s", msg)
        try:
            QMessageBox.critical(
                None, "Opiter — startup error",
                f"{exc_type.__name__}: {exc}\n\nLog: {log_path}",
            )
        except Exception:
            pass

    sys.excepthook = _excepthook

    try:
        qInstallMessageHandler(_qt_message_handler)
        log.debug("qInstallMessageHandler done")

        app = QApplication(sys.argv)
        app.setApplicationName("Opiter")
        app.setOrganizationName("Opiter")
        log.debug("QApplication created")

        # Late import — keeps any failure inside MainWindow from blocking
        # log setup above.
        from opiter.ui.main_window import MainWindow

        log.debug("MainWindow imported")

        window = MainWindow()
        log.debug("MainWindow constructed")

        window.show()
        log.debug("window.show() done — entering event loop")

        rc = app.exec()
        log.info("app.exec() returned %s", rc)
        sys.exit(rc)
    except SystemExit:
        raise
    except Exception:
        log.exception("main() raised before event loop")
        # Best-effort dialog — may itself fail if QApplication never came up.
        try:
            QMessageBox.critical(
                None, "Opiter — startup error",
                f"Failed to start. See log: {log_path}",
            )
        except Exception:
            pass
        sys.exit(1)
