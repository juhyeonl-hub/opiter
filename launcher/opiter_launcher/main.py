# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 juhyeonl
"""Launcher entry point — bootstraps QApplication and shows the wizard."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .wizard import LauncherWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Opiter Setup")
    app.setOrganizationName("Opiter")
    win = LauncherWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
