"""Undo/Redo support backed by full-document snapshots.

Each mutating operation pushes a :class:`SnapshotCommand` onto the
window's QUndoStack. The command captures the document bytes before
applying the operation (for undo) and after (for re-redo after an
undo). Operation-specific inverses would be lighter on memory but
require an inverse for every mutation; snapshots cover everything
uniformly with a single class.

Memory cost is bounded by the QUndoStack's undoLimit (set to 30 in
MainWindow). For a 10 MB PDF that's roughly 600 MB worst-case (before
+ after × 30 commands), which is acceptable for desktop use.
"""
from __future__ import annotations

from typing import Callable

from PySide6.QtGui import QUndoCommand

from opiter.core.document import Document


class SnapshotCommand(QUndoCommand):
    """Document-level snapshot-based undo command.

    On first ``redo`` (i.e. when QUndoStack.push runs) it:
      1. captures the document's current bytes (``before``),
      2. invokes ``apply_fn`` to perform the mutation,
      3. captures the document's new bytes (``after``).

    On subsequent ``redo`` (after a previous ``undo``) it restores the
    ``after`` snapshot. ``undo`` always restores ``before``. After every
    redo/undo, ``on_state_change`` runs so the UI can refresh.
    """

    def __init__(
        self,
        label: str,
        document: Document,
        apply_fn: Callable[[], None],
        on_state_change: Callable[[], None],
    ) -> None:
        super().__init__(label)
        self._doc = document
        self._apply_fn = apply_fn
        self._on_state_change = on_state_change
        self._before: bytes | None = None
        self._after: bytes | None = None
        self._first_run = True

    def redo(self) -> None:
        if self._first_run:
            self._before = self._doc.snapshot()
            self._apply_fn()
            self._after = self._doc.snapshot()
            self._first_run = False
        elif self._after is not None:
            self._doc.replace_content(self._after)
        self._on_state_change()

    def undo(self) -> None:
        if self._before is not None:
            self._doc.replace_content(self._before)
        self._on_state_change()
