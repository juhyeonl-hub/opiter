# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 juhyeonl
"""Export dialog for PDF → DOCX / PDF → HWP (options + file picker)."""
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)


@dataclass
class ExportOptions:
    include_annotations: bool


class ExportOptionsDialog(QDialog):
    """Lightweight dialog that asks whether annotations should be included."""

    def __init__(
        self,
        title: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(420, 160)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Some annotations (highlights, pen strokes, shapes, etc.) may "
                "not survive export. Unchecking the box below produces a cleaner "
                "result but drops your markup."
            )
        )
        self._include = QCheckBox("Include annotations in the exported file")
        self._include.setChecked(False)
        layout.addWidget(self._include)
        layout.addStretch(1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def options(self) -> ExportOptions:
        return ExportOptions(include_annotations=self._include.isChecked())
