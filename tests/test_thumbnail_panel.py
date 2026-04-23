"""Tests for opiter.ui.thumbnail_panel."""
from __future__ import annotations

from pathlib import Path

import fitz
import pytest
from PySide6.QtCore import Qt

from opiter.core.document import Document
from opiter.ui.thumbnail_panel import ThumbnailPanel


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    doc = fitz.open()
    for i in range(5):
        page = doc.new_page()
        page.insert_text((50, 100), f"Page {i + 1}", fontsize=24)
    out = tmp_path / "sample.pdf"
    doc.save(out)
    doc.close()
    return out


def test_initial_panel_is_empty(qtbot):
    p = ThumbnailPanel()
    qtbot.addWidget(p)
    assert p.count() == 0


def test_set_document_populates_one_item_per_page(qtbot, sample_pdf):
    p = ThumbnailPanel()
    qtbot.addWidget(p)
    p.set_document(Document.open(sample_pdf))
    assert p.count() == 5


def test_each_item_has_pixmap_icon(qtbot, sample_pdf):
    p = ThumbnailPanel()
    qtbot.addWidget(p)
    p.set_document(Document.open(sample_pdf))
    for i in range(p.count()):
        item = p.item(i)
        assert not item.icon().isNull()


def test_item_click_emits_page_clicked_with_index(qtbot, sample_pdf):
    p = ThumbnailPanel()
    qtbot.addWidget(p)
    p.set_document(Document.open(sample_pdf))
    with qtbot.waitSignal(p.page_clicked, timeout=1000) as blocker:
        p.itemClicked.emit(p.item(2))
    assert blocker.args == [2]


def test_select_page_sets_current_row(qtbot, sample_pdf):
    p = ThumbnailPanel()
    qtbot.addWidget(p)
    p.set_document(Document.open(sample_pdf))
    p.select_page(3)
    assert p.currentRow() == 3


def test_select_page_does_not_emit_page_clicked(qtbot, sample_pdf):
    """Programmatic selection (e.g. mirroring viewer state) must not fire a click."""
    p = ThumbnailPanel()
    qtbot.addWidget(p)
    p.set_document(Document.open(sample_pdf))
    with qtbot.assertNotEmitted(p.page_clicked):
        p.select_page(2)


def test_drag_drop_mode_is_internal_move(qtbot):
    """Reorder by drag is enabled."""
    from PySide6.QtWidgets import QAbstractItemView
    p = ThumbnailPanel()
    qtbot.addWidget(p)
    assert p.dragDropMode() == QAbstractItemView.DragDropMode.InternalMove


def test_relabel_after_reorder_resets_text_and_userrole(qtbot, sample_pdf):
    """After Qt has visually moved items, the parent calls relabel_after_reorder
    so each item's UserRole maps to its current row index."""
    p = ThumbnailPanel()
    qtbot.addWidget(p)
    p.set_document(Document.open(sample_pdf))

    # Simulate user-shuffled UserRoles (as if Qt drag-drop happened)
    p.item(0).setData(Qt.ItemDataRole.UserRole, 4)
    p.item(0).setText("Page 5")
    p.item(4).setData(Qt.ItemDataRole.UserRole, 0)
    p.item(4).setText("Page 1")

    p.relabel_after_reorder()

    for i in range(p.count()):
        assert p.item(i).data(Qt.ItemDataRole.UserRole) == i
        assert p.item(i).text() == f"Page {i + 1}"


def test_set_document_replaces_previous_contents(qtbot, sample_pdf, tmp_path):
    p = ThumbnailPanel()
    qtbot.addWidget(p)
    p.set_document(Document.open(sample_pdf))
    assert p.count() == 5

    # smaller doc
    doc = fitz.open()
    doc.new_page()
    doc.new_page()
    out = tmp_path / "two.pdf"
    doc.save(out)
    doc.close()

    p.set_document(Document.open(out))
    assert p.count() == 2
