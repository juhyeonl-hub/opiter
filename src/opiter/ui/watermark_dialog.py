# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 juhyeonl
"""Watermark configuration dialog (text only for MVP; image picker optional)."""
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


@dataclass
class WatermarkSettings:
    text: str
    fontsize: int
    opacity: float
    rotate: int


class WatermarkDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Watermark")
        self.resize(420, 220)

        outer = QVBoxLayout(self)
        form = QFormLayout()

        self._text = QLineEdit("CONFIDENTIAL")
        self._fontsize = QSpinBox()
        self._fontsize.setRange(10, 200)
        self._fontsize.setValue(48)
        self._opacity = QDoubleSpinBox()
        self._opacity.setRange(0.05, 1.0)
        self._opacity.setSingleStep(0.05)
        self._opacity.setValue(0.35)
        # PyMuPDF's FreeText annot only accepts rotate values of 0/90/180/270.
        # Arbitrary angles (e.g. 45°) silently fail to render.
        self._rotate = QComboBox()
        self._rotate.addItems(["0° (horizontal)", "90°", "180°", "270°"])
        self._rotate.setCurrentIndex(0)

        form.addRow("Text", self._text)
        form.addRow("Font size (pt)", self._fontsize)
        form.addRow("Opacity (0-1)", self._opacity)
        form.addRow("Rotation", self._rotate)
        outer.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    def settings(self) -> WatermarkSettings:
        rotate_map = {0: 0, 1: 90, 2: 180, 3: 270}
        return WatermarkSettings(
            text=self._text.text().strip(),
            fontsize=self._fontsize.value(),
            opacity=self._opacity.value(),
            rotate=rotate_map.get(self._rotate.currentIndex(), 0),
        )
