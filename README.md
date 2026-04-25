# Opiter

**English** | [한국어](./README.ko.md)

> Free, open-source desktop document workbench — edit PDFs, view DOCX and HWP, and convert between formats locally with no ads, subscriptions, or cloud uploads.

**Status**: v0.1 — first public release. PDF editing complete; DOCX and HWP supported as viewers. Built and tested on Linux (incl. WSL2).

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Built with PySide6](https://img.shields.io/badge/GUI-PySide6-41cd52.svg)](https://doc.qt.io/qtforpython-6/)

---

## Why Opiter?

Commercial PDF editors are expensive and proprietary. Free web-based alternatives often upload your files to remote servers. Korean office workers who receive HWP files have no good free, native viewer. Opiter is built on a different premise:

- **100% free** — no ads, no subscriptions, no premium tiers
- **Privacy-first** — all processing happens locally; files never leave your machine
- **One app, three formats** — PDF (full editing), DOCX (viewer), HWP (viewer)
- **Cross-format export** — convert PDF → DOCX in one click, optional PDF → HWP via LibreOffice + h2orestart

## Features

### PDF (full editor)
- Open, navigate, zoom, fit-to-width, dark mode
- Add / delete / reorder / rotate pages
- Merge multiple PDFs, split (by range or per-page), extract
- Annotations: highlight, underline, strikethrough, sticky notes, freehand pen, rect, ellipse, arrow, text box
- Watermarks (text, multiple rotations)
- Compression (3 quality presets)
- Document properties (title, author, keywords)
- Bookmarks / table of contents
- Image export (PNG/JPG per page) and image-to-PDF
- Full-text search with rotation-aware highlighting
- Multi-document tabs with independent undo stacks

### DOCX (viewer)
- Read-only rich-text rendering: headings, bold/italic/underline, tables, lists
- CJK font fallback for Korean text on systems without bundled CJK fonts

### HWP (viewer)
- Read-only text extraction via pyhwp
- Korean / hanja rendered correctly with Malgun / Noto CJK fallback

### Cross-format export
- **PDF → DOCX**: pdf2docx-based, preserves text, images, basic tables
- **PDF → HWP**: best-effort via LibreOffice + h2orestart extension (auto-detected)

See [FEATURES.md](./FEATURES.md) for the full feature inventory and post-v0.1 roadmap (DOCX editing, batch processing).

## Installation

### Quick install (download a release)

Pick the file that matches your OS from the [latest release](https://github.com/juhyeonl-hub/opiter/releases/latest):

#### Windows
File: `opiter-windows-x86_64.exe`. Double-click to run.

> **First-launch security warning.** Windows shows a blue "Windows protected your PC" dialog because the binary isn't yet code-signed. Click the small **"More info"** link, then **"Run anyway"** — the app will launch normally. (Code signing through the [SignPath Foundation](https://signpath.org/) is in progress; once approved, this warning will go away on its own.)
>
> **If nothing happens at all (no dialog, app silently fails):** your machine likely has Smart App Control turned on, which silently blocks unsigned apps. Wait for the SignPath-signed build, or build from source — see below.

#### macOS (Apple Silicon)
File: `opiter-macos-arm64.dmg`. Open the DMG and drag `Opiter.app` to Applications.

> **First-launch security warning.** Right-click the app → **"Open"** → confirm "Open" in the dialog. macOS will remember the choice for future launches. (The bundle isn't yet notarized; this step is only needed once.)

#### Linux (Debian / Ubuntu)
File: `opiter-linux-amd64.deb`.

```bash
sudo apt install ./opiter-linux-amd64.deb
```

Launch from the application menu or run `opiter` from any terminal.

### Build from source

Works on all three platforms — useful if the prebuilt binary is blocked or if you want to develop against the code.

**Prerequisites**:
- **Python 3.11** or later (uv installs it automatically)
- [**uv**](https://github.com/astral-sh/uv) package manager — install with:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- A working Qt6 display environment (Linux X11/Wayland, WSL2 + WSLg, macOS, Windows desktop)
- Optional: `libreoffice` + the [`h2orestart`](https://github.com/ebandal/H2Orestart) extension for PDF → HWP export

**Build & run**:
```bash
git clone https://github.com/juhyeonl-hub/opiter
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

# Run the test suite (186 tests)
uv run pytest
```

See [CONTRIBUTING.md](./CONTRIBUTING.md) for contribution guidelines and [ARCHITECTURE.md](./ARCHITECTURE.md) for the codebase structure.

## Documentation

| File | Purpose |
|------|---------|
| [PROJECT.md](./PROJECT.md) | Vision, philosophy, scope (what Opiter is and isn't) |
| [FEATURES.md](./FEATURES.md) | Full feature roadmap |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Module layout, data flow, design decisions |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | How to contribute |

## License

[GNU Affero General Public License v3.0 (AGPL-3.0)](./LICENSE) © 2026 juhyeonl

Opiter depends on AGPL-licensed libraries (PyMuPDF, pyhwp), so the project as a whole is licensed under AGPL-3.0. In short: you can use, modify, and redistribute it freely, but **any derivative work — including network services — must be released under the same license** with full source code.

## Acknowledgments

Opiter stands on the shoulders of excellent open-source projects:

- [PyMuPDF](https://github.com/pymupdf/PyMuPDF) (fitz) — PDF rendering, annotation, and editing core (AGPL-3.0)
- [pdf2docx](https://github.com/dothinking/pdf2docx) — PDF → DOCX conversion (MIT)
- [python-docx](https://github.com/python-openxml/python-docx) — DOCX read/write (MIT)
- [pyhwp](https://github.com/mete0r/pyhwp) — HWP text extraction (AGPL-3.0)
- [pypdf](https://github.com/py-pdf/pypdf) — PDF page-level operations (BSD)
- [pdfplumber](https://github.com/jsvine/pdfplumber) — text and table extraction (MIT)
- [PySide6](https://doc.qt.io/qtforpython-6/) — cross-platform GUI toolkit (LGPL-3.0)
- [uv](https://github.com/astral-sh/uv) — Python packaging

For PDF → HWP export, optionally requires [LibreOffice](https://www.libreoffice.org/) and the [h2orestart](https://github.com/ebandal/H2Orestart) extension.

## Code Signing

Windows binaries are code-signed by the [SignPath Foundation](https://signpath.org/) under their free certificate program for open-source projects. The macOS `.app` bundle and Linux `.deb` are currently distributed unsigned.
