"""Application entry point: bootstraps QApplication and shows the main window."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from opiter.ui.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Opiter")
    app.setOrganizationName("Opiter")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
