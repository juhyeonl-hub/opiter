# Opiter

> Free and open-source PDF editor — view, manipulate, and annotate PDFs locally with no ads, subscriptions, or cloud uploads.

**Status**: 🚧 Pre-alpha prototype. Phase 1~3 in active development. Not yet usable for end users.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Built with PySide6](https://img.shields.io/badge/GUI-PySide6-41cd52.svg)](https://doc.qt.io/qtforpython-6/)

---

## Why Opiter?

Commercial PDF editors are expensive and proprietary. Free web-based alternatives often upload your files to remote servers. Opiter is built on a different premise:

- **100% free** — no ads, no subscriptions, no premium tiers
- **Open source** — MIT-licensed, auditable by anyone
- **Privacy-first** — all processing happens locally; files never leave your machine
- **Cross-platform** (planned) — Windows, macOS, Linux from a single codebase

The long-term vision is a unified editor for multiple document formats (PDF, DOCX, HWP). The current MVP focuses on a polished PDF experience first.

## Features (MVP — Phase 1~3)

### Phase 1: Viewer 🚧
- Open PDF files with multi-page rendering
- Page navigation, zoom (fit-to-width, custom levels)
- Thumbnail sidebar
- Text search
- Dark mode / light mode

### Phase 2: Page Operations 🚧
- Add / delete / reorder pages
- Rotate pages (90° increments)
- Merge multiple PDFs
- Split PDFs (by range or per-page)
- Extract specific pages

### Phase 3: Annotations 🚧
- Highlight, underline, strikethrough
- Sticky notes (comments)
- Freehand drawing (pen)
- Shapes (rectangle, ellipse, arrow)
- Text boxes

See [FEATURES.md](./FEATURES.md) for the full roadmap including post-MVP plans (image conversion, compression, DOCX/HWP support).

## Installation

### Prerequisites
- **Python 3.11** or later (managed automatically by uv)
- [**uv**](https://github.com/astral-sh/uv) package manager
- A working Qt6 display environment:
  - **Linux**: a desktop session (X11 or Wayland)
  - **WSL2**: WSLg (Windows 11) or X server forwarding
  - **macOS / Windows**: not yet tested in this prototype

### Install uv (if needed)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Clone and run
```bash
git clone <repository-url>
cd opiter
uv sync
uv run opiter
```

## Development

```bash
# Install runtime + dev dependencies
uv sync --all-groups

# Run from source
uv run python -m opiter

# Run tests
uv run pytest
```

See [CONTRIBUTING.md](./CONTRIBUTING.md) for contribution guidelines and [ARCHITECTURE.md](./ARCHITECTURE.md) for the codebase structure.

## Documentation

| File | Purpose |
|------|---------|
| [PROJECT.md](./PROJECT.md) | Vision, philosophy, scope (what Opiter is and isn't) |
| [FEATURES.md](./FEATURES.md) | Full feature roadmap (Phase 1~5+) |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Module layout, data flow, design decisions |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | How to contribute |
| [PROJECT_BRIEF.md](./PROJECT_BRIEF.md) | Current iteration's working brief (Phase 1~3 prototype) |

## License

[MIT License](./LICENSE) © 2026 juhyeonl

## Acknowledgments

Opiter stands on the shoulders of excellent open-source projects:

- [PyMuPDF](https://github.com/pymupdf/PyMuPDF) (fitz) — PDF rendering and editing core
- [pypdf](https://github.com/py-pdf/pypdf) — page-level operations
- [pdfplumber](https://github.com/jsvine/pdfplumber) — text and table extraction
- [PySide6](https://doc.qt.io/qtforpython-6/) — cross-platform GUI toolkit (Qt for Python)
- [uv](https://github.com/astral-sh/uv) — Python packaging
