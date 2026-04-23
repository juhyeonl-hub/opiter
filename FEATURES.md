# Opiter — Feature Roadmap

Legend: ✅ Done · 🚧 In progress · 📋 Planned · 🔮 Long-term

> The current MVP scope (Phase 1~3) is tracked in detail in [PROJECT_BRIEF.md](./PROJECT_BRIEF.md). This document is the long-term roadmap.

---

## Phase 1: Basic Viewer 🚧 *(MVP scope)*

| Feature | Status |
|---------|--------|
| Open PDF (file dialog, drag-and-drop, recent files) | 📋 |
| Multi-page rendering | 📋 |
| Page navigation (next/prev, keyboard, page jump) | 📋 |
| Zoom controls (fit-to-width, fit-to-page, custom %) | 📋 |
| Thumbnail sidebar with click-to-jump | 📋 |
| Text search (current page + full document) | 📋 |
| Dark mode / light mode toggle | 📋 |

**Verification target**: Open a 10-page PDF, navigate to last page, zoom to 200%, search for a common word, toggle dark mode.

---

## Phase 2: Page Manipulation 🚧 *(MVP scope)*

| Feature | Status |
|---------|--------|
| Add page (blank or from another PDF) | 📋 |
| Delete page (single or range) | 📋 |
| Reorder pages (drag in sidebar) | 📋 |
| Rotate page (90° increments) | 📋 |
| Merge multiple PDFs into one | 📋 |
| Split PDF (by range or per-page) | 📋 |
| Extract pages (save selection as new PDF) | 📋 |

**Verification target**: Output files must open correctly in independent PDF viewers (e.g., evince, browser).

---

## Phase 3: Annotations 🚧 *(MVP scope)*

| Feature | Status |
|---------|--------|
| Text markup: highlight / underline / strikethrough | 📋 |
| Sticky notes (anchored pop-up comments) | 📋 |
| Freehand drawing (configurable color/thickness) | 📋 |
| Shapes: rectangle, ellipse, arrow | 📋 |
| Text box (arbitrary text on page) | 📋 |
| Annotation persistence in standard PDF format | 📋 |

**Verification target**: Annotations must survive save/reload and render correctly in other PDF viewers.

---

## Phase 4: Advanced PDF 📋 *(Post-MVP)*

- PDF → Image (PNG, JPG) — per-page or batch
- Image → PDF (compile images into PDF)
- PDF compression (quality/size tradeoff)
- Watermark (text or image overlay)
- Metadata editing (title, author, subject, keywords)
- Bookmarks / outline editing

## Phase 5: Multi-Format 🔮 *(Long-term)*

- DOCX support (view/edit)
- HWP support (view/edit)
- Format conversion (PDF ↔ DOCX, etc.)
- Unified document model across formats

## Beyond Phase 5 🔮

- OCR (text recognition from scanned documents)
- Form filling (PDF AcroForm / XFA)
- Digital signatures (sign / verify)
- Plugin system

---

## Non-Goals

Explicitly **out of scope** for this project (see [PROJECT.md](./PROJECT.md) for rationale):

- DRM circumvention / password-bypass for protected PDFs
- Server-side rendering / web service
- Mobile apps (iOS/Android)
- AI-based content generation
- Cloud-based collaboration (real-time multi-user editing)

---

## Platform Support

| OS | Phase 1~3 (MVP) | Post-MVP |
|----|-----------------|----------|
| Linux | ✅ Primary dev target (WSL2/WSLg now, native later) | ✅ |
| Windows | 🔮 Planned after MVP (PyInstaller / Nuitka) | ✅ |
| macOS | 🔮 Planned after MVP (PyInstaller / Nuitka) | ✅ |
