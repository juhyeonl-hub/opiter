"""Tests for opiter.ui.viewer_widget (page navigation behavior)."""
from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from opiter.core.document import Document
from opiter.ui.viewer_widget import ViewerWidget


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


def test_initial_state_no_document(qtbot):
    w = ViewerWidget()
    qtbot.addWidget(w)
    assert not w.has_document()
    assert w.page_count == 0
    assert w.current_page == 0


def test_set_document_emits_page_changed_with_first_page(qtbot, sample_pdf):
    w = ViewerWidget()
    qtbot.addWidget(w)
    with qtbot.waitSignal(w.page_changed, timeout=1000) as blocker:
        w.set_document(Document.open(sample_pdf))
    assert blocker.args == [0, 5]
    assert w.has_document()
    assert w.current_page == 0
    assert w.page_count == 5


def test_next_and_prev_within_bounds(qtbot, sample_pdf):
    w = ViewerWidget()
    qtbot.addWidget(w)
    w.set_document(Document.open(sample_pdf))

    w.next_page()
    assert w.current_page == 1
    w.next_page()
    assert w.current_page == 2
    w.prev_page()
    assert w.current_page == 1


def test_navigation_clamps_at_boundaries(qtbot, sample_pdf):
    w = ViewerWidget()
    qtbot.addWidget(w)
    w.set_document(Document.open(sample_pdf))

    w.prev_page()  # already at 0
    assert w.current_page == 0

    w.last_page()
    assert w.current_page == 4

    w.next_page()  # already at last
    assert w.current_page == 4


def test_goto_page_clamps_out_of_range(qtbot, sample_pdf):
    w = ViewerWidget()
    qtbot.addWidget(w)
    w.set_document(Document.open(sample_pdf))

    w.goto_page(100)
    assert w.current_page == 4

    w.goto_page(-5)
    assert w.current_page == 0


def test_no_op_navigation_does_not_emit(qtbot, sample_pdf):
    w = ViewerWidget()
    qtbot.addWidget(w)
    w.set_document(Document.open(sample_pdf))

    # We are already at page 0; prev_page should be a no-op (no signal).
    with qtbot.assertNotEmitted(w.page_changed):
        w.prev_page()
