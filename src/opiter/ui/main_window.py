"""Main application window: menus, toolbar, central viewer."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QFileDialog,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from opiter import __version__
from opiter.core.document import Document
from opiter.core.search import SearchMatch, search
from opiter.ui.search_bar import SearchBar
from opiter.ui.theme import apply_dark, apply_light
from opiter.ui.thumbnail_panel import ThumbnailPanel
from opiter.ui.viewer_widget import ViewerWidget
from opiter.utils.errors import CorruptedPDFError, EncryptedPDFError


class MainWindow(QMainWindow):
    """Top-level application window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Opiter")
        self.resize(1024, 768)

        self._viewer = ViewerWidget(self)
        self._viewer.page_changed.connect(self._on_page_changed)
        self._viewer.zoom_changed.connect(self._on_zoom_changed)

        self._search_bar = SearchBar(self)
        self._search_bar.hide()
        self._search_bar.query_changed.connect(self._on_search_query_changed)
        self._search_bar.next_requested.connect(self._on_search_next)
        self._search_bar.prev_requested.connect(self._on_search_prev)
        self._search_bar.close_requested.connect(self._on_search_close)

        central = QWidget(self)
        vbox = QVBoxLayout(central)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)
        vbox.addWidget(self._viewer, stretch=1)
        vbox.addWidget(self._search_bar)
        self.setCentralWidget(central)

        self._search_results: list[SearchMatch] = []
        self._search_current: int = -1

        self._thumb_panel = ThumbnailPanel(self)
        self._thumb_panel.page_clicked.connect(self._viewer.goto_page)
        self._viewer.page_changed.connect(
            lambda current, _total: self._thumb_panel.select_page(current)
        )

        self._thumb_dock = QDockWidget("Pages", self)
        self._thumb_dock.setObjectName("ThumbnailsDock")
        self._thumb_dock.setWidget(self._thumb_panel)
        self._thumb_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self._thumb_dock)

        self._page_indicator = QLabel("—")
        self._page_indicator.setMinimumWidth(80)
        self._page_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._zoom_indicator = QLabel("100%")
        self._zoom_indicator.setMinimumWidth(60)
        self._zoom_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)

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

        self._action_save = QAction("&Save", self)
        self._action_save.setShortcut(QKeySequence.StandardKey.Save)
        self._action_save.triggered.connect(self._on_save)

        self._action_save_as = QAction("Save &As…", self)
        self._action_save_as.setShortcut(QKeySequence.StandardKey.SaveAs)
        self._action_save_as.triggered.connect(self._on_save_as)

        self._action_quit = QAction("&Quit", self)
        self._action_quit.setShortcut(QKeySequence.StandardKey.Quit)
        self._action_quit.triggered.connect(self.close)

        self._action_rotate_right = QAction("Rotate Page &Right", self)
        self._action_rotate_right.setShortcut(QKeySequence("Ctrl+R"))
        self._action_rotate_right.triggered.connect(self._on_rotate_right)

        self._action_rotate_left = QAction("Rotate Page &Left", self)
        self._action_rotate_left.setShortcut(QKeySequence("Ctrl+Shift+R"))
        self._action_rotate_left.triggered.connect(self._on_rotate_left)

        self._action_delete_page = QAction("&Delete Page", self)
        self._action_delete_page.setShortcut(QKeySequence("Ctrl+Delete"))
        self._action_delete_page.triggered.connect(self._on_delete_page)

        self._action_insert_blank = QAction("&Insert Blank Page After", self)
        self._action_insert_blank.triggered.connect(self._on_insert_blank_page)

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

        # Adobe/Foxit/Okular-style zoom shortcuts
        self._action_zoom_in = QAction("Zoom &In", self)
        self._action_zoom_in.setShortcuts(
            [QKeySequence.StandardKey.ZoomIn, QKeySequence("Ctrl+=")]
        )
        self._action_zoom_in.triggered.connect(self._viewer.zoom_in)

        self._action_zoom_out = QAction("Zoom &Out", self)
        self._action_zoom_out.setShortcut(QKeySequence.StandardKey.ZoomOut)
        self._action_zoom_out.triggered.connect(self._viewer.zoom_out)

        self._action_fit_page = QAction("Fit &Page", self)
        self._action_fit_page.setShortcut(QKeySequence("Ctrl+0"))
        self._action_fit_page.triggered.connect(self._viewer.fit_page)

        self._action_actual_size = QAction("&Actual Size (100%)", self)
        self._action_actual_size.setShortcut(QKeySequence("Ctrl+1"))
        self._action_actual_size.triggered.connect(self._viewer.reset_zoom)

        self._action_fit_width = QAction("Fit &Width", self)
        self._action_fit_width.setShortcut(QKeySequence("Ctrl+2"))
        self._action_fit_width.triggered.connect(self._viewer.fit_width)

        self._action_toggle_thumbs = self._thumb_dock.toggleViewAction()
        self._action_toggle_thumbs.setText("Show &Thumbnails")
        self._action_toggle_thumbs.setShortcut(QKeySequence(Qt.Key.Key_F4))

        self._action_dark_mode = QAction("&Dark Mode", self)
        self._action_dark_mode.setCheckable(True)
        self._action_dark_mode.setShortcut(QKeySequence("Ctrl+Shift+D"))
        self._action_dark_mode.toggled.connect(self._on_toggle_dark_mode)

        # Application-scope so the shortcuts fire even while focus is in the
        # SearchBar's QLineEdit child.
        self._action_find = QAction("&Find…", self)
        self._action_find.setShortcut(QKeySequence.StandardKey.Find)
        self._action_find.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        self._action_find.triggered.connect(self._on_find_open)

        self._action_find_next = QAction("Find &Next", self)
        self._action_find_next.setShortcut(QKeySequence(Qt.Key.Key_F3))
        self._action_find_next.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        self._action_find_next.triggered.connect(self._on_search_next)

        self._action_find_prev = QAction("Find &Previous", self)
        self._action_find_prev.setShortcut(QKeySequence("Shift+F3"))
        self._action_find_prev.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        self._action_find_prev.triggered.connect(self._on_search_prev)

        self._action_about = QAction("&About Opiter", self)
        self._action_about.triggered.connect(self._on_about)

    def _build_menus(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        file_menu.addAction(self._action_open)
        file_menu.addSeparator()
        file_menu.addAction(self._action_save)
        file_menu.addAction(self._action_save_as)
        file_menu.addSeparator()
        file_menu.addAction(self._action_quit)

        edit_menu = menubar.addMenu("&Edit")
        edit_menu.addAction(self._action_find)
        edit_menu.addAction(self._action_find_next)
        edit_menu.addAction(self._action_find_prev)
        edit_menu.addSeparator()
        edit_menu.addAction(self._action_rotate_right)
        edit_menu.addAction(self._action_rotate_left)
        edit_menu.addSeparator()
        edit_menu.addAction(self._action_insert_blank)
        edit_menu.addAction(self._action_delete_page)

        view_menu = menubar.addMenu("&View")
        view_menu.addAction(self._action_prev)
        view_menu.addAction(self._action_next)
        view_menu.addAction(self._action_first)
        view_menu.addAction(self._action_last)
        view_menu.addAction(self._action_goto)
        view_menu.addSeparator()
        view_menu.addAction(self._action_zoom_in)
        view_menu.addAction(self._action_zoom_out)
        view_menu.addSeparator()
        view_menu.addAction(self._action_fit_page)
        view_menu.addAction(self._action_actual_size)
        view_menu.addAction(self._action_fit_width)
        view_menu.addSeparator()
        view_menu.addAction(self._action_toggle_thumbs)
        view_menu.addAction(self._action_dark_mode)

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
        toolbar.addSeparator()
        toolbar.addAction(self._action_zoom_out)
        toolbar.addWidget(self._zoom_indicator)
        toolbar.addAction(self._action_zoom_in)

    # ----------------------------------------------------------------- slots
    def _on_open(self) -> None:
        if not self._confirm_discard_if_modified():
            return
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

        self._thumb_panel.set_document(doc)
        self._viewer.set_document(doc)
        self._thumb_panel.select_page(self._viewer.current_page)
        self._reset_search_state()
        self._refresh_title()
        self._update_action_states()
        self.statusBar().showMessage(f"Loaded {doc.page_count} page(s)")

    def _on_save(self) -> None:
        doc = self._viewer._doc  # noqa: SLF001
        if doc is None:
            return
        try:
            doc.save()
        except Exception as exc:
            QMessageBox.critical(self, "Save Failed", str(exc))
            return
        self._refresh_title()
        self.statusBar().showMessage(f"Saved to {doc.path}", 3000)

    def _on_save_as(self) -> None:
        doc = self._viewer._doc  # noqa: SLF001
        if doc is None:
            return
        path_str, _ = QFileDialog.getSaveFileName(
            self,
            "Save PDF As",
            str(doc.path),
            "PDF files (*.pdf);;All files (*)",
        )
        if not path_str:
            return
        try:
            doc.save_as(path_str)
        except Exception as exc:
            QMessageBox.critical(self, "Save Failed", str(exc))
            return
        # Thumbnails stay valid (same doc instance, same content); rebuild
        # so saved file's rotation etc. are reflected if user re-renders.
        self._thumb_panel.set_document(doc)
        self._thumb_panel.select_page(self._viewer.current_page)
        self._refresh_title()
        self.statusBar().showMessage(f"Saved to {doc.path}", 3000)

    def _on_rotate_right(self) -> None:
        self._rotate_current_page(90)

    def _on_rotate_left(self) -> None:
        self._rotate_current_page(-90)

    def _rotate_current_page(self, degrees: int) -> None:
        doc = self._viewer._doc  # noqa: SLF001
        if doc is None:
            return
        idx = self._viewer.current_page
        doc.rotate_page(idx, degrees)
        # Re-render current page and refresh its thumbnail
        self._viewer._render_current(scroll_to="top")  # noqa: SLF001
        self._thumb_panel.set_document(doc)
        self._thumb_panel.select_page(idx)
        self._refresh_title()
        self._update_action_states()

    def _on_delete_page(self) -> None:
        doc = self._viewer._doc  # noqa: SLF001
        if doc is None:
            return
        if doc.page_count == 1:
            QMessageBox.warning(
                self,
                "Cannot Delete",
                "A PDF must contain at least one page.",
            )
            return
        idx = self._viewer.current_page
        button = QMessageBox.question(
            self,
            "Delete Page",
            f"Delete page {idx + 1} of {doc.page_count}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if button != QMessageBox.StandardButton.Yes:
            return
        doc.delete_page(idx)
        self._thumb_panel.set_document(doc)
        self._viewer.reload_current()
        self._thumb_panel.select_page(self._viewer.current_page)
        self._reset_search_state()
        self._refresh_title()
        self._update_action_states()
        self.statusBar().showMessage(
            f"Deleted page {idx + 1}. Now showing page "
            f"{self._viewer.current_page + 1} of {doc.page_count}.",
            4000,
        )

    def _on_insert_blank_page(self) -> None:
        doc = self._viewer._doc  # noqa: SLF001
        if doc is None:
            return
        idx = self._viewer.current_page
        new_idx = doc.insert_blank_page(after_index=idx)
        self._thumb_panel.set_document(doc)
        self._viewer.goto_page(new_idx)
        self._thumb_panel.select_page(new_idx)
        self._reset_search_state()
        self._refresh_title()
        self._update_action_states()
        self.statusBar().showMessage(
            f"Inserted blank page at position {new_idx + 1}.", 4000
        )

    def _on_page_changed(self, current: int, total: int) -> None:
        self._page_indicator.setText(f"{current + 1} / {total}" if total > 0 else "—")
        self._update_action_states()

    def _on_zoom_changed(self, zoom: float) -> None:
        self._zoom_indicator.setText(f"{round(zoom * 100)}%")

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

    # ----------------------------------------------------------------- search
    def _on_find_open(self) -> None:
        if not self._viewer.has_document():
            return
        self._search_bar.focus_input()
        # If the input retains a query from a previous session, re-run the
        # search so highlights and Prev/Next/Enter work without forcing the
        # user to retype.
        existing = self._search_bar.query()
        if existing.strip() and not self._search_results:
            self._on_search_query_changed(existing)

    def _on_search_close(self) -> None:
        self._search_bar.hide()
        self._reset_search_state()

    def _on_search_query_changed(self, query: str) -> None:
        if not self._viewer.has_document():
            return
        self._search_results = (
            search(self._viewer_doc(), query) if query.strip() else []
        )
        if self._search_results:
            self._search_current = 0
            self._apply_search_highlights()
            self._jump_to_current_match()
        else:
            self._search_current = -1
            self._viewer.clear_search_highlights()
        self._search_bar.set_status(self._search_current, len(self._search_results))

    def _on_search_next(self) -> None:
        if not self._search_results:
            return
        self._search_current = (self._search_current + 1) % len(self._search_results)
        self._apply_search_highlights()
        self._jump_to_current_match()
        self._search_bar.set_status(self._search_current, len(self._search_results))

    def _on_search_prev(self) -> None:
        if not self._search_results:
            return
        self._search_current = (self._search_current - 1) % len(self._search_results)
        self._apply_search_highlights()
        self._jump_to_current_match()
        self._search_bar.set_status(self._search_current, len(self._search_results))

    def _reset_search_state(self) -> None:
        self._search_results = []
        self._search_current = -1
        self._viewer.clear_search_highlights()
        self._search_bar.set_status(-1, 0)

    def _apply_search_highlights(self) -> None:
        rects_by_page: dict[int, list[tuple[float, float, float, float]]] = {}
        for m in self._search_results:
            rects_by_page.setdefault(m.page_index, []).append(m.rect)
        current = None
        if 0 <= self._search_current < len(self._search_results):
            cur_match = self._search_results[self._search_current]
            within_page = sum(
                1 for m in self._search_results[: self._search_current]
                if m.page_index == cur_match.page_index
            )
            current = (cur_match.page_index, within_page)
        self._viewer.set_search_highlights(rects_by_page, current=current)

    def _jump_to_current_match(self) -> None:
        if not (0 <= self._search_current < len(self._search_results)):
            return
        target_page = self._search_results[self._search_current].page_index
        if target_page != self._viewer.current_page:
            self._viewer.goto_page(target_page)

    def _viewer_doc(self) -> Document:
        # Internal access — viewer always has a document at this point.
        return self._viewer._doc  # noqa: SLF001  (intentional for search hookup)

    def _on_toggle_dark_mode(self, checked: bool) -> None:
        app = QApplication.instance()
        if app is None:
            return
        if checked:
            apply_dark(app)
        else:
            apply_light(app)

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
        for act in (
            self._action_zoom_in,
            self._action_zoom_out,
            self._action_fit_page,
            self._action_actual_size,
            self._action_fit_width,
            self._action_find,
            self._action_find_next,
            self._action_find_prev,
            self._action_save_as,
            self._action_rotate_right,
            self._action_rotate_left,
            self._action_insert_blank,
        ):
            act.setEnabled(has_doc)
        doc = self._viewer._doc  # noqa: SLF001
        self._action_save.setEnabled(has_doc and doc is not None and doc.is_modified)
        self._action_delete_page.setEnabled(
            has_doc and doc is not None and doc.page_count > 1
        )

    # -------------------------------------------------------------- helpers
    def _refresh_title(self) -> None:
        doc = self._viewer._doc  # noqa: SLF001
        if doc is None:
            self.setWindowTitle("Opiter")
            return
        marker = " *" if doc.is_modified else ""
        self.setWindowTitle(f"Opiter — {doc.path.name}{marker}")
        self._update_action_states()

    def _confirm_discard_if_modified(self) -> bool:
        """Prompt before discarding unsaved changes. Return True to proceed."""
        doc = self._viewer._doc  # noqa: SLF001
        if doc is None or not doc.is_modified:
            return True
        button = QMessageBox.question(
            self,
            "Unsaved Changes",
            f"{doc.path.name} has unsaved changes. Save before continuing?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if button == QMessageBox.StandardButton.Save:
            self._on_save()
            return not doc.is_modified
        if button == QMessageBox.StandardButton.Discard:
            return True
        return False

    def closeEvent(self, event) -> None:  # noqa: N802  (Qt override)
        if self._confirm_discard_if_modified():
            event.accept()
        else:
            event.ignore()
