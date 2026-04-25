# Opiter — Architecture

> **Status**: Reflects v0.1 codebase. Updated alongside major refactors.

---

## Principles

1. **Separation of concerns**: The UI layer never directly touches PDF/DOCX/HWP byte-level state. All file operations go through `core/` abstractions.
2. **Format-agnostic editor interface**: PDF, DOCX, and HWP each implement [`AbstractEditor`](src/opiter/ui/editors/abstract_editor.py) so the tab system treats them uniformly (open / save / modified / display name / close).
3. **Lazy / cached rendering**: Page pixmaps render on demand. Thumbnails are persisted under XDG cache, keyed by `(path, mtime, page_index, width)`, and bypass the cache when a document is in an unsaved-modified state so reorder/rotate updates show immediately.
4. **Graceful failure**: Corrupted or encrypted files surface user-friendly dialogs (password retry for AES) — never crash.
5. **Standard PDF annotations**: Highlights / underlines / strikeouts / sticky notes / shapes are written as native `/Annot` objects so they round-trip through Adobe / Foxit / browser PDF viewers.

---

## Module Map

```
src/opiter/
├── __init__.py            # version + main()
├── __main__.py            # `python -m opiter`
├── main.py                # bootstraps QApplication, MainWindow, dark/light theme
│
├── ui/                    # GUI layer (PySide6)
│   ├── main_window.py       # QMainWindow + menus / toolbars / two-level tabs
│   ├── viewer_widget.py     # PDF page rendering, scroll, zoom
│   ├── page_canvas.py       # QLabel-derived canvas with annotation draw + hit testing
│   ├── thumbnail_panel.py   # Drag-reorderable thumbnail list with delegate
│   ├── bookmarks_panel.py   # TOC tree edit
│   ├── search_bar.py        # Find: prev / next / count
│   ├── smooth_tab_bar.py    # QTabBar subclass: clamped drag, no-anim reorder
│   ├── cjk_font.py          # Auto-load Korean/CJK font fallback
│   ├── theme.py             # Dark/light Qt palettes
│   ├── preferences_dialog.py
│   ├── metadata_dialog.py
│   ├── watermark_dialog.py
│   ├── export_dialog.py     # PDF → DOCX/HWP options
│   └── editors/
│       ├── abstract_editor.py
│       ├── docx_editor.py     # python-docx → minimal HTML → QTextEdit
│       └── hwp_editor.py      # pyhwp text extraction → QTextEdit
│
├── core/                  # File domain (no Qt imports)
│   ├── document.py          # Document wrapper around fitz.Document with snapshot/restore
│   ├── renderer.py          # render_page(doc, idx, zoom, rotation)
│   ├── page_ops.py          # rotate / delete / insert / merge / split / extract
│   ├── annotations.py       # CRUD; rotation-aware coords; highlight overlap merge
│   ├── search.py            # PyMuPDF text search across pages
│   ├── compression.py       # 3 quality presets via fitz.save options
│   ├── watermark.py         # text watermark, multi-rotation, page-rotation aware
│   ├── metadata.py          # title/author/subject/keywords get/set
│   ├── toc.py               # bookmark / outline read/write
│   ├── image_export.py      # page → PNG/JPG
│   ├── image_to_pdf.py      # images → PDF
│   ├── pdf_to_docx.py       # pdf2docx wrapper
│   ├── pdf_to_hwp.py        # PDF → DOCX → HWP via soffice + h2orestart
│   ├── thumbnail_cache.py   # XDG-cached PNGs
│   ├── preferences.py       # JSON prefs in XDG config
│   └── undo.py              # QUndoCommand subclass: snapshot bytes before/after
│
└── utils/
    ├── paths.py             # XDG config/cache resolution
    └── errors.py            # CorruptedPDFError / EncryptedPDFError
```

---

## Two-Level Tab Model

```
QMainWindow
├── menubar
├── toolbars (Welcome | Main+Annotate | DOCX | HWP) — only one set visible at a time
└── centralWidget = format_tabs (outer QTabWidget)
    ├── PDF
    │   └── pdf_file_tabs (inner QTabWidget) ─ N PDFTabHolder placeholders
    │       The PDF chrome (QSplitter [thumbnails | viewer+searchbar | bookmarks])
    │       gets reparented into whichever holder is currently active.
    ├── DOCX
    │   └── docx_file_tabs ─ N DOCXEditor instances
    └── HWP
        └── hwp_file_tabs ─ N HWPEditor instances
```

Format tabs (PDF / DOCX / HWP) appear dynamically when the first file of that type is opened and disappear when the last one closes. Each format has its own toolbar swapped in/out on `_format_tabs.currentChanged`.

---

## Multi-PDF State

Each open PDF is owned by a `_PDFTabHolder` (in `main_window.py`) holding:

- `Document` instance + its file path
- `QUndoStack` registered into the window's `QUndoGroup`
- Viewer state: current page, zoom, scroll offsets
- Search state: query, results, current index
- POINTER selection state: annot xref, page index

On tab activation, `_save_active_pdf_state` captures viewer state into the outgoing holder, the chrome splitter is reparented into the new holder, and `_load_pdf_state` restores the new holder's state. The `QUndoGroup.setActiveStack` call routes the menu's Undo/Redo to whichever document is in front.

---

## Data Flow: Open a PDF

```
File → Open (QFileDialog)
   │  uses ext-based routing in _open_path
   ▼
[ext = .pdf] dedup scan: any holder with same path? → focus existing tab
   │
   ▼
core/document.py: Document.open(path)        ← may raise EncryptedPDFError / CorruptedPDFError
   │
   ▼
new _PDFTabHolder(doc) added to QUndoGroup; addTab into _pdf_file_tabs
   │
   ▼
_on_pdf_inner_tab_changed fires → mounts splitter into the holder, swap_document into viewer
```

DOCX / HWP take the parallel `_open_docx_tab` / `_open_hwp_tab` path — same dedup, no Document model needed (read-only).

---

## Annotation Pipeline (highlight as example)

```
PageCanvas (text drag)
   │ emits text_drag_finished(rect_in_rotated_pdf_coords)
   ▼
MainWindow._on_text_drag_finished
   │ core.annotations.find_words_in_rect → merged-line word rects
   │ packs into a SnapshotCommand
   ▼
SnapshotCommand.redo()
   │ snapshot doc bytes (BEFORE)
   │ run apply_fn = lambda: anno.add_highlight(doc, page_idx, word_rects)
   │ snapshot doc bytes (AFTER)
   ▼
core.annotations.add_highlight
   │ derotate each rect (page.derotation_matrix)
   │ scan existing /Annot Highlight; merge overlapping or same-line-adjacent quads
   │ delete merged-into annotations; create one fresh annot covering union
   ▼
_refresh_after_annotation: viewer reload, thumbnails refresh, title update
```

---

## Threading Model

Currently single-threaded. Qt event loop drives everything; PyMuPDF rendering happens synchronously on the main thread because typical pages render in a few ms. Async / threaded rendering is a candidate for a future polish pass if very large PDFs cause perceptible UI lag.

---

## Persistence / State

- **Recent files + preferences**: `~/.config/opiter/preferences.json` (XDG config)
- **Thumbnail cache**: `~/.cache/opiter/thumbnails/` (XDG cache); cache bypassed while documents are in an unsaved-modified state
- **CJK fonts**: discovered at runtime via `cjk_font.py`, registered into the application font database

---

## Error Handling

| Error | Behavior |
|---|---|
| `FileNotFoundError` (recent file gone) | Recent menu auto-prunes |
| `CorruptedPDFError` | Modal: "file may be damaged" |
| `EncryptedPDFError` | Password prompt with up to 3 retries |
| `PermissionError` (save) | Modal with the OSError message |
| Unexpected exceptions in handlers | Caught at the slot boundary; surfaced as a critical dialog |

---

## Test Strategy

`pytest` + `pytest-qt`. 186 tests total covering:

- Pure-core (document, page_ops, annotations, search, compression, image export, pdf2docx)
- Qt widgets in offscreen mode (viewer, thumbnail panel, search bar, main window)
- Phase 4 advanced PDF features
- Phase 5 cross-format export (3 tests including a real pdf2docx run on a synthetic PDF)

CI is not yet wired (post v0.1).
