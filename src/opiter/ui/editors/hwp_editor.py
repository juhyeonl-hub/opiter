# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 juhyeonl
"""HWP viewer tab — text extraction via pyhwp, rendered as plain text.

HWP (Hangul Word Processor) support is limited in the Python ecosystem:
``pyhwp`` extracts text for HWP 5 format reliably but does not preserve
layout. For MVP we display extracted text in a read-only QTextEdit.
More faithful rendering (LibreOffice-based) can come in a later polish
brief.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QTextEdit, QVBoxLayout

from opiter.ui.cjk_font import cjk_family_chain
from opiter.ui.editors.abstract_editor import AbstractEditor


def _extract_hwp_text(path: str | Path) -> str:
    """Best-effort text extraction from an HWP 5 file.

    Falls back to a descriptive error string if the file cannot be read
    or if pyhwp's API shape differs from expectations on this install.
    """
    try:
        # pyhwp exports its modules under the top-level `hwp5` package.
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
        # Walk every section, picking ParaText records and joining the
        # string payloads out of their (range, payload) chunk tuples.
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
                        # carriage return marker — paragraph break
                        if buf.strip():
                            lines.append(buf)
                        buf = ""
            if buf.strip():
                lines.append(buf)
        return "\n".join(lines) if lines else "[HWP file had no extractable text]"
    except Exception as exc:  # pragma: no cover - catch-all
        return f"[Could not read HWP file: {exc}]"


class HWPEditor(AbstractEditor):
    """Read-only HWP text viewer."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._edit = QTextEdit()
        self._edit.setReadOnly(True)
        self._edit.setPlaceholderText("HWP text content will appear here.")
        font = QFont()
        font.setFamilies(cjk_family_chain())
        font.setPointSize(11)
        self._edit.setFont(font)
        layout.addWidget(self._edit)

        self._path: Path | None = None

    def open_file(self, path: str | Path) -> None:
        p = Path(path)
        text = _extract_hwp_text(p)
        self._edit.setPlainText(text)
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
