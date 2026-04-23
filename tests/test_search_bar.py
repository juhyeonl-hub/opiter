"""Tests for opiter.ui.search_bar."""
from __future__ import annotations

from PySide6.QtCore import Qt

from opiter.ui.search_bar import SearchBar


def test_initial_query_is_empty(qtbot):
    bar = SearchBar()
    qtbot.addWidget(bar)
    assert bar.query() == ""


def test_typing_emits_query_changed(qtbot):
    bar = SearchBar()
    qtbot.addWidget(bar)
    with qtbot.waitSignal(bar.query_changed, timeout=1000) as blocker:
        bar._input.setText("foo")
    assert blocker.args == ["foo"]


def test_pressing_enter_emits_next(qtbot):
    bar = SearchBar()
    qtbot.addWidget(bar)
    bar._input.setText("foo")
    bar.show()
    qtbot.waitExposed(bar)
    with qtbot.waitSignal(bar.next_requested, timeout=1000):
        qtbot.keyClick(bar._input, Qt.Key.Key_Return)


def test_set_status_with_results_renders_counter(qtbot):
    bar = SearchBar()
    qtbot.addWidget(bar)
    bar.set_status(2, 10)
    assert "3 of 10" in bar._counter.text()


def test_set_status_zero_results_with_query_shows_not_found(qtbot):
    bar = SearchBar()
    qtbot.addWidget(bar)
    bar._input.setText("anything")
    bar.set_status(-1, 0)
    assert "Not found" in bar._counter.text()


def test_set_status_zero_results_no_query_is_blank(qtbot):
    bar = SearchBar()
    qtbot.addWidget(bar)
    bar.set_status(-1, 0)
    assert bar._counter.text() == ""


def test_esc_shortcut_is_wired_to_close_requested(qtbot):
    """Verify the QShortcut → close_requested wiring exists.

    In real Qt this fires from Esc key in SearchBar or its QLineEdit child.
    Offscreen Qt cannot reliably simulate focus, so we test the activation
    signal directly. Real-world Esc behavior is covered by manual GUI testing.
    """
    bar = SearchBar()
    qtbot.addWidget(bar)
    with qtbot.waitSignal(bar.close_requested, timeout=1000):
        bar._esc_shortcut.activated.emit()


def test_esc_shortcut_uses_widget_with_children_context(qtbot):
    """The shortcut context must include children — the bug being fixed was
    Esc not working when the QLineEdit child held focus."""
    bar = SearchBar()
    qtbot.addWidget(bar)
    assert bar._esc_shortcut.context() == Qt.ShortcutContext.WidgetWithChildrenShortcut
