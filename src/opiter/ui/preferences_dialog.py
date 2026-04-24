"""Preferences dialog — currently focused on keyboard shortcut customization.

Future tabs (annotation colors, theme, etc.) will hang off the same
dialog. The dialog is purely UI; persistence lives in
``opiter.core.preferences``.
"""
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QKeySequenceEdit,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


@dataclass(frozen=True)
class KeymapEntry:
    action_id: str
    display_name: str
    default_shortcut: str  # human-readable form, e.g. "Ctrl+O" or "" for unbound


class PreferencesDialog(QDialog):
    """Edit per-action keyboard shortcut overrides."""

    def __init__(
        self,
        registry: list[KeymapEntry],
        current_overrides: dict[str, str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Preferences — Keyboard Shortcuts")
        self.resize(560, 480)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Customize keyboard shortcuts. Leave the override field empty "
                "to use the default. Click in the override cell and press the "
                "key combination you want."
            )
        )

        self._tree = QTreeWidget()
        self._tree.setColumnCount(3)
        self._tree.setHeaderLabels(["Action", "Default", "Override"])
        self._tree.setRootIsDecorated(False)
        self._tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

        self._editors: dict[str, QKeySequenceEdit] = {}
        for entry in registry:
            item = QTreeWidgetItem(
                [entry.display_name, entry.default_shortcut or "(none)", ""]
            )
            self._tree.addTopLevelItem(item)
            edit = QKeySequenceEdit(self._tree)
            override_str = current_overrides.get(entry.action_id, "")
            if override_str:
                edit.setKeySequence(QKeySequence(override_str))
            self._tree.setItemWidget(item, 2, edit)
            self._editors[entry.action_id] = edit

        layout.addWidget(self._tree, stretch=1)

        # Reset-to-defaults clears every override.
        reset_btn = QPushButton("Reset All to Defaults")
        reset_btn.clicked.connect(self._reset_all)
        layout.addWidget(reset_btn)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _reset_all(self) -> None:
        for editor in self._editors.values():
            editor.clear()

    def get_overrides(self) -> dict[str, str]:
        """Return only non-empty overrides; empty entries fall back to defaults."""
        result: dict[str, str] = {}
        for action_id, editor in self._editors.items():
            seq = editor.keySequence()
            if not seq.isEmpty():
                result[action_id] = seq.toString()
        return result
