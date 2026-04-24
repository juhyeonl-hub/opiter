"""Main application window: menus, toolbar, central viewer."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
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
from opiter.core import annotations as anno
from opiter.core import preferences as prefs_mod
from opiter.core.document import Document
from opiter.core.page_ops import (
    extract_pages,
    merge_pdfs,
    parse_multi_range_spec,
    parse_page_range_spec,
    split_by_groups,
    split_per_page,
)
from opiter.core.preferences import Preferences
from opiter.core.search import SearchMatch, search
from opiter.ui.page_canvas import ToolMode
from opiter.ui.preferences_dialog import KeymapEntry, PreferencesDialog
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
        self._prefs: Preferences = prefs_mod.load()
        self.resize(self._prefs.window_width, self._prefs.window_height)
        if self._prefs.window_x is not None and self._prefs.window_y is not None:
            self.move(self._prefs.window_x, self._prefs.window_y)

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

        # Wire annotation-tool signals from PageCanvas
        canvas = self._viewer.page_canvas
        canvas.text_drag_finished.connect(self._on_text_drag_finished)
        canvas.canvas_clicked.connect(self._on_canvas_clicked)
        canvas.stroke_finished.connect(self._on_stroke_finished)
        canvas.rect_drag_finished.connect(self._on_rect_drag_finished)
        canvas.arrow_drag_finished.connect(self._on_arrow_drag_finished)
        canvas.pointer_clicked.connect(self._on_pointer_clicked)
        canvas.pointer_drag_finished.connect(self._on_pointer_drag_finished)

        # POINTER selection state
        self._selected_annot_xref: int | None = None
        self._selected_annot_page: int | None = None

        self._thumb_panel = ThumbnailPanel(self)
        self._thumb_panel.page_clicked.connect(self._viewer.goto_page)
        self._thumb_panel.pages_reordered.connect(self._on_pages_reordered)
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
        self._action_registry: list[tuple[KeymapEntry, QAction]] = (
            self._build_keymap_registry()
        )
        self._apply_keymap_overrides()
        self._build_menus()
        self._build_toolbar()
        self.statusBar().showMessage("Ready")
        self._update_action_states()
        self._apply_loaded_preferences()

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

        self._action_extract = QAction("E&xtract Pages…", self)
        self._action_extract.triggered.connect(self._on_extract_pages)

        self._action_split_ranges = QAction("Split PDF by &Range…", self)
        self._action_split_ranges.triggered.connect(self._on_split_by_ranges)

        self._action_split_per_page = QAction("Split PDF Per &Page", self)
        self._action_split_per_page.triggered.connect(self._on_split_per_page)

        self._action_merge = QAction("&Merge PDFs…", self)
        self._action_merge.triggered.connect(self._on_merge_pdfs)

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

        self._action_preferences = QAction("&Preferences…", self)
        self._action_preferences.setShortcut(QKeySequence("Ctrl+,"))
        self._action_preferences.triggered.connect(self._on_preferences)

        # ----- Annotation tool actions (mutually exclusive via QActionGroup) ---
        self._tool_group = QActionGroup(self)
        self._tool_group.setExclusive(True)

        self._action_tool_none = self._make_tool_action(
            "&Select (no tool)", ToolMode.NONE, "Esc", checked=True
        )
        self._action_tool_pointer = self._make_tool_action(
            "&Pointer (Select / Move / Delete)", ToolMode.POINTER
        )
        self._action_tool_highlight = self._make_tool_action(
            "&Highlight Text", ToolMode.HIGHLIGHT
        )
        self._action_tool_underline = self._make_tool_action(
            "&Underline Text", ToolMode.UNDERLINE
        )
        self._action_tool_strikeout = self._make_tool_action(
            "&Strikeout Text", ToolMode.STRIKEOUT
        )
        self._action_tool_note = self._make_tool_action(
            "Sticky &Note", ToolMode.NOTE
        )
        self._action_tool_pen = self._make_tool_action(
            "&Pen (Freehand)", ToolMode.PEN
        )
        self._action_tool_rect = self._make_tool_action(
            "&Rectangle", ToolMode.RECT
        )
        self._action_tool_ellipse = self._make_tool_action(
            "&Ellipse", ToolMode.ELLIPSE
        )
        self._action_tool_arrow = self._make_tool_action(
            "&Arrow", ToolMode.ARROW
        )
        self._action_tool_textbox = self._make_tool_action(
            "&Text Box", ToolMode.TEXTBOX
        )

        self._action_delete_selected_annot = QAction("Delete Selected &Annotation", self)
        self._action_delete_selected_annot.setShortcut(QKeySequence(Qt.Key.Key_Delete))
        self._action_delete_selected_annot.setShortcutContext(
            Qt.ShortcutContext.ApplicationShortcut
        )
        self._action_delete_selected_annot.triggered.connect(self._on_delete_selected_annot)
        self._action_delete_selected_annot.setEnabled(False)

    def _make_tool_action(
        self,
        text: str,
        mode: ToolMode,
        shortcut: str | None = None,
        checked: bool = False,
    ) -> QAction:
        action = QAction(text, self)
        action.setCheckable(True)
        action.setChecked(checked)
        if shortcut is not None:
            action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(lambda _checked, m=mode: self._set_tool(m))
        self._tool_group.addAction(action)
        return action

    def _build_menus(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        file_menu.addAction(self._action_open)
        self._menu_recent = file_menu.addMenu("Open &Recent")
        self._rebuild_recent_menu()
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
        edit_menu.addAction(self._action_preferences)
        edit_menu.addSeparator()
        edit_menu.addAction(self._action_rotate_right)
        edit_menu.addAction(self._action_rotate_left)
        edit_menu.addSeparator()
        edit_menu.addAction(self._action_insert_blank)
        edit_menu.addAction(self._action_delete_page)
        edit_menu.addSeparator()
        edit_menu.addAction(self._action_extract)
        edit_menu.addAction(self._action_split_ranges)
        edit_menu.addAction(self._action_split_per_page)
        edit_menu.addAction(self._action_merge)

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

        annotate_menu = menubar.addMenu("&Annotate")
        annotate_menu.addAction(self._action_tool_none)
        annotate_menu.addAction(self._action_tool_pointer)
        annotate_menu.addSeparator()
        annotate_menu.addAction(self._action_delete_selected_annot)
        annotate_menu.addSeparator()
        annotate_menu.addAction(self._action_tool_highlight)
        annotate_menu.addAction(self._action_tool_underline)
        annotate_menu.addAction(self._action_tool_strikeout)
        annotate_menu.addSeparator()
        annotate_menu.addAction(self._action_tool_note)
        annotate_menu.addAction(self._action_tool_pen)
        annotate_menu.addSeparator()
        annotate_menu.addAction(self._action_tool_rect)
        annotate_menu.addAction(self._action_tool_ellipse)
        annotate_menu.addAction(self._action_tool_arrow)
        annotate_menu.addAction(self._action_tool_textbox)

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
        self._open_path(path_str, confirm_discard=False)

    def _open_path(self, path_str: str, *, confirm_discard: bool = True) -> None:
        """Load the PDF at *path_str* into the viewer. Shared by the Open
        dialog and the Open Recent submenu.
        """
        if confirm_discard and not self._confirm_discard_if_modified():
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
        self._clear_annot_selection()
        self._refresh_title()
        self._update_action_states()
        # Update recent files (front of MRU) and refresh submenu
        prefs_mod.push_recent_file(self._prefs, path_str)
        self._rebuild_recent_menu()
        self.statusBar().showMessage(f"Loaded {doc.page_count} page(s)")

    # ---------------------------------------------------- Open Recent menu
    def _rebuild_recent_menu(self) -> None:
        if not hasattr(self, "_menu_recent"):
            return
        prefs_mod.prune_missing_recent_files(self._prefs)
        self._menu_recent.clear()
        if not self._prefs.recent_files:
            placeholder = QAction("(no recent files)", self)
            placeholder.setEnabled(False)
            self._menu_recent.addAction(placeholder)
            return
        for p in self._prefs.recent_files:
            name = Path(p).name
            action = QAction(name, self)
            action.setToolTip(p)
            action.triggered.connect(lambda _checked=False, path=p: self._open_path(path))
            self._menu_recent.addAction(action)
        self._menu_recent.addSeparator()
        clear = QAction("&Clear Recent", self)
        clear.triggered.connect(self._on_clear_recent)
        self._menu_recent.addAction(clear)

    def _on_clear_recent(self) -> None:
        self._prefs.recent_files.clear()
        self._rebuild_recent_menu()

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

    def _on_pages_reordered(self, new_order: list[int]) -> None:
        """The thumbnail panel was just reordered visually by the user.
        Apply the new order to the document and re-label items so each
        item ↔ doc-page mapping is the identity again."""
        doc = self._viewer._doc  # noqa: SLF001
        if doc is None:
            return
        # The viewer was showing some page (by old index). Find where it
        # sits in the new order so we can keep the user on the same
        # logical page.
        cur_old = self._viewer.current_page
        try:
            cur_new = new_order.index(cur_old)
        except ValueError:
            cur_new = 0

        doc.reorder_pages(new_order)
        self._thumb_panel.relabel_after_reorder()

        self._viewer._current_page = cur_new  # noqa: SLF001
        self._viewer.reload_current()
        self._thumb_panel.select_page(cur_new)
        self._reset_search_state()
        self._refresh_title()
        self._update_action_states()
        self.statusBar().showMessage("Page order updated.", 4000)

    def _on_extract_pages(self) -> None:
        doc = self._viewer._doc  # noqa: SLF001
        if doc is None:
            return
        spec, ok = QInputDialog.getText(
            self,
            "Extract Pages",
            f"Pages to extract (1 – {doc.page_count}, e.g. 1-3,5,7-9):",
        )
        if not ok or not spec.strip():
            return
        try:
            indices = parse_page_range_spec(spec, doc.page_count)
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid Page Range", str(exc))
            return
        default_name = f"{doc.path.stem}_extract.pdf"
        out_str, _ = QFileDialog.getSaveFileName(
            self,
            "Save Extracted Pages",
            str(doc.path.parent / default_name),
            "PDF files (*.pdf);;All files (*)",
        )
        if not out_str:
            return
        try:
            out = extract_pages(doc, indices, out_str)
        except Exception as exc:
            QMessageBox.critical(self, "Extract Failed", str(exc))
            return
        self.statusBar().showMessage(
            f"Extracted {len(indices)} page(s) to {out}", 5000
        )

    def _on_split_by_ranges(self) -> None:
        doc = self._viewer._doc  # noqa: SLF001
        if doc is None:
            return
        spec, ok = QInputDialog.getText(
            self,
            "Split PDF by Range",
            f"Page groups (use ; between groups, e.g. 1-3;4-7;8-{doc.page_count}):",
        )
        if not ok or not spec.strip():
            return
        try:
            groups = parse_multi_range_spec(spec, doc.page_count)
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid Page Range", str(exc))
            return
        out_dir = self._prompt_output_directory(
            f"{doc.path.stem}_split", "Split Output Directory"
        )
        if out_dir is None:
            return
        try:
            written = split_by_groups(doc, groups, out_dir, doc.path.stem)
        except Exception as exc:
            QMessageBox.critical(self, "Split Failed", str(exc))
            return
        QMessageBox.information(
            self,
            "Split Complete",
            f"Wrote {len(written)} file(s) to:\n{out_dir}",
        )

    def _on_merge_pdfs(self) -> None:
        # Merge does not require an open document — let the user pick
        # any PDFs to combine.
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select PDFs to Merge (in order)",
            str(Path.home()),
            "PDF files (*.pdf);;All files (*)",
        )
        if not paths:
            return
        if len(paths) < 2:
            QMessageBox.warning(
                self,
                "Need More Files",
                "Select at least two PDFs to merge.",
            )
            return
        default_out = str(Path(paths[0]).parent / "merged.pdf")
        out_str, _ = QFileDialog.getSaveFileName(
            self,
            "Save Merged PDF",
            default_out,
            "PDF files (*.pdf);;All files (*)",
        )
        if not out_str:
            return
        try:
            out = merge_pdfs(paths, out_str)
        except Exception as exc:
            QMessageBox.critical(self, "Merge Failed", str(exc))
            return
        QMessageBox.information(
            self,
            "Merge Complete",
            f"Merged {len(paths)} files into:\n{out}",
        )

    def _on_split_per_page(self) -> None:
        doc = self._viewer._doc  # noqa: SLF001
        if doc is None:
            return
        out_dir = self._prompt_output_directory(
            f"{doc.path.stem}_pages", "Per-Page Output Directory"
        )
        if out_dir is None:
            return
        try:
            written = split_per_page(doc, out_dir, doc.path.stem)
        except Exception as exc:
            QMessageBox.critical(self, "Split Failed", str(exc))
            return
        QMessageBox.information(
            self,
            "Split Complete",
            f"Wrote {len(written)} file(s) (one per page) to:\n{out_dir}",
        )

    def _prompt_output_directory(
        self, default_name: str, dialog_title: str
    ) -> str | None:
        """Ask the user for an output directory; create it if missing.

        Avoids QFileDialog.getExistingDirectory because that only allows
        selecting existing folders (the Choose button stays disabled when
        the user types a non-existent name) — the Qt "Create New Folder"
        button is too easy to miss.

        Returns the absolute path string, or ``None`` if the user
        cancelled or directory creation failed.
        """
        doc = self._viewer._doc  # noqa: SLF001
        suggested = (
            str(doc.path.parent / default_name) if doc is not None else default_name
        )
        out_str, ok = QInputDialog.getText(
            self,
            dialog_title,
            "Output directory (will be created if missing):",
            text=suggested,
        )
        if not ok or not out_str.strip():
            return None
        out_path = Path(out_str.strip()).expanduser()
        try:
            out_path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            QMessageBox.critical(self, "Cannot Create Directory", str(exc))
            return None
        return str(out_path)

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
        # Selection is page-scoped; clear when leaving its page.
        if (
            self._selected_annot_page is not None
            and self._selected_annot_page != current
        ):
            self._clear_annot_selection()
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

    # ----------------------------------------------------------- annotation tools
    def _set_tool(self, mode: ToolMode) -> None:
        if not self._viewer.has_document() and mode != ToolMode.NONE:
            self._action_tool_none.setChecked(True)
            return
        # Leaving POINTER clears any selection state
        if mode != ToolMode.POINTER:
            self._clear_annot_selection()
        self._viewer.page_canvas.set_tool(mode)
        self.statusBar().showMessage(
            f"Tool: {mode.name.title()}" if mode != ToolMode.NONE else "Ready",
            3000,
        )

    def _clear_annot_selection(self) -> None:
        self._selected_annot_xref = None
        self._selected_annot_page = None
        self._viewer.page_canvas.set_selection_rect(None)
        self._action_delete_selected_annot.setEnabled(False)

    def _on_pointer_clicked(self, pdf_point: tuple[float, float]) -> None:
        doc = self._viewer._doc  # noqa: SLF001
        if doc is None:
            return
        page_idx = self._viewer.current_page
        xref = anno.find_annotation_at(doc, page_idx, pdf_point)
        if xref is None:
            self._clear_annot_selection()
            self.statusBar().showMessage("No annotation at click point.", 2000)
            return
        self._selected_annot_xref = xref
        self._selected_annot_page = page_idx
        rect = anno.get_annotation_rect(doc, page_idx, xref)
        self._viewer.page_canvas.set_selection_rect(rect)
        self._action_delete_selected_annot.setEnabled(True)
        self.statusBar().showMessage(
            "Annotation selected — Delete to remove, drag inside box to move.",
            4000,
        )

    def _on_pointer_drag_finished(
        self,
        start_pdf: tuple[float, float],
        end_pdf: tuple[float, float],
    ) -> None:
        # Drag = move only if we have a selected annotation AND the drag
        # started inside its bounding box.
        if (
            self._selected_annot_xref is None
            or self._selected_annot_page is None
        ):
            return
        doc = self._viewer._doc  # noqa: SLF001
        if doc is None or self._selected_annot_page != self._viewer.current_page:
            return
        rect = anno.get_annotation_rect(
            doc, self._selected_annot_page, self._selected_annot_xref
        )
        if rect is None:
            return
        sx, sy = start_pdf
        if not (rect[0] <= sx <= rect[2] and rect[1] <= sy <= rect[3]):
            # User clicked outside the selection bbox to select something
            # else — already handled by _on_pointer_clicked. No move.
            return
        dx = end_pdf[0] - start_pdf[0]
        dy = end_pdf[1] - start_pdf[1]
        if abs(dx) < 1 and abs(dy) < 1:
            return  # tiny drag, ignore
        try:
            anno.move_annotation(
                doc, self._selected_annot_page, self._selected_annot_xref, dx, dy
            )
        except Exception as exc:
            QMessageBox.critical(self, "Move Failed", str(exc))
            return
        self._refresh_after_annotation()
        # Refresh selection box at the new position
        new_rect = anno.get_annotation_rect(
            doc, self._selected_annot_page, self._selected_annot_xref
        )
        self._viewer.page_canvas.set_selection_rect(new_rect)

    def _on_delete_selected_annot(self) -> None:
        if (
            self._selected_annot_xref is None
            or self._selected_annot_page is None
        ):
            return
        doc = self._viewer._doc  # noqa: SLF001
        if doc is None:
            return
        try:
            anno.delete_annotation(
                doc, self._selected_annot_page, self._selected_annot_xref
            )
        except Exception as exc:
            QMessageBox.critical(self, "Delete Failed", str(exc))
            return
        self._clear_annot_selection()
        self._refresh_after_annotation()

    def _refresh_after_annotation(self) -> None:
        """After a new annotation is added, re-render and update title/state."""
        # Re-render forces PyMuPDF to bake the new /Annot into the pixmap.
        self._viewer.reload_current()
        self._refresh_title()
        self._update_action_states()

    def _on_text_drag_finished(
        self, tool_value: int, pdf_rect: tuple[float, float, float, float]
    ) -> None:
        doc = self._viewer._doc  # noqa: SLF001
        if doc is None:
            return
        page_idx = self._viewer.current_page
        word_rects = anno.find_words_in_rect(doc, page_idx, pdf_rect)
        if not word_rects:
            self.statusBar().showMessage(
                "No text found in selection.", 3000
            )
            return
        try:
            tool = ToolMode(tool_value)
            if tool == ToolMode.HIGHLIGHT:
                anno.add_highlight(doc, page_idx, word_rects)
            elif tool == ToolMode.UNDERLINE:
                anno.add_underline(doc, page_idx, word_rects)
            elif tool == ToolMode.STRIKEOUT:
                anno.add_strikeout(doc, page_idx, word_rects)
            else:
                return
        except Exception as exc:
            QMessageBox.critical(self, "Annotation Failed", str(exc))
            return
        self._refresh_after_annotation()

    def _on_canvas_clicked(
        self, tool_value: int, pdf_point: tuple[float, float]
    ) -> None:
        doc = self._viewer._doc  # noqa: SLF001
        if doc is None or ToolMode(tool_value) != ToolMode.NOTE:
            return
        # If the user clicked an existing sticky note's icon, don't open a
        # second dialog — without this, every click on an icon spawns a
        # duplicate note. (Reading existing note content is a polish-stage
        # feature; for now the user can rely on an external PDF viewer.)
        if self._click_hits_existing_note(pdf_point):
            self.statusBar().showMessage(
                "Existing sticky note here. Open in another PDF viewer to read it.",
                4000,
            )
            return
        text, ok = QInputDialog.getMultiLineText(
            self, "Sticky Note", "Note text:", ""
        )
        if not ok or not text.strip():
            return
        try:
            anno.add_sticky_note(doc, self._viewer.current_page, pdf_point, text)
        except Exception as exc:
            QMessageBox.critical(self, "Annotation Failed", str(exc))
            return
        self._refresh_after_annotation()

    def _click_hits_existing_note(self, pdf_point: tuple[float, float]) -> bool:
        doc = self._viewer._doc  # noqa: SLF001
        if doc is None:
            return False
        page = doc.page(self._viewer.current_page)  # keep page alive in scope
        px, py = pdf_point
        for annot in page.annots():
            if annot.type[1] != "Text":
                continue
            r = annot.rect
            if r.x0 <= px <= r.x1 and r.y0 <= py <= r.y1:
                return True
        return False

    def _on_stroke_finished(self, stroke: list[tuple[float, float]]) -> None:
        doc = self._viewer._doc  # noqa: SLF001
        if doc is None or len(stroke) < 2:
            return
        try:
            anno.add_ink(doc, self._viewer.current_page, [stroke])
        except Exception as exc:
            QMessageBox.critical(self, "Annotation Failed", str(exc))
            return
        self._refresh_after_annotation()

    def _on_rect_drag_finished(
        self, tool_value: int, pdf_rect: tuple[float, float, float, float]
    ) -> None:
        doc = self._viewer._doc  # noqa: SLF001
        if doc is None:
            return
        page_idx = self._viewer.current_page
        try:
            tool = ToolMode(tool_value)
            if tool == ToolMode.RECT:
                anno.add_rect(doc, page_idx, pdf_rect)
            elif tool == ToolMode.ELLIPSE:
                anno.add_ellipse(doc, page_idx, pdf_rect)
            elif tool == ToolMode.TEXTBOX:
                text, ok = QInputDialog.getMultiLineText(
                    self, "Text Box", "Text:", ""
                )
                if not ok or not text.strip():
                    return
                anno.add_text_box(doc, page_idx, pdf_rect, text)
            else:
                return
        except Exception as exc:
            QMessageBox.critical(self, "Annotation Failed", str(exc))
            return
        self._refresh_after_annotation()

    def _on_arrow_drag_finished(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
    ) -> None:
        doc = self._viewer._doc  # noqa: SLF001
        if doc is None:
            return
        try:
            anno.add_arrow(doc, self._viewer.current_page, start, end)
        except Exception as exc:
            QMessageBox.critical(self, "Annotation Failed", str(exc))
            return
        self._refresh_after_annotation()

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
            self._action_extract,
            self._action_split_ranges,
            self._action_split_per_page,
            self._action_tool_highlight,
            self._action_tool_underline,
            self._action_tool_strikeout,
            self._action_tool_note,
            self._action_tool_pen,
            self._action_tool_rect,
            self._action_tool_ellipse,
            self._action_tool_arrow,
            self._action_tool_textbox,
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
        if not self._confirm_discard_if_modified():
            event.ignore()
            return
        try:
            self._capture_preferences()
            prefs_mod.save(self._prefs)
        except Exception:
            # Never block close on a preferences write failure.
            pass
        event.accept()

    # ------------------------------------------------------------- keymap
    def _build_keymap_registry(self) -> list[tuple[KeymapEntry, QAction]]:
        """List of ((id, label, default_shortcut), action) for every action
        the user is allowed to rebind. Default shortcut is captured BEFORE
        ``_apply_keymap_overrides`` mutates the actions."""
        spec: list[tuple[str, str, QAction]] = [
            # File
            ("file.open", "Open File", self._action_open),
            ("file.save", "Save", self._action_save),
            ("file.save_as", "Save As", self._action_save_as),
            ("file.quit", "Quit", self._action_quit),
            # Edit
            ("edit.find", "Find", self._action_find),
            ("edit.find_next", "Find Next", self._action_find_next),
            ("edit.find_prev", "Find Previous", self._action_find_prev),
            ("edit.preferences", "Preferences", self._action_preferences),
            ("edit.rotate_right", "Rotate Page Right", self._action_rotate_right),
            ("edit.rotate_left", "Rotate Page Left", self._action_rotate_left),
            ("edit.delete_page", "Delete Page", self._action_delete_page),
            # View — navigation
            ("view.prev_page", "Previous Page", self._action_prev),
            ("view.next_page", "Next Page", self._action_next),
            ("view.first_page", "First Page", self._action_first),
            ("view.last_page", "Last Page", self._action_last),
            ("view.goto_page", "Go to Page", self._action_goto),
            # View — zoom
            ("view.zoom_in", "Zoom In", self._action_zoom_in),
            ("view.zoom_out", "Zoom Out", self._action_zoom_out),
            ("view.fit_page", "Fit Page", self._action_fit_page),
            ("view.actual_size", "Actual Size", self._action_actual_size),
            ("view.fit_width", "Fit Width", self._action_fit_width),
            # View — layout/theme
            ("view.toggle_thumbs", "Show Thumbnails", self._action_toggle_thumbs),
            ("view.dark_mode", "Dark Mode", self._action_dark_mode),
            # Annotate — tools
            ("annotate.tool_none", "Tool: Select", self._action_tool_none),
            ("annotate.tool_pointer", "Tool: Pointer", self._action_tool_pointer),
            ("annotate.tool_highlight", "Tool: Highlight", self._action_tool_highlight),
            ("annotate.tool_underline", "Tool: Underline", self._action_tool_underline),
            ("annotate.tool_strikeout", "Tool: Strikeout", self._action_tool_strikeout),
            ("annotate.tool_note", "Tool: Sticky Note", self._action_tool_note),
            ("annotate.tool_pen", "Tool: Pen", self._action_tool_pen),
            ("annotate.tool_rect", "Tool: Rectangle", self._action_tool_rect),
            ("annotate.tool_ellipse", "Tool: Ellipse", self._action_tool_ellipse),
            ("annotate.tool_arrow", "Tool: Arrow", self._action_tool_arrow),
            ("annotate.tool_textbox", "Tool: Text Box", self._action_tool_textbox),
            ("annotate.delete_selected", "Delete Selected Annotation",
             self._action_delete_selected_annot),
        ]
        return [
            (
                KeymapEntry(
                    action_id=aid,
                    display_name=label,
                    default_shortcut=action.shortcut().toString(),
                ),
                action,
            )
            for aid, label, action in spec
        ]

    def _apply_keymap_overrides(self) -> None:
        """Apply per-action shortcut overrides from preferences."""
        for entry, action in self._action_registry:
            override = self._prefs.keymap.get(entry.action_id)
            if override:
                action.setShortcut(QKeySequence(override))

    def _on_preferences(self) -> None:
        entries = [e for e, _ in self._action_registry]
        dlg = PreferencesDialog(entries, dict(self._prefs.keymap), self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        new_overrides = dlg.get_overrides()
        self._prefs.keymap = new_overrides
        # Re-apply: first reset every action to its captured default,
        # then layer overrides on top.
        for entry, action in self._action_registry:
            action.setShortcut(QKeySequence(entry.default_shortcut))
        self._apply_keymap_overrides()
        try:
            prefs_mod.save(self._prefs)
        except Exception:
            pass
        self.statusBar().showMessage("Keyboard shortcuts updated.", 4000)

    # -------------------------------------------------------- preferences
    def _apply_loaded_preferences(self) -> None:
        """Apply ``self._prefs`` to UI state after all widgets are built."""
        # Dark mode
        if self._prefs.dark_mode:
            self._action_dark_mode.setChecked(True)  # triggers toggled → apply_dark
        # Dock visibility + area
        if not self._prefs.dock_visible:
            self._thumb_dock.hide()
        if self._prefs.dock_area == "right":
            self.removeDockWidget(self._thumb_dock)
            self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._thumb_dock)
            if self._prefs.dock_visible:
                self._thumb_dock.show()
        # Maximized state takes precedence over size/pos if set
        if self._prefs.window_maximized:
            self.showMaximized()

    def _capture_preferences(self) -> None:
        """Copy current UI state into ``self._prefs`` (pre-save)."""
        self._prefs.window_maximized = self.isMaximized()
        if not self.isMaximized():
            self._prefs.window_width = self.width()
            self._prefs.window_height = self.height()
            self._prefs.window_x = self.x()
            self._prefs.window_y = self.y()
        self._prefs.dock_visible = self._thumb_dock.isVisible()
        dock_area = self.dockWidgetArea(self._thumb_dock)
        if dock_area == Qt.DockWidgetArea.RightDockWidgetArea:
            self._prefs.dock_area = "right"
        else:
            self._prefs.dock_area = "left"
        self._prefs.dark_mode = self._action_dark_mode.isChecked()
