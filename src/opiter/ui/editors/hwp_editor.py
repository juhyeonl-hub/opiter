"""HWP viewer tab — text extraction via pyhwp, rendered as plain text.

HWP (Hangul Word Processor) support is limited in the Python ecosystem:
``pyhwp`` extracts text for HWP 5 format reliably but does not preserve
layout. For MVP we display extracted text in a read-only QTextEdit.
More faithful rendering (LibreOffice-based) can come in a later polish
brief.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QTextEdit, QVBoxLayout

from opiter.ui.editors.abstract_editor import AbstractEditor


def _extract_hwp_text(path: str | Path) -> str:
    """Best-effort text extraction from an HWP 5 file.

    Falls back to a descriptive error string if the file cannot be read
    or if pyhwp's API shape differs from expectations on this install.
    """
    try:
        # pyhwp's Python API is fairly thin; exposure varies per release.
        from pyhwp.hwp5 import xmlmodel  # type: ignore[import-untyped]
        from pyhwp.hwp5.dataio import ParseError  # type: ignore[import-untyped]

        try:
            hwp = xmlmodel.Hwp5File(str(path))
        except ParseError as exc:
            return f"[HWP parse error: {exc}]"

        lines: list[str] = []
        try:
            for section in hwp.bodytext.sections:
                for para in section.paragraphs:
                    text = ""
                    for char in para.content:
                        t = getattr(char, "text", None)
                        if t:
                            text += t
                    if text:
                        lines.append(text)
        except Exception as exc:  # pragma: no cover - pyhwp shape varies
            return f"[HWP read error: {exc}]"
        return "\n".join(lines) if lines else "[HWP file had no extractable text]"
    except ImportError:
        return "[HWP support requires pyhwp — install it to view .hwp files]"
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
