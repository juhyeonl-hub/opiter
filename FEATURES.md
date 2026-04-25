# Opiter — Feature Roadmap

Legend: ✅ Done · 🚧 In progress · 📋 Planned · 🔮 Long-term

---

## v0.1 — Shipped ✅

### PDF (full editor)

| Feature | Status |
|---------|--------|
| Open PDF (file dialog, recent files, encrypted with password) | ✅ |
| Multi-page rendering with QScrollArea + zoom (fit/actual/fit-width) | ✅ |
| Page navigation (PgUp/PgDn, Home/End, Go-to-page) | ✅ |
| Thumbnail sidebar (click-to-jump, drag-reorder, multi-select) | ✅ |
| Full-text search (rotation-aware highlighting) | ✅ |
| Dark mode / light mode toggle | ✅ |
| Add / delete / insert blank / rotate pages | ✅ |
| Merge multiple PDFs | ✅ |
| Split (by range or per-page) | ✅ |
| Extract pages | ✅ |
| Annotations: highlight, underline, strikethrough (with auto-merge of adjacent runs) | ✅ |
| Annotations: sticky note, freehand pen, rectangle, ellipse, arrow, text box | ✅ |
| Pointer tool: select / move / delete annotations | ✅ |
| Per-document undo/redo (snapshot-based) | ✅ |
| Image export (PNG/JPG, per-page or batch) | ✅ |
| Image → PDF (auto-opens result) | ✅ |
| Compression (3 quality presets) | ✅ |
| Text watermark (4 rotations, rotation-aware on rotated pages) | ✅ |
| Document properties / metadata editing | ✅ |
| Bookmarks / TOC editing dock | ✅ |
| Multi-PDF tabs (independent state, undo, dedup on re-open) | ✅ |

### DOCX (viewer)

| Feature | Status |
|---------|--------|
| Open .docx, render headings / bold / italic / underline / tables | ✅ |
| CJK font fallback (Malgun Gothic / Noto CJK / NanumGothic) | ✅ |
| Multi-DOCX tabs | ✅ |

### HWP (viewer)

| Feature | Status |
|---------|--------|
| Text extraction via pyhwp | ✅ |
| Korean / Hanja rendering | ✅ |
| Multi-HWP tabs | ✅ |

### Cross-format export

| Feature | Status |
|---------|--------|
| PDF → DOCX (pdf2docx) | ✅ |
| PDF → HWP (best-effort via LibreOffice + h2orestart, auto-detected) | ✅ |

---

## Post-v0.1 Roadmap

### Phase 6 — DOCX editing 📋

- Inline text editing in QTextEdit
- Basic styling: bold / italic / underline / heading levels
- Paragraph add / delete / reorder
- Table edits
- Save back to .docx with format preservation

### Distribution 📋

- Windows installer (PyInstaller + Inno Setup)
- macOS .app bundle (PyInstaller, code signing)
- Auto-update mechanism

### Other 🔮

- OCR for scanned PDFs (tesseract)
- Form filling (PDF AcroForm)
- Digital signatures (sign / verify)
- Batch processing CLI
- Plugin system

---

## Non-Goals

Explicitly **out of scope** (see [PROJECT.md](./PROJECT.md) for rationale):

- DRM circumvention / password-bypass for protected PDFs
- Server-side rendering / web service
- Mobile apps (iOS/Android)
- AI-based content generation
- Cloud-based collaboration (real-time multi-user editing)
- HWP editing (read-only by design — no viable Python writer for the format)

---

## Platform Support

| OS | v0.1 |
|----|------|
| Linux (X11 / Wayland / WSL2+WSLg) | ✅ Primary |
| Windows | 📋 Planned (build from source via uv works; native installer post v0.1) |
| macOS | 📋 Planned (same caveat) |
