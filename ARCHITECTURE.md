# Opiter — Architecture

> **Status**: Initial draft (Step 2). Will evolve as Phase 1~3 implementation progresses.
> Concrete module files listed below are *targets* for implementation, not all yet present.

---

## Principles

1. **Separation of concerns**: The UI layer must never directly touch PDF bytes. All PDF operations go through `core/` abstractions.
2. **Format-agnostic core interface**: Phase 1~3 targets PDF only, but `core/` abstractions should not assume PDF-only types in their public API (prepare for DOCX/HWP in Phase 5+).
3. **Lazy loading**: Large PDFs (hundreds of MB, thousands of pages) must not block the UI thread. Pages render on demand; thumbnails generate asynchronously and cache.
4. **Graceful failure**: Corrupted, encrypted, or otherwise unopenable PDFs must surface user-friendly errors via dialogs — never crash the app.
5. **No global state**: Document and view state belong to instances, not module-level singletons (except resource caches).

---

## Module Map (Target)

```
src/opiter/
├── __init__.py            # package marker, re-exports main()
├── __main__.py            # `python -m opiter` entry point
├── main.py                # bootstraps QApplication, creates MainWindow
│
├── ui/                    # GUI layer (PySide6-dependent)
│   ├── main_window.py       # QMainWindow + menu/toolbar orchestration
│   ├── viewer_widget.py     # Page rendering canvas (scrollable)
│   ├── thumbnail_panel.py   # Sidebar thumbnails
│   ├── search_bar.py        # Text search UI + result navigation
│   ├── dialogs/             # Open/save/preferences/about dialogs
│   └── theme.py             # Dark/light mode stylesheet management
│
├── core/                  # PDF domain (PyMuPDF/pypdf/pdfplumber-dependent, no Qt imports)
│   ├── document.py          # Document model wrapping fitz.Document
│   ├── renderer.py          # render_page(doc, idx, zoom, rotation) → image bytes
│   ├── page_ops.py          # Phase 2: add/delete/reorder/rotate/merge/split/extract
│   ├── annotations.py       # Phase 3: annotation CRUD
│   └── search.py            # Full-text search across pages
│
├── utils/                 # Cross-cutting helpers (no Qt, no PDF libs)
│   ├── paths.py             # XDG-compliant config/cache paths
│   ├── i18n.py              # Translation loader (Qt Linguist-based)
│   ├── logging.py           # Structured logging
│   └── errors.py            # Custom exception types
│
└── resources/             # Static assets (icons, .qss stylesheets, .qm translations)
```

The strict `ui/` ↔ `core/` boundary is enforced by convention: `core/` modules must not `import PySide6`. This keeps the core unit-testable headlessly and prepares for non-Qt frontends later if needed.

---

## Data Flow: "Open and Render a Page"

```
User: File → Open
   │
   ▼
ui/main_window.py
   │  → QFileDialog
   │  → receives file path
   ▼
core/document.py: Document.open(path)
   │  ↳ fitz.open() — may raise CorruptedPDFError / EncryptedPDFError
   │  ↳ returns Document wrapper
   ▼
ui/viewer_widget.py: set_document(doc)
   │  → triggers render of page 0
   ▼
core/renderer.py: render_page(doc, 0, zoom=1.0, rotation=0)
   │  → fitz.Page.get_pixmap() → bytes
   ▼
QImage.fromData(bytes) → QLabel.setPixmap()
   │
   ▼
ui/thumbnail_panel.py: kick off async thumbnail generation for pages 1..N
   (QThreadPool — UI stays responsive)
```

---

## Threading Model

- **Main thread**: Qt event loop, all UI updates, user input handling
- **Worker thread pool** (`QThreadPool`): page rendering, thumbnail generation, full-document search
- **Communication**: Qt signals/slots (thread-safe across thread boundaries)

Heavy operations (e.g., merging large PDFs) must run in workers and emit progress signals back to the UI.

---

## Error Handling

| Error Type | Behavior |
|------------|----------|
| `FileNotFoundError` | Modal error dialog; return to previous state |
| `CorruptedPDFError` | Modal error dialog: "file may be damaged" |
| `EncryptedPDFError` | Password prompt dialog; if cancelled → abort open |
| `PermissionError` | Modal error dialog: "check file permissions" |
| Unexpected exceptions | Logged + modal error with "report a bug" link |

All custom exceptions live in `utils/errors.py`.

---

## Persistence / State

- **Recent files**: XDG config (`~/.config/opiter/recent.json`)
- **Preferences**: XDG config (`~/.config/opiter/config.json`) — theme, default zoom, sidebar visibility
- **Thumbnail cache**: XDG cache (`~/.cache/opiter/thumbnails/`) — keyed by file content hash

XDG paths are resolved through `utils/paths.py` to keep platform differences contained.

---

## Internationalization

- Pipeline: Qt Linguist `.ts` source → `.qm` compiled translations
- Bundled languages: `en` (default), `ko`
- Runtime locale: `QLocale.system()` with English fallback
- All user-facing strings wrapped in `tr()` from the start (Phase 1+)

---

## Design Decisions Deferred

These will be settled as implementation reaches the relevant phase:

| Decision | Phase | Notes |
|----------|-------|-------|
| Annotation storage format | 3 | Standard PDF `/Annot` (interoperable) vs. external sidecar JSON. **Tentative**: standard `/Annot` for portability |
| Thumbnail cache invalidation | 1 | mtime-based vs. content-hash. **Tentative**: content-hash (more robust) |
| Undo/redo scope and depth | 2 | Per-document `QUndoStack`, default 100 steps |
| Render backend choice | 1 | PyMuPDF only vs. fallback to pypdfium2. **Tentative**: PyMuPDF only for Phase 1; revisit if perf issues |
| Plugin/extension system | Post-MVP | Architecture impact small if deferred; defer |
