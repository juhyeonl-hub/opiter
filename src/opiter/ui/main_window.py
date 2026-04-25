# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 juhyeonl
"""Main application window: menus, toolbar, central viewer."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QKeySequence,
    QUndoGroup,
    QUndoStack,
)
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QSlider,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from opiter import __version__
from opiter.core import annotations as anno
from opiter.core import preferences as prefs_mod
from opiter.core.compression import compress_pdf
from opiter.core.document import Document
from opiter.core.image_export import export_pages_as_images
from opiter.core.image_to_pdf import images_to_pdf
from opiter.core.metadata import read_metadata, write_metadata
from opiter.core.page_ops import (
    extract_pages,
    merge_pdfs,
    parse_multi_range_spec,
    parse_page_range_spec,
    split_by_groups,
    split_per_page,
)
from opiter.core.pdf_to_docx import pdf_to_docx
from opiter.core.pdf_to_hwp import hwp_conversion_available, pdf_to_hwp
from opiter.core.preferences import Preferences
from opiter.core.search import SearchMatch, search
from opiter.core.toc import read_toc, write_toc
from opiter.core.undo import SnapshotCommand
from opiter.core.watermark import add_text_watermark
from opiter.ui.bookmarks_panel import BookmarksPanel
from opiter.ui.editors.docx_editor import DOCXEditor
from opiter.ui.editors.hwp_editor import HWPEditor
from opiter.ui.export_dialog import ExportOptionsDialog
from opiter.ui.metadata_dialog import MetadataDialog
from opiter.ui.page_canvas import ToolMode
from opiter.ui.preferences_dialog import ColorEntry, KeymapEntry, PreferencesDialog
from opiter.ui.search_bar import SearchBar
from opiter.ui.smooth_tab_bar import SmoothTabBar
from opiter.ui.theme import apply_dark, apply_light
from opiter.ui.thumbnail_panel import ThumbnailPanel
from opiter.ui.viewer_widget import ViewerWidget
from opiter.ui.watermark_dialog import WatermarkDialog
from opiter.utils.errors import CorruptedPDFError, EncryptedPDFError


class _PDFTabHolder(QWidget):
    """Per-PDF-tab state container.

    The widget itself is a thin placeholder; the visible PDF chrome
    (the splitter with thumbnails / viewer / bookmarks) is reparented
    into this widget's layout when the tab becomes active. State that
    has to survive tab switches (Document, undo stack, current page,
    zoom, scroll, search, selection) lives on this object.
    """

    def __init__(self, doc: Document, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.doc: Document = doc
        # Per-PDF undo stack — added to the window's QUndoGroup so the
        # global undo/redo actions auto-route to whichever stack is
        # active.
        self.undo_stack: QUndoStack = QUndoStack()
        self.undo_stack.setUndoLimit(30)
        # Viewer state captured on tab deactivate, restored on activate.
        self.current_page: int = 0
        self.zoom: float = 1.0
        self.scroll_x: int = 0
        self.scroll_y: int = 0
        # Search state
        self.search_query: str = ""
        self.search_results: list = []  # SearchMatch objects
        self.search_current: int = -1
        # POINTER selection state
        self.selected_annot_xref: int | None = None
        self.selected_annot_page: int | None = None
        # Empty layout — chrome splitter is mounted here on activate.
        self._holder_layout = QVBoxLayout(self)
        self._holder_layout.setContentsMargins(0, 0, 0, 0)
        self._holder_layout.setSpacing(0)


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

        # Two-level tab structure. Outer = format (PDF/DOCX/HWP); inner =
        # files within that format. Format tabs are added only when a file
        # of that type is open, and removed when the last one closes.
        # PDF inner tabs are :class:`_PDFTabHolder` widgets — empty
        # placeholders that own per-document state (Document, undo stack,
        # zoom/scroll/page); the visible PDF chrome (splitter with
        # thumbs / viewer / bookmarks) is reparented into whichever
        # holder is active so we only render one PDF at a time.
        self._pdf_file_tabs = QTabWidget(self)
        self._pdf_file_tabs.setTabBar(SmoothTabBar(self._pdf_file_tabs))
        self._pdf_file_tabs.setTabsClosable(True)
        self._pdf_file_tabs.setMovable(True)
        self._pdf_file_tabs.tabCloseRequested.connect(self._on_pdf_tab_close)
        self._pdf_file_tabs.currentChanged.connect(
            self._on_pdf_inner_tab_changed
        )
        # Tracks the holder currently mounted in the PDF chrome. Used to
        # save state out of the viewer before swapping to a new tab.
        self._active_pdf_holder: _PDFTabHolder | None = None

        self._docx_file_tabs = QTabWidget(self)
        self._docx_file_tabs.setTabBar(SmoothTabBar(self._docx_file_tabs))
        self._docx_file_tabs.setTabsClosable(True)
        self._docx_file_tabs.setMovable(True)
        self._docx_file_tabs.tabCloseRequested.connect(self._on_docx_tab_close)

        self._hwp_file_tabs = QTabWidget(self)
        self._hwp_file_tabs.setTabBar(SmoothTabBar(self._hwp_file_tabs))
        self._hwp_file_tabs.setTabsClosable(True)
        self._hwp_file_tabs.setMovable(True)
        self._hwp_file_tabs.tabCloseRequested.connect(self._on_hwp_tab_close)

        self._format_tabs = QTabWidget(self)
        self._format_tabs.setTabBar(SmoothTabBar(self._format_tabs))
        self._format_tabs.setTabsClosable(True)
        self._format_tabs.setMovable(True)
        self._format_tabs.currentChanged.connect(self._on_format_changed)
        self._format_tabs.tabCloseRequested.connect(self._on_format_tab_close)
        self.setCentralWidget(self._format_tabs)

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

        # Undo/redo
        # Each open PDF gets its own QUndoStack added to this group; the
        # group's createUndoAction wires the menu item to whatever stack
        # is currently active, so tab switches don't need to rewire.
        self._undo_group = QUndoGroup(self)

        self._thumb_panel = ThumbnailPanel(
            self, thumb_width=self._prefs.thumbnail_width_px
        )
        self._thumb_panel.page_clicked.connect(self._viewer.goto_page)
        self._thumb_panel.pages_reordered.connect(self._on_pages_reordered)
        self._viewer.page_changed.connect(
            lambda current, _total: self._thumb_panel.select_page(current)
        )

        # Thumbnail size slider sits above the list in the dock container.
        self._thumb_size_slider = QSlider(Qt.Orientation.Horizontal)
        from opiter.ui.thumbnail_panel import THUMB_WIDTH_MIN, THUMB_WIDTH_MAX
        self._thumb_size_slider.setRange(THUMB_WIDTH_MIN, THUMB_WIDTH_MAX)
        self._thumb_size_slider.setValue(self._prefs.thumbnail_width_px)
        self._thumb_size_slider.setToolTip("Thumbnail size")
        self._thumb_size_slider.valueChanged.connect(self._on_thumb_size_changed)

        # Thumbnail container (slider + list) lives inside the PDF tab,
        # not as a QDockWidget around the central area — that way the
        # outer format-tab line stays at a fixed position and panels
        # appear under it instead of beside the whole window.
        self._thumb_container = QWidget(self)
        _thumb_layout = QVBoxLayout(self._thumb_container)
        _thumb_layout.setContentsMargins(4, 4, 4, 4)
        _thumb_layout.setSpacing(4)
        _thumb_layout.addWidget(self._thumb_size_slider)
        _thumb_layout.addWidget(self._thumb_panel, stretch=1)

        # Bookmarks panel (Phase 4: 9-6) — also inline, hidden by default.
        self._bookmarks_panel = BookmarksPanel(self)
        self._bookmarks_panel.page_jump_requested.connect(self._viewer.goto_page)
        self._bookmarks_panel.toc_changed.connect(self._on_toc_changed)
        self._bookmarks_panel.hide()

        # The "PDF chrome" (thumbs | viewer+searchbar | bookmarks) is a
        # free-floating splitter — it gets reparented into whichever PDF
        # inner tab (a :class:`_PDFTabHolder`) is currently active.
        _viewer_holder = QWidget(self)
        _viewer_layout = QVBoxLayout(_viewer_holder)
        _viewer_layout.setContentsMargins(0, 0, 0, 0)
        _viewer_layout.setSpacing(0)
        _viewer_layout.addWidget(self._viewer, stretch=1)
        _viewer_layout.addWidget(self._search_bar)

        self._pdf_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self._pdf_splitter.addWidget(self._thumb_container)
        self._pdf_splitter.addWidget(_viewer_holder)
        self._pdf_splitter.addWidget(self._bookmarks_panel)
        self._pdf_splitter.setStretchFactor(0, 0)
        self._pdf_splitter.setStretchFactor(1, 1)
        self._pdf_splitter.setStretchFactor(2, 0)
        self._pdf_splitter.setSizes([200, 800, 220])
        # Hidden until mounted into an active holder.
        self._pdf_splitter.hide()

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
        # No document open on startup — apply the "nothing-open" visual state.
        self._on_format_changed(self._format_tabs.currentIndex())
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

        self._action_toggle_thumbs = QAction("Show &Thumbnails", self)
        self._action_toggle_thumbs.setCheckable(True)
        self._action_toggle_thumbs.setChecked(True)
        self._action_toggle_thumbs.setShortcut(QKeySequence(Qt.Key.Key_F4))
        self._action_toggle_thumbs.toggled.connect(self._thumb_container.setVisible)

        self._action_toggle_bookmarks = QAction("Show &Bookmarks", self)
        self._action_toggle_bookmarks.setCheckable(True)
        self._action_toggle_bookmarks.setChecked(False)
        self._action_toggle_bookmarks.toggled.connect(
            self._bookmarks_panel.setVisible
        )
        self._action_toggle_bookmarks.setShortcut(QKeySequence(Qt.Key.Key_F5))

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

        self._action_install_libreoffice = QAction(
            "&Install LibreOffice for full DOCX/HWP rendering…", self
        )
        self._action_install_libreoffice.triggered.connect(
            self._on_install_libreoffice_menu
        )

        self._action_preferences = QAction("&Preferences…", self)
        self._action_preferences.setShortcut(QKeySequence("Ctrl+,"))
        self._action_preferences.triggered.connect(self._on_preferences)

        # Phase 4: advanced PDF features
        self._action_export_images = QAction("Export Pages as &Images…", self)
        self._action_export_images.triggered.connect(self._on_export_images)

        self._action_images_to_pdf = QAction("Create PDF from I&mages…", self)
        self._action_images_to_pdf.triggered.connect(self._on_images_to_pdf)

        self._action_compress = QAction("Save &Compressed Copy…", self)
        self._action_compress.triggered.connect(self._on_compress)

        self._action_watermark = QAction("Add &Watermark…", self)
        self._action_watermark.triggered.connect(self._on_watermark)

        self._action_metadata = QAction("Document &Properties…", self)
        self._action_metadata.triggered.connect(self._on_metadata)

        # Phase 5: cross-format export
        self._action_export_docx = QAction("Export as &DOCX…", self)
        self._action_export_docx.triggered.connect(self._on_export_docx)

        self._action_export_hwp = QAction("Export as &HWP…", self)
        self._action_export_hwp.triggered.connect(self._on_export_hwp)
        if not hwp_conversion_available():
            self._action_export_hwp.setToolTip(
                "Requires LibreOffice + the h2orestart extension (for HWP export)."
            )

        # Undo / Redo come from the stack so their text auto-includes the
        # command label, and they enable/disable correctly.
        self._action_undo = self._undo_group.createUndoAction(self, "&Undo")
        self._action_undo.setShortcut(QKeySequence.StandardKey.Undo)
        self._action_redo = self._undo_group.createRedoAction(self, "&Redo")
        self._action_redo.setShortcuts(
            [QKeySequence.StandardKey.Redo, QKeySequence("Ctrl+Y")]
        )

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
        file_menu.addAction(self._action_compress)
        file_menu.addSeparator()
        file_menu.addAction(self._action_export_images)
        file_menu.addAction(self._action_images_to_pdf)
        file_menu.addAction(self._action_export_docx)
        file_menu.addAction(self._action_export_hwp)
        file_menu.addSeparator()
        file_menu.addAction(self._action_metadata)
        file_menu.addSeparator()
        file_menu.addAction(self._action_quit)

        edit_menu = menubar.addMenu("&Edit")
        edit_menu.addAction(self._action_undo)
        edit_menu.addAction(self._action_redo)
        edit_menu.addSeparator()
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
        edit_menu.addSeparator()
        edit_menu.addAction(self._action_watermark)

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
        view_menu.addAction(self._action_toggle_bookmarks)
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
        help_menu.addAction(self._action_install_libreoffice)
        help_menu.addSeparator()
        help_menu.addAction(self._action_about)

    def _build_toolbar(self) -> None:
        # ---------------------------------------------------- Welcome (empty)
        welcome_toolbar = self.addToolBar("Welcome")
        welcome_toolbar.setObjectName("WelcomeToolbar")
        welcome_toolbar.setMovable(False)
        welcome_toolbar.addAction(self._action_open)
        welcome_toolbar.addSeparator()
        welcome_toolbar.addWidget(
            QLabel("No document — File → Open (Ctrl+O) to begin.")
        )
        self._welcome_toolbar = welcome_toolbar

        # ------------------------------------------------------------- PDF
        toolbar = self.addToolBar("Main")
        toolbar.setObjectName("MainToolbar")
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
        self._main_toolbar = toolbar

        # Annotation tools get their own toolbar below the main one.
        anno_toolbar = self.addToolBar("Annotate")
        anno_toolbar.setObjectName("AnnotateToolbar")
        anno_toolbar.setMovable(True)
        anno_toolbar.addAction(self._action_tool_none)
        anno_toolbar.addAction(self._action_tool_pointer)
        anno_toolbar.addSeparator()
        anno_toolbar.addAction(self._action_tool_highlight)
        anno_toolbar.addAction(self._action_tool_underline)
        anno_toolbar.addAction(self._action_tool_strikeout)
        anno_toolbar.addSeparator()
        anno_toolbar.addAction(self._action_tool_note)
        anno_toolbar.addAction(self._action_tool_pen)
        anno_toolbar.addSeparator()
        anno_toolbar.addAction(self._action_tool_rect)
        anno_toolbar.addAction(self._action_tool_ellipse)
        anno_toolbar.addAction(self._action_tool_arrow)
        anno_toolbar.addAction(self._action_tool_textbox)
        anno_toolbar.addSeparator()
        anno_toolbar.addAction(self._action_delete_selected_annot)
        self._anno_toolbar = anno_toolbar

        # ------------------------------------------------------------- DOCX
        docx_toolbar = self.addToolBar("DOCX")
        docx_toolbar.setObjectName("DocxToolbar")
        docx_toolbar.setMovable(False)
        docx_toolbar.addAction(self._action_open)
        docx_toolbar.addSeparator()
        docx_toolbar.addWidget(QLabel("DOCX viewer — read-only (MVP)"))
        self._docx_toolbar = docx_toolbar
        docx_toolbar.hide()

        # ------------------------------------------------------------- HWP
        hwp_toolbar = self.addToolBar("HWP")
        hwp_toolbar.setObjectName("HwpToolbar")
        hwp_toolbar.setMovable(False)
        hwp_toolbar.addAction(self._action_open)
        hwp_toolbar.addSeparator()
        hwp_toolbar.addWidget(QLabel("HWP viewer — text-only (MVP)"))
        self._hwp_toolbar = hwp_toolbar
        hwp_toolbar.hide()

    # ----------------------------------------------------------------- slots
    def _on_open(self) -> None:
        # Don't prompt about unsaved PDF changes here — DOCX/HWP files
        # spawn a new tab without touching the open PDF, so the prompt
        # would be misleading. ``_open_path`` will prompt only when the
        # picked file is a PDF that would replace the current document.
        path_str, _ = QFileDialog.getOpenFileName(
            self,
            "Open Document",
            str(Path.home()),
            "All supported (*.pdf *.docx *.hwp);;PDF files (*.pdf);;"
            "Word documents (*.docx);;HWP documents (*.hwp);;All files (*)",
        )
        if not path_str:
            return
        self._open_path(path_str, confirm_discard=True)

    def _open_path(self, path_str: str, *, confirm_discard: bool = True) -> None:
        """Load a document at *path_str*. PDF replaces the PDF tab; DOCX
        and HWP each spawn a new tab. Encrypted PDFs prompt for a password.
        """
        ext = Path(path_str).suffix.lower()
        if ext == ".docx":
            self._open_docx_tab(path_str)
            return
        if ext == ".hwp":
            self._open_hwp_tab(path_str)
            return

        # PDF dedup: if the same file is already open in some inner tab,
        # focus it instead of loading a second copy.
        try:
            target = Path(path_str).resolve()
        except OSError:
            target = Path(path_str)
        for i in range(self._pdf_file_tabs.count()):
            holder = self._pdf_file_tabs.widget(i)
            if isinstance(holder, _PDFTabHolder):
                try:
                    cur = holder.doc.path.resolve()
                except OSError:
                    cur = holder.doc.path
                if cur == target:
                    self._pdf_file_tabs.setCurrentIndex(i)
                    self._format_tabs.setCurrentWidget(self._pdf_file_tabs)
                    return
        doc: Document | None = None
        password: str | None = None
        for _ in range(4):  # original attempt + up to 3 password retries
            try:
                doc = Document.open(path_str, password=password)
                break
            except EncryptedPDFError:
                pwd, ok = QInputDialog.getText(
                    self,
                    "Password Required",
                    f"{Path(path_str).name} is password-protected.\nEnter password:",
                    QLineEdit.EchoMode.Password,
                )
                if not ok:
                    return
                password = pwd
                continue
            except CorruptedPDFError as exc:
                QMessageBox.critical(
                    self,
                    "Cannot Open File",
                    f"The file may be damaged or unsupported.\n\n{exc}",
                )
                return
        else:
            QMessageBox.warning(
                self,
                "Wrong Password",
                "Too many incorrect attempts.",
            )
            return
        if doc is None:
            return

        # New holder for this document.
        holder = _PDFTabHolder(doc, self)
        self._undo_group.addStack(holder.undo_stack)
        self._ensure_format_tab(self._pdf_file_tabs, "PDF")
        self._format_tabs.setCurrentWidget(self._pdf_file_tabs)
        idx = self._pdf_file_tabs.addTab(holder, doc.path.name)
        # setCurrentIndex fires _on_pdf_inner_tab_changed which mounts
        # the chrome and loads state into the viewer.
        self._pdf_file_tabs.setCurrentIndex(idx)
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
        label = f"Rotate page {idx + 1} {'right' if degrees > 0 else 'left'}"
        self._push_undo(label, lambda: doc.rotate_page(idx, degrees))

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
        self._reset_search_state()
        self._push_undo(f"Delete page {idx + 1}", lambda: doc.delete_page(idx))
        self.statusBar().showMessage(f"Deleted page {idx + 1}.", 3000)

    def _on_pages_reordered(self, new_order: list[int]) -> None:
        """User drag-reordered the thumbnails. Apply via undoable command."""
        doc = self._viewer._doc  # noqa: SLF001
        if doc is None:
            return
        self._reset_search_state()
        self._push_undo(
            "Reorder pages", lambda: doc.reorder_pages(new_order)
        )
        self.statusBar().showMessage("Page order updated.", 3000)

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
        """Ask the user for an output directory via the native file browser.

        Opens ``QFileDialog.getExistingDirectory`` — it lets the user
        navigate the filesystem and create a new folder with the dialog's
        "New Folder" button. If the chosen directory doesn't yet exist it
        is created here (defensive).

        Returns the absolute path string, or ``None`` if the user
        cancelled or directory creation failed.
        """
        doc = self._viewer._doc  # noqa: SLF001
        start_dir = (
            str(doc.path.parent / default_name) if doc is not None else default_name
        )
        out_str = QFileDialog.getExistingDirectory(
            self,
            dialog_title,
            start_dir,
            QFileDialog.Option.ShowDirsOnly,
        )
        if not out_str:
            return None
        out_path = Path(out_str).expanduser()
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
        self._reset_search_state()
        self._push_undo(
            f"Insert blank page after {idx + 1}",
            lambda: doc.insert_blank_page(after_index=idx),
        )
        self.statusBar().showMessage("Inserted blank page.", 3000)

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
        page = self._selected_annot_page
        xref = self._selected_annot_xref
        self._push_undo(
            "Move annotation",
            lambda: anno.move_annotation(doc, page, xref, dx, dy),
        )
        # After the move the annotation's xref may have changed (ink annots
        # get deleted and recreated because PyMuPDF refuses set_rect on them).
        # Re-acquire the selection by hit-testing at the drag end point,
        # which is guaranteed to fall inside the moved bbox.
        new_xref = anno.find_annotation_at(doc, page, end_pdf)
        if new_xref is not None:
            self._selected_annot_xref = new_xref
            new_rect = anno.get_annotation_rect(doc, page, new_xref)
            self._viewer.page_canvas.set_selection_rect(new_rect)
        else:
            # Couldn't re-find it — safer to clear than leave a stale box.
            self._clear_annot_selection()

    def _on_delete_selected_annot(self) -> None:
        if (
            self._selected_annot_xref is None
            or self._selected_annot_page is None
        ):
            return
        doc = self._viewer._doc  # noqa: SLF001
        if doc is None:
            return
        xref = self._selected_annot_xref
        page = self._selected_annot_page
        self._clear_annot_selection()
        self._push_undo(
            "Delete annotation",
            lambda: anno.delete_annotation(doc, page, xref),
        )

    def _refresh_after_annotation(self) -> None:
        """After any document mutation, re-render the viewer and refresh
        thumbnails / title / action states / bookmarks panel."""
        doc = self._viewer._doc  # noqa: SLF001
        if doc is not None:
            self._thumb_panel.set_document(doc)
        self._viewer.reload_current()
        if doc is not None:
            self._thumb_panel.select_page(self._viewer.current_page)
        self._refresh_bookmarks_panel()
        self._refresh_title()
        self._update_action_states()

    @property
    def _undo_stack(self) -> QUndoStack | None:
        """The currently-active QUndoStack (per-PDF). ``None`` when no
        PDF is open."""
        return self._undo_group.activeStack()

    def _push_undo(self, label: str, apply_fn) -> None:
        """Wrap a mutating operation as an undo-able snapshot command."""
        doc = self._viewer._doc  # noqa: SLF001
        stack = self._undo_stack
        if doc is None or stack is None:
            return
        cmd = SnapshotCommand(label, doc, apply_fn, self._refresh_after_annotation)
        stack.push(cmd)

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
        tool = ToolMode(tool_value)
        if tool == ToolMode.HIGHLIGHT:
            apply_fn = lambda: anno.add_highlight(
                doc, page_idx, word_rects,
                color=prefs_mod.parse_color(self._prefs.color_highlight),
            )
            label = "Highlight text"
        elif tool == ToolMode.UNDERLINE:
            apply_fn = lambda: anno.add_underline(
                doc, page_idx, word_rects,
                color=prefs_mod.parse_color(self._prefs.color_underline),
            )
            label = "Underline text"
        elif tool == ToolMode.STRIKEOUT:
            apply_fn = lambda: anno.add_strikeout(
                doc, page_idx, word_rects,
                color=prefs_mod.parse_color(self._prefs.color_strikeout),
            )
            label = "Strikeout text"
        else:
            return
        self._push_undo(label, apply_fn)

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
        page_idx = self._viewer.current_page
        self._push_undo(
            "Add sticky note",
            lambda: anno.add_sticky_note(doc, page_idx, pdf_point, text),
        )

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
        page_idx = self._viewer.current_page
        self._push_undo(
            "Pen stroke",
            lambda: anno.add_ink(
                doc, page_idx, [stroke],
                color=prefs_mod.parse_color(self._prefs.color_pen),
            ),
        )

    def _on_rect_drag_finished(
        self, tool_value: int, pdf_rect: tuple[float, float, float, float]
    ) -> None:
        doc = self._viewer._doc  # noqa: SLF001
        if doc is None:
            return
        page_idx = self._viewer.current_page
        tool = ToolMode(tool_value)
        if tool == ToolMode.RECT:
            self._push_undo(
                "Add rectangle",
                lambda: anno.add_rect(
                    doc, page_idx, pdf_rect,
                    color=prefs_mod.parse_color(self._prefs.color_rect),
                ),
            )
        elif tool == ToolMode.ELLIPSE:
            self._push_undo(
                "Add ellipse",
                lambda: anno.add_ellipse(
                    doc, page_idx, pdf_rect,
                    color=prefs_mod.parse_color(self._prefs.color_ellipse),
                ),
            )
        elif tool == ToolMode.TEXTBOX:
            text, ok = QInputDialog.getMultiLineText(
                self, "Text Box", "Text:", ""
            )
            if not ok or not text.strip():
                return
            self._push_undo(
                "Add text box",
                lambda: anno.add_text_box(
                    doc, page_idx, pdf_rect, text,
                    color=prefs_mod.parse_color(self._prefs.color_textbox),
                ),
            )

    def _on_arrow_drag_finished(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
    ) -> None:
        doc = self._viewer._doc  # noqa: SLF001
        if doc is None:
            return
        page_idx = self._viewer.current_page
        self._push_undo(
            "Add arrow",
            lambda: anno.add_arrow(
                doc, page_idx, start, end,
                color=prefs_mod.parse_color(self._prefs.color_arrow),
            ),
        )

    # =============================================================== Phase 5 export
    def _on_export_docx(self) -> None:
        doc = self._viewer._doc  # noqa: SLF001
        if doc is None:
            return
        if doc.is_modified:
            save_first = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved edits. Save the PDF first so they appear "
                "in the DOCX export?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.No
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save,
            )
            if save_first == QMessageBox.StandardButton.Cancel:
                return
            if save_first == QMessageBox.StandardButton.Save:
                self._on_save()
                if doc.is_modified:
                    return  # save failed
        dlg = ExportOptionsDialog("Export as DOCX", self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        opts = dlg.options()
        default_out = str(doc.path.with_name(f"{doc.path.stem}.docx"))
        out_str, _ = QFileDialog.getSaveFileName(
            self, "Save DOCX", default_out, "Word files (*.docx)"
        )
        if not out_str:
            return
        try:
            pdf_to_docx(doc.path, out_str)
        except Exception as exc:
            QMessageBox.critical(self, "DOCX Export Failed", str(exc))
            return
        msg = "Exported to DOCX."
        if not opts.include_annotations:
            msg += " (Annotations excluded via pdf2docx — rasterized only.)"
        self.statusBar().showMessage(msg, 5000)

    def _on_export_hwp(self) -> None:
        doc = self._viewer._doc  # noqa: SLF001
        if doc is None:
            return
        if not hwp_conversion_available():
            QMessageBox.information(
                self,
                "HWP Export Unavailable",
                "HWP export needs LibreOffice plus the h2orestart extension "
                "(which is not bundled by default). Install both and retry.",
            )
            return
        if doc.is_modified:
            self._on_save()
            if doc.is_modified:
                return
        default_out = str(doc.path.with_name(f"{doc.path.stem}.hwp"))
        out_str, _ = QFileDialog.getSaveFileName(
            self, "Save HWP", default_out, "HWP files (*.hwp)"
        )
        if not out_str:
            return
        try:
            pdf_to_hwp(doc.path, out_str)
        except Exception as exc:
            QMessageBox.critical(self, "HWP Export Failed", str(exc))
            return
        self.statusBar().showMessage("Exported to HWP.", 5000)

    # =============================================================== Phase 5 tabs
    def _focus_existing_tab(
        self, inner: QTabWidget, target: Path
    ) -> bool:
        """If *target* is already open in *inner*, switch focus to it
        and return True; otherwise return False."""
        try:
            target_resolved = target.resolve()
        except OSError:
            target_resolved = target
        for i in range(inner.count()):
            editor = inner.widget(i)
            cur = getattr(editor, "file_path", lambda: None)()
            if cur is None:
                continue
            try:
                cur_resolved = Path(cur).resolve()
            except OSError:
                cur_resolved = Path(cur)
            if cur_resolved == target_resolved:
                inner.setCurrentIndex(i)
                self._format_tabs.setCurrentWidget(inner)
                return True
        return False

    def _open_docx_tab(self, path_str: str) -> None:
        if self._focus_existing_tab(self._docx_file_tabs, Path(path_str)):
            return
        editor = DOCXEditor()
        editor.status_message.connect(
            lambda msg, ms: self.statusBar().showMessage(msg, ms)
        )
        try:
            editor.open_file(path_str)
        except Exception as exc:
            QMessageBox.critical(self, "Cannot Open DOCX", str(exc))
            editor.deleteLater()
            return
        self._ensure_format_tab(self._docx_file_tabs, "DOCX")
        idx = self._docx_file_tabs.addTab(editor, Path(path_str).name)
        self._docx_file_tabs.setCurrentIndex(idx)
        self._format_tabs.setCurrentWidget(self._docx_file_tabs)
        prefs_mod.push_recent_file(self._prefs, path_str)
        self._rebuild_recent_menu()
        self._maybe_prompt_lo_install()

    def _open_hwp_tab(self, path_str: str) -> None:
        if self._focus_existing_tab(self._hwp_file_tabs, Path(path_str)):
            return
        editor = HWPEditor()
        editor.status_message.connect(
            lambda msg, ms: self.statusBar().showMessage(msg, ms)
        )
        try:
            editor.open_file(path_str)
        except Exception as exc:
            QMessageBox.critical(self, "Cannot Open HWP", str(exc))
            editor.deleteLater()
            return
        self._ensure_format_tab(self._hwp_file_tabs, "HWP")
        idx = self._hwp_file_tabs.addTab(editor, Path(path_str).name)
        self._hwp_file_tabs.setCurrentIndex(idx)
        self._format_tabs.setCurrentWidget(self._hwp_file_tabs)
        prefs_mod.push_recent_file(self._prefs, path_str)
        self._rebuild_recent_menu()
        self._maybe_prompt_lo_install()

    # =================================================== LibreOffice prompt
    def _maybe_prompt_lo_install(self) -> None:
        """Offer to auto-install LibreOffice + h2orestart on the user's
        first DOCX/HWP open if it's missing. Idempotent — once the user
        has answered the prompt is suppressed forever (via prefs).
        """
        from opiter.core import lo_installer
        if self._prefs.lo_install_prompted:
            return
        if lo_installer.is_libreoffice_installed():
            return
        if lo_installer.detect_installer() is None:
            # No package manager we know how to drive — don't bother
            # the user with a prompt that has no clean answer.
            self._prefs.lo_install_prompted = True
            return

        size = lo_installer.estimated_libreoffice_size_mb()
        installer = lo_installer.installer_display_name(
            lo_installer.detect_installer()  # type: ignore[arg-type]
        )
        box = QMessageBox(self)
        box.setWindowTitle("Improve DOCX / HWP rendering?")
        box.setIcon(QMessageBox.Icon.Question)
        box.setText(
            "Opiter is currently showing this document in a simplified "
            "view (text + basic formatting).\n\n"
            "For pixel-perfect rendering of DOCX and HWP files — page "
            "layout, fonts, colors, embedded images, tables — install "
            f"LibreOffice (~{size} MB) via {installer}?\n\n"
            "The simplified view will keep working either way."
        )
        install_btn = box.addButton("Install LibreOffice", QMessageBox.ButtonRole.AcceptRole)
        skip_btn = box.addButton("Not now", QMessageBox.ButtonRole.RejectRole)
        never_btn = box.addButton("Don't ask again", QMessageBox.ButtonRole.DestructiveRole)
        box.setDefaultButton(install_btn)
        box.exec()
        clicked = box.clickedButton()

        if clicked is install_btn:
            self._prefs.lo_install_prompted = True
            self._launch_lo_install_dialog()
        elif clicked is never_btn:
            self._prefs.lo_install_prompted = True
        # "Not now" leaves the flag False so the prompt returns next session.

    def _launch_lo_install_dialog(self) -> None:
        """Spawn the modal install dialog; on success, refresh any
        already-open DOCX / HWP tabs so they re-render with LibreOffice."""
        from opiter.ui.lo_install_dialog import LibreOfficeInstallDialog
        dlg = LibreOfficeInstallDialog(self)
        dlg.finished_ok.connect(self._on_lo_install_succeeded)
        dlg.start()
        dlg.exec()

    def _on_install_libreoffice_menu(self) -> None:
        """Help → Install LibreOffice. Always available so the user can
        retry after a previously dismissed / failed prompt without
        editing preferences by hand."""
        from opiter.core import lo_installer
        if lo_installer.is_libreoffice_installed():
            QMessageBox.information(
                self, "LibreOffice already installed",
                "LibreOffice is already detected on this system. Open a "
                "DOCX or HWP file to use the high-fidelity renderer.\n\n"
                "If documents still look simple, the H2Orestart extension "
                "may be missing — re-run this from a clean install.",
            )
            return
        if lo_installer.detect_installer() is None:
            QMessageBox.warning(
                self, "No package manager detected",
                "No supported package manager was found on this system.\n\n"
                "Install LibreOffice manually from "
                "https://www.libreoffice.org/download/ and restart Opiter.",
            )
            return
        # Force show the dialog regardless of the lo_install_prompted flag.
        self._launch_lo_install_dialog()

    def _on_lo_install_succeeded(self) -> None:
        """Re-open every open DOCX / HWP file via the new LibreOffice
        path so the user sees the upgraded rendering immediately."""
        for inner in (self._docx_file_tabs, self._hwp_file_tabs):
            for i in range(inner.count()):
                w = inner.widget(i)
                p = getattr(w, "file_path", lambda: None)()
                if p is None:
                    continue
                try:
                    w.open_file(p)
                except Exception as exc:
                    self.statusBar().showMessage(
                        f"Could not refresh {p.name}: {exc}", 6000
                    )
        self.statusBar().showMessage(
            "LibreOffice installed — DOCX / HWP files now use the "
            "high-fidelity renderer.",
            6000,
        )

    def _ensure_format_tab(self, inner: QTabWidget, label: str) -> None:
        """Add *inner* as a format tab on the outer bar if absent."""
        if self._format_tabs.indexOf(inner) == -1:
            self._format_tabs.addTab(inner, label)

    def _on_pdf_inner_tab_changed(self, idx: int) -> None:
        """Mount the PDF chrome into the newly active inner tab,
        saving state out of the previously active one first."""
        new_holder = (
            self._pdf_file_tabs.widget(idx)
            if idx != -1 else None
        )
        if not isinstance(new_holder, _PDFTabHolder):
            new_holder = None

        # Save state of the previously active holder.
        if self._active_pdf_holder is not None:
            self._save_active_pdf_state()
            # Detach chrome from old holder so it can move.
            old_layout = self._active_pdf_holder.layout()
            if old_layout is not None:
                old_layout.removeWidget(self._pdf_splitter)
            self._pdf_splitter.setParent(self)
            self._pdf_splitter.hide()

        self._active_pdf_holder = new_holder

        if new_holder is None:
            # No PDF — reset viewer/panels but DON'T close any doc; the
            # holder that owned it already closed it on tab close.
            self._viewer.detach_document()
            self._thumb_panel.clear()
            self._thumb_panel._current_doc = None  # noqa: SLF001
            self._reset_search_state()
            self._clear_annot_selection()
            self._refresh_bookmarks_panel()
            self._refresh_title()
            self._update_action_states()
            return

        # Mount chrome into the new holder.
        new_holder.layout().addWidget(self._pdf_splitter)
        self._pdf_splitter.show()
        self._undo_group.setActiveStack(new_holder.undo_stack)
        self._load_pdf_state(new_holder)

    def _save_active_pdf_state(self) -> None:
        """Capture viewer / search / selection state into the active holder."""
        h = self._active_pdf_holder
        if h is None:
            return
        h.current_page = self._viewer.current_page
        h.zoom = self._viewer.zoom
        h.scroll_x = self._viewer.horizontalScrollBar().value()
        h.scroll_y = self._viewer.verticalScrollBar().value()
        h.search_query = self._search_bar.query()
        h.search_results = list(self._search_results)
        h.search_current = self._search_current
        h.selected_annot_xref = self._selected_annot_xref
        h.selected_annot_page = self._selected_annot_page

    def _load_pdf_state(self, h: "_PDFTabHolder") -> None:
        """Restore *h*'s saved state into the shared chrome."""
        # Document → viewer + thumbnails. Use swap_document so we don't
        # close the previously-active holder's doc — it's still owned by
        # whatever tab we just left.
        self._viewer.swap_document(h.doc)
        self._thumb_panel.set_document(h.doc)
        self._viewer.goto_page(h.current_page)
        self._viewer.set_zoom(h.zoom)
        self._viewer.horizontalScrollBar().setValue(h.scroll_x)
        self._viewer.verticalScrollBar().setValue(h.scroll_y)
        self._thumb_panel.select_page(h.current_page)
        # Search — restore results but leave the bar hidden; user reopens
        # via Ctrl+F when needed.
        self._search_results = list(h.search_results)
        self._search_current = h.search_current
        # Selection
        self._selected_annot_xref = h.selected_annot_xref
        self._selected_annot_page = h.selected_annot_page
        # Bookmarks panel + title + actions
        self._refresh_bookmarks_panel()
        self._refresh_title()
        self._update_action_states()

    def _on_pdf_tab_close(self, index: int) -> None:
        """Close one PDF inner tab. Asks about unsaved changes, releases
        the document, removes the holder. If it was the last PDF, the
        PDF format tab is also removed."""
        holder = self._pdf_file_tabs.widget(index)
        if not isinstance(holder, _PDFTabHolder):
            return
        if holder.doc.is_modified:
            ret = QMessageBox.question(
                self,
                "Unsaved Changes",
                f"{holder.doc.path.name} has unsaved changes. Save before closing?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
            )
            if ret == QMessageBox.StandardButton.Cancel:
                return
            if ret == QMessageBox.StandardButton.Save:
                # Save in place via the document's path.
                try:
                    holder.doc.save_as(holder.doc.path)
                except Exception as exc:
                    QMessageBox.critical(
                        self, "Save Failed", str(exc)
                    )
                    return

        is_active = holder is self._active_pdf_holder
        if is_active:
            # Detach chrome before removing the holder so it doesn't get
            # destroyed as the holder's child widget.
            old_layout = holder.layout()
            if old_layout is not None:
                old_layout.removeWidget(self._pdf_splitter)
            self._pdf_splitter.setParent(self)
            self._pdf_splitter.hide()
            self._active_pdf_holder = None

        self._undo_group.removeStack(holder.undo_stack)
        self._pdf_file_tabs.removeTab(index)
        try:
            holder.doc.close()
        except Exception:
            pass
        holder.deleteLater()

        if self._pdf_file_tabs.count() == 0:
            outer = self._format_tabs.indexOf(self._pdf_file_tabs)
            if outer != -1:
                self._format_tabs.removeTab(outer)
            # _on_pdf_inner_tab_changed will fire with idx=-1 and clean up.
        elif is_active:
            # Switch to the new current tab so chrome remounts.
            new_idx = self._pdf_file_tabs.currentIndex()
            self._on_pdf_inner_tab_changed(new_idx)

    def _on_docx_tab_close(self, index: int) -> None:
        self._close_inner_tab(self._docx_file_tabs, index)

    def _on_hwp_tab_close(self, index: int) -> None:
        self._close_inner_tab(self._hwp_file_tabs, index)

    def _on_format_tab_close(self, index: int) -> None:
        """Closing a format tab closes every file under it. Routes to the
        same per-file handlers so unsaved-PDF prompts and resource cleanup
        still run."""
        widget = self._format_tabs.widget(index)
        if widget is self._pdf_file_tabs:
            # Single PDF — same path as the inner × on the PDF.
            self._on_pdf_tab_close(0)
            return
        if widget is self._docx_file_tabs:
            inner = self._docx_file_tabs
        elif widget is self._hwp_file_tabs:
            inner = self._hwp_file_tabs
        else:
            return
        # _close_inner_tab removes the format tab itself once the inner
        # count hits 0, so we just keep popping index 0.
        while inner.count() > 0:
            self._close_inner_tab(inner, 0)

    def _close_inner_tab(self, inner: QTabWidget, index: int) -> None:
        widget = inner.widget(index)
        inner.removeTab(index)
        if widget is not None:
            close = getattr(widget, "close_document", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    pass
            widget.deleteLater()
        # Remove the format tab entirely when it has no files left.
        if inner.count() == 0:
            outer_idx = self._format_tabs.indexOf(inner)
            if outer_idx != -1:
                self._format_tabs.removeTab(outer_idx)

    def _on_format_changed(self, index: int) -> None:
        """Swap toolbars and PDF-only docks based on the active format tab.
        When no format tab exists (index == -1), hide everything and show
        the always-on welcome toolbar so the user can still open a file."""
        widget = self._format_tabs.widget(index) if index != -1 else None
        is_pdf = widget is self._pdf_file_tabs
        is_docx = widget is self._docx_file_tabs
        is_hwp = widget is self._hwp_file_tabs
        nothing_open = widget is None

        self._welcome_toolbar.setVisible(nothing_open)
        self._main_toolbar.setVisible(is_pdf)
        self._anno_toolbar.setVisible(is_pdf)
        self._docx_toolbar.setVisible(is_docx)
        self._hwp_toolbar.setVisible(is_hwp)
        # Thumbnail/bookmark panels live inside the PDF tab content now,
        # so their visibility is owned by the toggle actions, not the
        # format-tab change. Nothing to do here.

    # =============================================================== Phase 4
    def _on_export_images(self) -> None:
        doc = self._viewer._doc  # noqa: SLF001
        if doc is None:
            return
        spec, ok = QInputDialog.getText(
            self,
            "Export Pages as Images",
            f"Pages (1 – {doc.page_count}, e.g. 1-3,5):",
            text=f"1-{doc.page_count}",
        )
        if not ok or not spec.strip():
            return
        try:
            indices = parse_page_range_spec(spec, doc.page_count)
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid Page Range", str(exc))
            return
        # Use a QMessageBox with explicit buttons — the QInputDialog.getItem
        # combobox popup sometimes stays open after selection under WSLg.
        fmt_box = QMessageBox(self)
        fmt_box.setWindowTitle("Image Format")
        fmt_box.setText("Choose an output format:")
        btn_png = fmt_box.addButton("PNG", QMessageBox.ButtonRole.AcceptRole)
        btn_jpg = fmt_box.addButton("JPG", QMessageBox.ButtonRole.AcceptRole)
        btn_cancel = fmt_box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        fmt_box.setDefaultButton(btn_png)
        fmt_box.exec()
        clicked = fmt_box.clickedButton()
        if clicked is btn_cancel or clicked is None:
            return
        fmt = "jpg" if clicked is btn_jpg else "png"
        out_dir = self._prompt_output_directory(
            f"{doc.path.stem}_images", "Image Export Directory"
        )
        if out_dir is None:
            return
        try:
            paths = export_pages_as_images(
                doc, indices, out_dir, doc.path.stem, fmt=fmt
            )
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", str(exc))
            return
        QMessageBox.information(
            self, "Export Complete",
            f"Wrote {len(paths)} image(s) to:\n{out_dir}",
        )

    def _on_images_to_pdf(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Images (order preserved)",
            str(Path.home()),
            "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff);;All files (*)",
        )
        if not paths:
            return
        default_out = str(Path(paths[0]).parent / "images.pdf")
        out_str, _ = QFileDialog.getSaveFileName(
            self, "Save New PDF", default_out, "PDF files (*.pdf)"
        )
        if not out_str:
            return
        try:
            out = images_to_pdf(paths, out_str)
        except Exception as exc:
            QMessageBox.critical(self, "Conversion Failed", str(exc))
            return
        self.statusBar().showMessage(
            f"Combined {len(paths)} image(s) into {out}", 5000
        )
        # Open the freshly-created PDF so the user can verify the result.
        self._open_path(str(out), confirm_discard=False)

    def _on_compress(self) -> None:
        doc = self._viewer._doc  # noqa: SLF001
        if doc is None:
            return
        # 3 explicit buttons instead of a combobox popup — cleaner UX and
        # sidesteps a Qt/WSLg quirk where the dropdown stayed open after
        # picking an item.
        box = QMessageBox(self)
        box.setWindowTitle("Compression Quality")
        box.setText("Pick a compression preset:")
        box.setInformativeText(
            "Low = smallest file / most loss\n"
            "Medium = balanced (default)\n"
            "High = largest file / least loss"
        )
        btn_low = box.addButton("Low", QMessageBox.ButtonRole.AcceptRole)
        btn_med = box.addButton("Medium", QMessageBox.ButtonRole.AcceptRole)
        btn_high = box.addButton("High", QMessageBox.ButtonRole.AcceptRole)
        btn_cancel = box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(btn_med)
        box.exec()
        clicked = box.clickedButton()
        if clicked is btn_cancel or clicked is None:
            return
        if clicked is btn_low:
            quality = "low"
        elif clicked is btn_high:
            quality = "high"
        else:
            quality = "medium"
        default_out = str(doc.path.with_name(f"{doc.path.stem}_compressed.pdf"))
        out_str, _ = QFileDialog.getSaveFileName(
            self, "Save Compressed Copy", default_out, "PDF files (*.pdf)"
        )
        if not out_str:
            return
        try:
            compress_pdf(doc, out_str, quality=quality)
        except Exception as exc:
            QMessageBox.critical(self, "Compression Failed", str(exc))
            return
        original = doc.path.stat().st_size if doc.path.exists() else 0
        compressed = Path(out_str).stat().st_size
        pct = (1 - compressed / original) * 100 if original else 0
        self.statusBar().showMessage(
            f"Compressed: {original/1024:.0f} KB → {compressed/1024:.0f} KB "
            f"({pct:.1f}% reduction)",
            6000,
        )

    def _on_watermark(self) -> None:
        doc = self._viewer._doc  # noqa: SLF001
        if doc is None:
            return
        dlg = WatermarkDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        s = dlg.settings()
        if not s.text:
            return
        self._push_undo(
            "Add watermark",
            lambda: add_text_watermark(
                doc, s.text,
                fontsize=s.fontsize,
                opacity=s.opacity,
                rotate=s.rotate,
            ),
        )

    def _on_metadata(self) -> None:
        doc = self._viewer._doc  # noqa: SLF001
        if doc is None:
            return
        current = read_metadata(doc)
        dlg = MetadataDialog(current, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        new_md = dlg.get_metadata()
        self._push_undo(
            "Edit document properties",
            lambda: write_metadata(doc, new_md),
        )

    def _on_toc_changed(self, entries: list) -> None:
        """BookmarksPanel → apply new TOC to the document."""
        doc = self._viewer._doc  # noqa: SLF001
        if doc is None:
            return
        self._push_undo(
            "Edit bookmarks",
            lambda: write_toc(doc, entries),
        )

    def _refresh_bookmarks_panel(self) -> None:
        doc = self._viewer._doc  # noqa: SLF001
        if doc is None:
            self._bookmarks_panel.clear()
            return
        self._bookmarks_panel.set_page_context(
            self._viewer.current_page, doc.page_count
        )
        self._bookmarks_panel.set_toc(read_toc(doc))

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
            self._action_export_images,
            self._action_compress,
            self._action_watermark,
            self._action_metadata,
            self._action_export_docx,
        ):
            act.setEnabled(has_doc)
        self._action_export_hwp.setEnabled(has_doc and hwp_conversion_available())
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
            self._update_action_states()
            return
        marker = " *" if doc.is_modified else ""
        self.setWindowTitle(f"Opiter — {doc.path.name}{marker}")
        # Update the inner tab label for the active holder.
        h = self._active_pdf_holder
        if h is not None:
            idx = self._pdf_file_tabs.indexOf(h)
            if idx != -1:
                self._pdf_file_tabs.setTabText(
                    idx, f"{doc.path.name}{marker}"
                )
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

    _COLOR_ENTRIES = (
        ColorEntry("color_highlight", "Highlight"),
        ColorEntry("color_underline", "Underline"),
        ColorEntry("color_strikeout", "Strikeout"),
        ColorEntry("color_pen", "Pen"),
        ColorEntry("color_rect", "Rectangle"),
        ColorEntry("color_ellipse", "Ellipse"),
        ColorEntry("color_arrow", "Arrow"),
        ColorEntry("color_textbox", "Text Box"),
    )

    def _on_preferences(self) -> None:
        entries = [e for e, _ in self._action_registry]
        current_colors = {
            e.pref_field: prefs_mod.parse_color(getattr(self._prefs, e.pref_field))
            for e in self._COLOR_ENTRIES
        }
        dlg = PreferencesDialog(
            entries,
            dict(self._prefs.keymap),
            list(self._COLOR_ENTRIES),
            current_colors,
            self,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        # Apply keymap overrides
        new_overrides = dlg.get_overrides()
        self._prefs.keymap = new_overrides
        for entry, action in self._action_registry:
            action.setShortcut(QKeySequence(entry.default_shortcut))
        self._apply_keymap_overrides()
        # Apply color choices
        for field, rgb in dlg.get_colors().items():
            setattr(self._prefs, field, prefs_mod.format_color(rgb))
        try:
            prefs_mod.save(self._prefs)
        except Exception:
            pass
        self.statusBar().showMessage("Preferences updated.", 4000)

    # -------------------------------------------------------- preferences
    def _apply_loaded_preferences(self) -> None:
        """Apply ``self._prefs`` to UI state after all widgets are built."""
        # Dark mode
        if self._prefs.dark_mode:
            # Triggers _on_toggle_dark_mode → apply_dark.
            self._action_dark_mode.setChecked(True)
        else:
            # Default light theme — call explicitly so our Fusion-based
            # palette + QSS gets installed instead of the platform's
            # native style (which on Windows ignores our palette).
            from PySide6.QtWidgets import QApplication
            apply_light(QApplication.instance())
        # Thumbnail panel visibility persists across sessions.
        if not self._prefs.dock_visible:
            self._action_toggle_thumbs.setChecked(False)
        # Maximized state takes precedence over size/pos if set
        if self._prefs.window_maximized:
            self.showMaximized()

    def _on_thumb_size_changed(self, value: int) -> None:
        self._thumb_panel.set_thumbnail_width(value)
        self._prefs.thumbnail_width_px = self._thumb_panel.thumbnail_width()
        self._thumb_panel.select_page(self._viewer.current_page)

    def _capture_preferences(self) -> None:
        """Copy current UI state into ``self._prefs`` (pre-save)."""
        self._prefs.window_maximized = self.isMaximized()
        self._prefs.thumbnail_width_px = self._thumb_panel.thumbnail_width()
        if not self.isMaximized():
            self._prefs.window_width = self.width()
            self._prefs.window_height = self.height()
            self._prefs.window_x = self.x()
            self._prefs.window_y = self.y()
        self._prefs.dock_visible = self._action_toggle_thumbs.isChecked()
        # dock_area legacy field — left as-is; not used now that the panel
        # lives inside the PDF tab content.
        self._prefs.dark_mode = self._action_dark_mode.isChecked()
