"""Preferences dialog — keymap + annotation colors.

Persistence lives in :mod:`opiter.core.preferences`; this module is
purely UI. The dialog has two sections (collapsible groups) inside a
single scrollable layout.
"""
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QKeySequence
from PySide6.QtWidgets import (
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHeaderView,
    QKeySequenceEdit,
    QLabel,
    QPushButton,
    QScrollArea,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


@dataclass(frozen=True)
class KeymapEntry:
    action_id: str
    display_name: str
    default_shortcut: str  # human-readable, "" for unbound


@dataclass(frozen=True)
class ColorEntry:
    pref_field: str    # name of the Preferences field (e.g. "color_highlight")
    display_name: str  # "Highlight"


class _ColorButton(QToolButton):
    """A small button whose face is filled with the current color."""

    def __init__(self, initial: tuple[float, float, float], parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(60, 22)
        self._rgb = initial
        self._refresh()
        self.clicked.connect(self._pick)

    def color(self) -> tuple[float, float, float]:
        return self._rgb

    def _refresh(self) -> None:
        # Selector-scoped so the color tint does not cascade to any child
        # widget (most importantly, to a QColorDialog that would otherwise
        # inherit and be painted entirely in the swatch color).
        r, g, b = (int(c * 255) for c in self._rgb)
        self.setStyleSheet(
            f"QToolButton {{"
            f"  background-color: rgb({r},{g},{b});"
            f"  border: 1px solid #888;"
            f"}}"
        )

    def _pick(self) -> None:
        r, g, b = (int(c * 255) for c in self._rgb)
        # Parent the dialog to the top-level window — NOT to the button —
        # so the button's swatch stylesheet does not cascade into the
        # color picker's own widgets.
        parent_window = self.window()
        chosen = QColorDialog.getColor(
            QColor(r, g, b), parent_window, "Pick a color"
        )
        if chosen.isValid():
            self._rgb = (chosen.redF(), chosen.greenF(), chosen.blueF())
            self._refresh()


class PreferencesDialog(QDialog):
    """Edit per-action shortcuts and per-tool annotation colors."""

    def __init__(
        self,
        registry: list[KeymapEntry],
        current_overrides: dict[str, str],
        color_entries: list[ColorEntry],
        current_colors: dict[str, tuple[float, float, float]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.resize(620, 620)

        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        host = QWidget()
        scroll.setWidget(host)
        layout = QVBoxLayout(host)
        outer.addWidget(scroll, stretch=1)

        # ----- Keymap group -----
        keymap_group = QGroupBox("Keyboard Shortcuts")
        kg_layout = QVBoxLayout(keymap_group)
        kg_layout.addWidget(
            QLabel(
                "Click in the override cell and press the key combination you want. "
                "Leave blank to use the default."
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
            override = current_overrides.get(entry.action_id, "")
            if override:
                edit.setKeySequence(QKeySequence(override))
            self._tree.setItemWidget(item, 2, edit)
            self._editors[entry.action_id] = edit

        kg_layout.addWidget(self._tree)
        reset_btn = QPushButton("Reset All Shortcuts to Defaults")
        reset_btn.clicked.connect(self._reset_shortcuts)
        kg_layout.addWidget(reset_btn)
        layout.addWidget(keymap_group)

        # ----- Colors group -----
        color_group = QGroupBox("Annotation Colors")
        cg_form = QFormLayout(color_group)
        self._color_buttons: dict[str, _ColorButton] = {}
        for entry in color_entries:
            initial = current_colors.get(entry.pref_field, (0.0, 0.0, 0.0))
            btn = _ColorButton(initial)
            self._color_buttons[entry.pref_field] = btn
            cg_form.addRow(entry.display_name, btn)
        layout.addWidget(color_group)

        # ----- Buttons -----
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    def _reset_shortcuts(self) -> None:
        for editor in self._editors.values():
            editor.clear()

    def get_overrides(self) -> dict[str, str]:
        result: dict[str, str] = {}
        for action_id, editor in self._editors.items():
            seq = editor.keySequence()
            if not seq.isEmpty():
                result[action_id] = seq.toString()
        return result

    def get_colors(self) -> dict[str, tuple[float, float, float]]:
        return {fname: btn.color() for fname, btn in self._color_buttons.items()}
