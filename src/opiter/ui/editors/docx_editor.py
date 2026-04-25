# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 juhyeonl
"""DOCX viewer tab — two rendering tiers.

Tier 1 (preferred): LibreOffice converts the DOCX to PDF in the
background, and we render the PDF inside a ``QPdfView``. Result is
pixel-perfect: page layout, fonts, colors, highlights, embedded
images all come through.

Tier 2 (fallback): when LibreOffice isn't installed, we fall back to
``mammoth``-produced semantic HTML rendered in a ``QTextEdit``.
Tables, lists, headings, basic inline formatting survive; page
layout and color highlights don't.

The chosen tier is decided per-open via ``office_conversion_available``.
A ``QStackedWidget`` swaps the visible widget between the two views.
"""
from __future__ import annotations

from pathlib import Path

import mammoth
from PySide6.QtCore import QUrl
from PySide6.QtGui import QFont
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtWidgets import QStackedWidget, QTextEdit, QVBoxLayout

from opiter.core.office_to_pdf import convert_to_pdf, office_conversion_available
from opiter.ui.cjk_font import cjk_family_chain
from opiter.ui.editors.abstract_editor import AbstractEditor


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
    """Render a .docx as HTML using mammoth's default style map."""
    with open(path, "rb") as f:
        result = mammoth.convert_to_html(f)
    body = result.value or ""
    return f"<html><head>{_HTML_PROLOGUE}</head><body>{body}</body></html>"


class DOCXEditor(AbstractEditor):
    """Read-only DOCX viewer with PDF (preferred) or HTML (fallback) rendering."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._stack = QStackedWidget(self)
        layout.addWidget(self._stack)

        # Tier 2: HTML fallback
        self._text = QTextEdit()
        self._text.setReadOnly(True)
        font = QFont()
        font.setFamilies(cjk_family_chain())
        font.setPointSize(11)
        self._text.setFont(font)
        self._stack.addWidget(self._text)

        # Tier 1: PDF view
        self._pdf_doc = QPdfDocument(self)
        self._pdf_view = QPdfView()
        self._pdf_view.setDocument(self._pdf_doc)
        self._pdf_view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        self._pdf_view.setPageMode(QPdfView.PageMode.MultiPage)
        self._stack.addWidget(self._pdf_view)

        self._path: Path | None = None

    # ------------------------------------------------------------ interface
    def open_file(self, path: str | Path) -> None:
        p = Path(path)
        if office_conversion_available():
            try:
                pdf_path = convert_to_pdf(p)
                self._pdf_doc.load(str(pdf_path))
                self._stack.setCurrentWidget(self._pdf_view)
                self._path = p
                self.title_changed.emit(self.display_name())
                return
            except Exception as exc:
                self.status_message.emit(
                    f"LibreOffice conversion failed; using fallback: {exc}",
                    6000,
                )
        # Fallback to mammoth HTML.
        html_str = docx_to_html(p)
        self._text.setHtml(html_str)
        self._stack.setCurrentWidget(self._text)
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
