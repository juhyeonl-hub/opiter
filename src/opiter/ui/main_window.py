"""Main application window: menus, toolbar, central viewer."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QInputDialog,
    QLabel,
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
        self._viewer.page_changed.connect(self._on_page_changed)

        self._page_indicator = QLabel("—")
        self._page_indicator.setMinimumWidth(80)
        self._page_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._build_actions()
        self._build_menus()
        self._build_toolbar()
        self.statusBar().showMessage("Ready")
        self._update_action_states()

    # ------------------------------------------------------------------ build
    def _build_actions(self) -> None:
        self._action_open = QAction("&Open…", self)
        self._action_open.setShortcut(QKeySequence.StandardKey.Open)
        self._action_open.triggered.connect(self._on_open)

        self._action_quit = QAction("&Quit", self)
        self._action_quit.setShortcut(QKeySequence.StandardKey.Quit)
        self._action_quit.triggered.connect(self.close)

        self._action_prev = QAction("&Previous Page", self)
        self._action_prev.setShortcut(QKeySequence(Qt.Key.Key_PageUp))
        self._action_prev.triggered.connect(self._viewer.prev_page)

        self._action_next = QAction("&Next Page", self)
        self._action_next.setShortcut(QKeySequence(Qt.Key.Key_PageDown))
        self._action_next.triggered.connect(self._viewer.next_page)

        self._action_first = QAction("&First Page", self)
        self._action_first.setShortcut(QKeySequence(Qt.Key.Key_Home))
        self._action_first.triggered.connect(self._viewer.first_page)

        self._action_last = QAction("&Last Page", self)
        self._action_last.setShortcut(QKeySequence(Qt.Key.Key_End))
        self._action_last.triggered.connect(self._viewer.last_page)

        self._action_goto = QAction("&Go to Page…", self)
        self._action_goto.setShortcut(QKeySequence("Ctrl+G"))
        self._action_goto.triggered.connect(self._on_goto_page)

        self._action_about = QAction("&About Opiter", self)
        self._action_about.triggered.connect(self._on_about)

    def _build_menus(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        file_menu.addAction(self._action_open)
        file_menu.addSeparator()
        file_menu.addAction(self._action_quit)

        view_menu = menubar.addMenu("&View")
        view_menu.addAction(self._action_prev)
        view_menu.addAction(self._action_next)
        view_menu.addAction(self._action_first)
        view_menu.addAction(self._action_last)
        view_menu.addSeparator()
        view_menu.addAction(self._action_goto)

        help_menu = menubar.addMenu("&Help")
        help_menu.addAction(self._action_about)

    def _build_toolbar(self) -> None:
        toolbar = self.addToolBar("Main")
        toolbar.setMovable(False)
        toolbar.addAction(self._action_open)
        toolbar.addSeparator()
        toolbar.addAction(self._action_prev)
        toolbar.addAction(self._action_next)
        toolbar.addWidget(self._page_indicator)

    # ----------------------------------------------------------------- slots
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

    def _on_page_changed(self, current: int, total: int) -> None:
        self._page_indicator.setText(f"{current + 1} / {total}" if total > 0 else "—")
        self._update_action_states()

    def _on_goto_page(self) -> None:
        if not self._viewer.has_document():
            return
        page, ok = QInputDialog.getInt(
            self,
            "Go to Page",
            f"Page (1 – {self._viewer.page_count}):",
            value=self._viewer.current_page + 1,
            minValue=1,
            maxValue=self._viewer.page_count,
        )
        if ok:
            self._viewer.goto_page(page - 1)

    def _on_about(self) -> None:
        QMessageBox.about(
            self,
            "About Opiter",
            f"Opiter v{__version__}\n\n"
            "Free and open-source PDF editor.\n"
            "MIT License © 2026 juhyeonl",
        )

    # ----------------------------------------------------------------- state
    def _update_action_states(self) -> None:
        has_doc = self._viewer.has_document()
        cur = self._viewer.current_page
        last = self._viewer.page_count - 1
        self._action_prev.setEnabled(has_doc and cur > 0)
        self._action_next.setEnabled(has_doc and cur < last)
        self._action_first.setEnabled(has_doc and cur > 0)
        self._action_last.setEnabled(has_doc and cur < last)
        self._action_goto.setEnabled(has_doc)
