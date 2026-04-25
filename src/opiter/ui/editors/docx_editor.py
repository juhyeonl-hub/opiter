# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 juhyeonl
"""DOCX viewer tab — read-only HTML rendering via mammoth.

We use `mammoth <https://github.com/mwilliamson/python-mammoth>`_ to
turn the .docx into semantic HTML. Mammoth handles paragraphs,
headings, lists (bulleted and numbered), tables (including merged
cells), bold / italic / underline / strikethrough, hyperlinks, and
inline images, and emits clean class-based HTML that QTextEdit can
display directly. Anything mammoth flags as a conversion warning is
silently dropped — the user just sees the best-effort rendering.

For maximum fidelity (page layout, exact fonts) a future iteration
can convert DOCX → PDF via LibreOffice and render through PyMuPDF;
this file is the no-extra-dependency tier.
"""
from __future__ import annotations

from pathlib import Path

import mammoth
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QTextEdit, QVBoxLayout

from opiter.ui.cjk_font import cjk_family_chain
from opiter.ui.editors.abstract_editor import AbstractEditor


# Light QSS embedded into the rendered HTML so the document looks
# typographically reasonable inside QTextEdit. QTextEdit only supports
# a subset of CSS, hence the conservative rules.
_HTML_PROLOGUE = """
<style>
  body { font-family: sans-serif; line-height: 1.45; color: #141414; }
  h1 { font-size: 22pt; margin: 14pt 0 8pt; }
  h2 { font-size: 18pt; margin: 12pt 0 6pt; }
  h3 { font-size: 15pt; margin: 10pt 0 5pt; }
  h4 { font-size: 13pt; margin: 8pt 0 4pt; }
  p  { margin: 4pt 0; }
  table { border-collapse: collapse; margin: 6pt 0; }
  td, th { border: 1px solid #888; padding: 4px 6px; vertical-align: top; }
  th { background: #eaeaea; font-weight: bold; }
  ul, ol { margin: 4pt 0; padding-left: 24pt; }
  li { margin: 2pt 0; }
  blockquote { margin: 6pt 16pt; color: #444; border-left: 3px solid #bbb;
               padding-left: 10pt; }
  a { color: #0066cc; }
</style>
"""


def docx_to_html(path: str | Path) -> str:
    """Render a .docx as HTML using mammoth's default style map.

    Conversion warnings (unsupported element variants, etc.) are
    discarded — best-effort rendering is preferred over a half-empty
    viewer.
    """
    with open(path, "rb") as f:
        result = mammoth.convert_to_html(f)
    body = result.value or ""
    return f"<html><head>{_HTML_PROLOGUE}</head><body>{body}</body></html>"


class DOCXEditor(AbstractEditor):
    """Read-only DOCX viewer."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._edit = QTextEdit()
        self._edit.setReadOnly(True)
        font = QFont()
        font.setFamilies(cjk_family_chain())
        font.setPointSize(11)
        self._edit.setFont(font)
        layout.addWidget(self._edit)

        self._path: Path | None = None

    # ------------------------------------------------------------ interface
    def open_file(self, path: str | Path) -> None:
        p = Path(path)
        html_str = docx_to_html(p)
        self._edit.setHtml(html_str)
        self._path = p
        self.title_changed.emit(self.display_name())

    def save(self) -> None:
        self.status_message.emit(
            "DOCX editing is not yet supported — use Save As or export to PDF.",
            4000,
        )

    def save_as(self, path: str | Path) -> None:
        self.status_message.emit(
            "DOCX editing is not yet supported.", 4000
        )

    def is_modified(self) -> bool:
        return False

    def file_path(self) -> Path | None:
        return self._path
