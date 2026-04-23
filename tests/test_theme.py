"""Tests for opiter.ui.theme."""
from __future__ import annotations

from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication

from opiter.ui.theme import apply_dark, apply_light


def test_apply_dark_sets_dark_window_role(qapp: QApplication):
    apply_dark(qapp)
    color = qapp.palette().color(QPalette.ColorRole.Window)
    # Window background should be dark (low luminance).
    assert color.lightness() < 80


def test_apply_dark_sets_light_window_text(qapp: QApplication):
    apply_dark(qapp)
    color = qapp.palette().color(QPalette.ColorRole.WindowText)
    assert color.lightness() > 200


def test_apply_dark_installs_qss(qapp: QApplication):
    apply_dark(qapp)
    assert "QToolTip" in qapp.styleSheet()


def test_apply_light_clears_qss(qapp: QApplication):
    apply_dark(qapp)
    assert qapp.styleSheet() != ""
    apply_light(qapp)
    assert qapp.styleSheet() == ""


def test_dark_then_light_round_trip_does_not_crash(qapp: QApplication):
    apply_dark(qapp)
    apply_light(qapp)
    apply_dark(qapp)
    apply_light(qapp)
    # Just ensure we end in a known state.
    assert qapp.styleSheet() == ""
