"""Tests for opiter.core.undo (snapshot-based undo/redo)."""
from __future__ import annotations

from pathlib import Path

import fitz
import pytest
from PySide6.QtGui import QUndoStack

from opiter.core.document import Document
from opiter.core.undo import SnapshotCommand


@pytest.fixture
def numbered_pdf(tmp_path: Path) -> Path:
    doc = fitz.open()
    for i in range(3):
        p = doc.new_page()
        p.insert_text((50, 100), f"Page_{i + 1}_marker", fontsize=14)
    out = tmp_path / "n.pdf"
    doc.save(out)
    doc.close()
    return out


def _page_text(doc: Document, idx: int) -> str:
    return doc.page(idx).get_text("text").strip()


def test_snapshot_command_redo_applies_then_undo_restores(qtbot, numbered_pdf):
    refreshes: list[int] = []
    with Document.open(numbered_pdf) as doc:
        stack = QUndoStack()
        cmd = SnapshotCommand(
            "Rotate p1",
            doc,
            lambda: doc.rotate_page(0, 90),
            lambda: refreshes.append(1),
        )
        stack.push(cmd)
        assert doc.page_rotation(0) == 90
        assert refreshes == [1]

        stack.undo()
        assert doc.page_rotation(0) == 0  # reverted
        assert refreshes == [1, 1]

        stack.redo()
        assert doc.page_rotation(0) == 90  # re-applied
        assert refreshes == [1, 1, 1]


def test_snapshot_undo_chain_rotate_then_delete(qtbot, numbered_pdf):
    """Multiple commands: undo each one in LIFO order."""
    with Document.open(numbered_pdf) as doc:
        stack = QUndoStack()
        # Op 1: rotate page 0
        stack.push(SnapshotCommand(
            "rot", doc, lambda: doc.rotate_page(0, 90), lambda: None
        ))
        # Op 2: delete page 1 (originally Page_2)
        stack.push(SnapshotCommand(
            "del", doc, lambda: doc.delete_page(1), lambda: None
        ))
        assert doc.page_count == 2
        assert doc.page_rotation(0) == 90

        # Undo delete
        stack.undo()
        assert doc.page_count == 3
        assert "Page_2_marker" in _page_text(doc, 1)
        assert doc.page_rotation(0) == 90  # rotation still applied

        # Undo rotate
        stack.undo()
        assert doc.page_rotation(0) == 0
        assert doc.page_count == 3

        # Redo rotate
        stack.redo()
        assert doc.page_rotation(0) == 90

        # Redo delete
        stack.redo()
        assert doc.page_count == 2


def test_snapshot_command_delete_undo_restores_page_content(qtbot, numbered_pdf):
    """Whole-document snapshots cover even hard-to-invert ops like page deletion."""
    with Document.open(numbered_pdf) as doc:
        stack = QUndoStack()
        # Capture page 1's marker
        before = _page_text(doc, 1)
        assert "Page_2_marker" in before

        stack.push(SnapshotCommand(
            "Delete page 2", doc, lambda: doc.delete_page(1), lambda: None
        ))
        assert doc.page_count == 2

        stack.undo()
        assert doc.page_count == 3
        # Content of page 1 must match exactly what it was
        assert _page_text(doc, 1) == before
