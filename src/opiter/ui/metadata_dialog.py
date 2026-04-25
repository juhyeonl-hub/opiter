# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 juhyeonl
"""Document metadata editor dialog (title / author / subject / keywords / creator)."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from opiter.core.metadata import Metadata


class MetadataDialog(QDialog):
    def __init__(self, current: Metadata, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Document Properties")
        self.resize(460, 260)

        outer = QVBoxLayout(self)
        form = QFormLayout()

        self._title = QLineEdit(current.title)
        self._author = QLineEdit(current.author)
        self._subject = QLineEdit(current.subject)
        self._keywords = QLineEdit(current.keywords)
        self._creator = QLineEdit(current.creator)

        form.addRow("Title", self._title)
        form.addRow("Author", self._author)
        form.addRow("Subject", self._subject)
        form.addRow("Keywords", self._keywords)
        form.addRow("Creator", self._creator)
        outer.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    def get_metadata(self) -> Metadata:
        return Metadata(
            title=self._title.text(),
            author=self._author.text(),
            subject=self._subject.text(),
            keywords=self._keywords.text(),
            creator=self._creator.text(),
        )
