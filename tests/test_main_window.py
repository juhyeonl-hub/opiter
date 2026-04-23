"""Integration tests for MainWindow workflows that span multiple components."""
from __future__ import annotations

from pathlib import Path

import fitz
import pytest
from PySide6.QtCore import Qt

from opiter.core.document import Document
from opiter.ui.main_window import MainWindow


@pytest.fixture
def text_pdf(tmp_path: Path) -> Path:
    """3-page PDF where the word 'hello' appears once on each page."""
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page()
        page.insert_text((50, 100), f"hello world page {i + 1}", fontsize=14)
    out = tmp_path / "text.pdf"
    doc.save(out)
    doc.close()
    return out


def _open_doc_into(window: MainWindow, pdf_path: Path) -> None:
    doc = Document.open(pdf_path)
    window._thumb_panel.set_document(doc)
    window._viewer.set_document(doc)
    window._reset_search_state()


def test_find_actions_use_application_shortcut_context(qtbot, text_pdf):
    """Regression: F3 / Shift+F3 must fire even when QLineEdit child is focused."""
    window = MainWindow()
    qtbot.addWidget(window)
    assert (
        window._action_find_next.shortcutContext()
        == Qt.ShortcutContext.ApplicationShortcut
    )
    assert (
        window._action_find_prev.shortcutContext()
        == Qt.ShortcutContext.ApplicationShortcut
    )
    assert (
        window._action_find.shortcutContext()
        == Qt.ShortcutContext.ApplicationShortcut
    )


def test_reopening_search_with_stale_query_re_runs_search(qtbot, text_pdf):
    """Regression: closing the search bar (X / Esc) keeps the query in the
    input. Re-opening with Ctrl+F must re-run the search so highlights and
    Prev/Next/Enter work without forcing the user to retype.
    """
    window = MainWindow()
    qtbot.addWidget(window)
    _open_doc_into(window, text_pdf)

    # First search session
    window._on_find_open()
    window._search_bar._input.setText("hello")
    assert len(window._search_results) == 3
    assert window._search_current == 0

    # Close (simulates X click or Esc)
    window._on_search_close()
    assert window._search_results == []
    assert window._search_current == -1
    # The input retains "hello" by design
    assert window._search_bar.query() == "hello"

    # Re-open: must re-run search
    window._on_find_open()
    assert len(window._search_results) == 3
    assert window._search_current == 0

    # Next/Prev now work
    window._on_search_next()
    assert window._search_current == 1
    window._on_search_prev()
    assert window._search_current == 0
