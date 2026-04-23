"""Main application window: menus, toolbar, central viewer."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMessageBox,
)

from opiter import __version__
from opiter.core.document import Document
from opiter.ui.viewer_widget import ViewerWidget
from opiter.utils.errors import CorruptedPDFError, EncryptedPDFError


class MainWindow(QMainWindow):
    """Top-level application window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Opiter")
        self.resize(1024, 768)

        self._viewer = ViewerWidget(self)
        self.setCentralWidget(self._viewer)

        self._action_open: QAction
        self._build_menus()
        self._build_toolbar()
        self.statusBar().showMessage("Ready")

    def _build_menus(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        self._action_open = QAction("&Open…", self)
        self._action_open.setShortcut(QKeySequence.StandardKey.Open)
        self._action_open.triggered.connect(self._on_open)
        file_menu.addAction(self._action_open)

        file_menu.addSeparator()
        action_quit = QAction("&Quit", self)
        action_quit.setShortcut(QKeySequence.StandardKey.Quit)
        action_quit.triggered.connect(self.close)
        file_menu.addAction(action_quit)

        # View menu — concrete actions land in Step 4 (zoom/fit/dark mode)
        menubar.addMenu("&View")

        help_menu = menubar.addMenu("&Help")
        action_about = QAction("&About Opiter", self)
        action_about.triggered.connect(self._on_about)
        help_menu.addAction(action_about)

    def _build_toolbar(self) -> None:
        toolbar = self.addToolBar("Main")
        toolbar.setMovable(False)
        toolbar.addAction(self._action_open)

    def _on_open(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(
            self,
            "Open PDF",
            str(Path.home()),
            "PDF files (*.pdf);;All files (*)",
        )
        if not path_str:
            return
        try:
            doc = Document.open(path_str)
        except EncryptedPDFError as exc:
            QMessageBox.warning(
                self,
                "Encrypted PDF",
                f"Password-protected PDFs are not yet supported.\n\n{exc}",
            )
            return
        except CorruptedPDFError as exc:
            QMessageBox.critical(
                self,
                "Cannot Open File",
                f"The file may be damaged or unsupported.\n\n{exc}",
            )
            return

        self._viewer.set_document(doc)
        self.setWindowTitle(f"Opiter — {Path(path_str).name}")
        self.statusBar().showMessage(f"Loaded {doc.page_count} page(s)")

    def _on_about(self) -> None:
        QMessageBox.about(
            self,
            "About Opiter",
            f"Opiter v{__version__}\n\n"
            "Free and open-source PDF editor.\n"
            "MIT License © 2026 juhyeonl",
        )
