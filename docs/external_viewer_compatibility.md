# External PDF Viewer Compatibility Matrix

> Polish phase D-2 — documents how Opiter-produced annotations render in
> third-party PDF viewers. Opiter writes standard PDF `/Annot` types, so
> behavior depends primarily on each viewer's rendering of those types.
>
> **Last verified**: 2026-04-24 (initial baseline; refresh per release).

## Annotation type → standard PDF /Annot mapping

| Opiter tool | PDF /Annot subtype | Notes |
|-------------|-------------------|-------|
| Highlight | `/Highlight` | Per-word quads, color from prefs |
| Underline | `/Underline` | Per-word quads |
| Strikeout | `/StrikeOut` | Per-word quads |
| Sticky Note | `/Text` | Pop-up note; icon orientation viewer-dependent |
| Pen | `/Ink` | List of strokes; stroke color/width set |
| Rectangle | `/Square` | Stroke-only; fill not used |
| Ellipse | `/Circle` | PDF spec name for ellipse annot |
| Arrow | `/Line` with `LE_OPEN_ARROW` end | Open arrow head at end-point only |
| Text Box | `/FreeText` | `rotate` set to match page rotation so text reads upright |

## Viewer matrix

Legend: ✅ renders correctly, ⚠️ renders but with quirks, ❌ broken/missing,
N/T not tested.

| Annotation | Adobe Acrobat Reader | Foxit | Chrome PDF.js (built-in) | Firefox PDF.js | evince (GNOME) | VS Code (vscode-pdf) |
|------------|----------------------|-------|--------------------------|----------------|----------------|----------------------|
| Highlight  | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Underline  | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ thin |
| Strikeout  | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Sticky Note (icon) | ✅ | ✅ | ⚠️ minimal icon | ⚠️ minimal icon | ✅ | ⚠️ different icon style |
| Sticky Note (popup content) | ✅ click → popup | ✅ click → popup | ⚠️ inline label | ⚠️ inline label | ✅ click → popup | ⚠️ inline label only |
| Pen / Ink | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Rectangle | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Ellipse | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Arrow | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ no arrow head |
| Text Box (FreeText) | ✅ | ✅ | ✅ | ✅ | ⚠️ no border by default | ⚠️ rendered as small box |

## Known quirks (verified by users)

- **VS Code `vscode-pdf` extension**: renders FreeText with a sticky-note-style
  yellow background (instead of plain text). This is a viewer styling
  choice — the underlying PDF data is correct. Open in any other viewer
  to see the intended FreeText rendering.
- **Browser PDF.js (Chrome / Firefox)**: sticky note popups appear as
  inline text labels rather than expandable icons. Functional but
  different UX than Adobe.
- **evince**: FreeText box has no visible border by default (Adobe shows
  one). Text content still renders correctly.

## Page rotation

All viewers tested respect the PDF `/Rotate` field — i.e. if Opiter saves
the page as 90°-rotated, the viewer displays it landscape. Annotations
placed via Opiter's Pointer/derotation pipeline land at the user's
intended visual location in any of the viewers above.

FreeText `rotate` property is honored by Adobe / Foxit / PDF.js (text
appears upright in the rotated view). evince and `vscode-pdf` ignore the
property and render text at the unrotated baseline — the text is still
present and readable, just at a different orientation than what the user
saw while authoring.

## Areas still untested

- Mobile viewers (iOS Files preview, Adobe Mobile, etc.)
- macOS Preview
- Specialized industry viewers (PDF/A archival viewers)
- HiDPI / retina rendering accuracy across viewers

These belong to a separate compatibility-test pass after the multi-OS
packaging step.
