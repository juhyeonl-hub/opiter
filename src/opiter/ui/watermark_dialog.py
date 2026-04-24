"""Watermark configuration dialog (text only for MVP; image picker optional)."""
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import (
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
        self._rotate = QSpinBox()
        self._rotate.setRange(-180, 180)
        self._rotate.setValue(45)

        form.addRow("Text", self._text)
        form.addRow("Font size (pt)", self._fontsize)
        form.addRow("Opacity (0-1)", self._opacity)
        form.addRow("Rotation (degrees)", self._rotate)
        outer.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    def settings(self) -> WatermarkSettings:
        return WatermarkSettings(
            text=self._text.text().strip(),
            fontsize=self._fontsize.value(),
            opacity=self._opacity.value(),
            rotate=self._rotate.value(),
        )
