# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 juhyeonl
"""HWP viewer tab — two rendering tiers.

Tier 1 (preferred): LibreOffice + the ``h2orestart`` extension converts
the HWP to PDF in the background, and we render the PDF inside a
``QPdfView``. Result is full-fidelity (page layout, fonts, tables,
images, colors).

Tier 2 (fallback): when LibreOffice or h2orestart is unavailable we
fall back to ``pyhwp`` text extraction in a ``QTextEdit``. The
fallback only recovers paragraph text — no layout.

A ``QStackedWidget`` swaps the visible widget between the two views.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QFont
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtWidgets import QMessageBox, QStackedWidget, QTextEdit, QVBoxLayout

from opiter.core.office_to_pdf import convert_to_pdf, office_conversion_available
from opiter.ui.cjk_font import cjk_family_chain
from opiter.ui.editors.abstract_editor import AbstractEditor


def _extract_hwp_text(path: str | Path) -> str:
    """Best-effort text extraction from an HWP 5 file via pyhwp."""
    try:
        from hwp5 import xmlmodel  # type: ignore[import-untyped]
        from hwp5.binmodel import ParaText  # type: ignore[import-untyped]
        from hwp5.dataio import ParseError  # type: ignore[import-untyped]
    except ImportError:
        return "[HWP support requires pyhwp — install it to view .hwp files]"

    try:
        try:
            hwp = xmlmodel.Hwp5File(str(path))
        except ParseError as exc:
            return f"[HWP parse error: {exc}]"

        lines: list[str] = []
        for idx in range(len(hwp.bodytext.sections)):
            section = hwp.bodytext.section(idx)
            buf = ""
            for model in section.models():
                if model["type"] is not ParaText:
                    continue
                for _, payload in model["content"].get("chunks") or []:
                    if isinstance(payload, str):
                        buf += payload
                    elif isinstance(payload, dict) and payload.get("code") == 13:
                        if buf.strip():
                            lines.append(buf)
                        buf = ""
            if buf.strip():
                lines.append(buf)
        return "\n".join(lines) if lines else "[HWP file had no extractable text]"
    except Exception as exc:  # pragma: no cover - catch-all
        return f"[Could not read HWP file: {exc}]"


class HWPEditor(AbstractEditor):
    """Read-only HWP viewer with PDF (preferred) or text (fallback) rendering."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._stack = QStackedWidget(self)
        layout.addWidget(self._stack)

        # Tier 2: text fallback
        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setPlaceholderText("HWP text content will appear here.")
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
                QMessageBox.warning(
                    self,
                    "HWP rendering — using text-only view",
                    "Opiter found LibreOffice but couldn't convert this "
                    "HWP file to PDF, so it is showing the text fallback "
                    "instead.\n\nThe most common cause is the H2Orestart "
                    "extension not being loaded into LibreOffice.\n\n"
                    f"Reason:\n{exc}",
                )
        text = _extract_hwp_text(p)
        self._text.setPlainText(text)
        self._stack.setCurrentWidget(self._text)
        self._path = p
        self.title_changed.emit(self.display_name())

    def save(self) -> None:
        self.status_message.emit(
            "HWP editing is not supported — export to PDF or DOCX.", 4000
        )

    def save_as(self, path: str | Path) -> None:
        self.status_message.emit(
            "HWP editing is not supported.", 4000
        )

    def is_modified(self) -> bool:
        return False

    def file_path(self) -> Path | None:
        return self._path
