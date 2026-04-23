"""Tests for opiter.ui.viewer_widget (page navigation behavior)."""
from __future__ import annotations

from pathlib import Path

import fitz
import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent

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


def _wheel(delta_y: int) -> QWheelEvent:
    """Build a synthetic vertical-scroll wheel event."""
    return QWheelEvent(
        QPointF(10, 10),
        QPointF(10, 10),
        QPoint(0, 0),
        QPoint(0, delta_y),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )


def _scrollable_viewer(qtbot, pdf: Path) -> ViewerWidget:
    """Build a viewer forcibly smaller than the page so scrollbars exist."""
    w = ViewerWidget()
    qtbot.addWidget(w)
    w.resize(200, 400)
    w.show()
    qtbot.waitExposed(w)
    w.set_document(Document.open(pdf))
    return w


# ---------------------------------------------------------------- initial state
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


# ---------------------------------------------------------------- programmatic
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

    w.prev_page()
    assert w.current_page == 0

    w.last_page()
    assert w.current_page == 4

    w.next_page()
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

    with qtbot.assertNotEmitted(w.page_changed):
        w.prev_page()


# ------------------------------------------------------------------ wheel edge
def test_wheel_down_at_bottom_advances_page(qtbot, sample_pdf):
    w = _scrollable_viewer(qtbot, sample_pdf)
    sb = w.verticalScrollBar()
    sb.setValue(sb.maximum())

    w.wheelEvent(_wheel(-120))
    assert w.current_page == 1


def test_wheel_up_at_top_retreats_page_and_lands_at_bottom(qtbot, sample_pdf):
    w = _scrollable_viewer(qtbot, sample_pdf)
    w.next_page()
    sb = w.verticalScrollBar()
    sb.setValue(sb.minimum())

    w.wheelEvent(_wheel(120))
    assert w.current_page == 0
    sb = w.verticalScrollBar()
    assert sb.value() == sb.maximum()


def test_wheel_in_middle_does_not_change_page(qtbot, sample_pdf):
    w = _scrollable_viewer(qtbot, sample_pdf)
    sb = w.verticalScrollBar()
    sb.setValue((sb.minimum() + sb.maximum()) // 2)

    before = w.current_page
    w.wheelEvent(_wheel(-120))
    assert w.current_page == before


def test_wheel_down_at_last_page_bottom_does_not_advance(qtbot, sample_pdf):
    w = _scrollable_viewer(qtbot, sample_pdf)
    w.last_page()
    sb = w.verticalScrollBar()
    sb.setValue(sb.maximum())

    w.wheelEvent(_wheel(-120))
    assert w.current_page == 4


def test_wheel_up_at_first_page_top_does_not_retreat(qtbot, sample_pdf):
    w = _scrollable_viewer(qtbot, sample_pdf)
    sb = w.verticalScrollBar()
    sb.setValue(sb.minimum())

    w.wheelEvent(_wheel(120))
    assert w.current_page == 0
