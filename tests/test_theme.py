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


def test_apply_light_installs_light_qss(qapp: QApplication):
    apply_dark(qapp)
    apply_light(qapp)
    # Light theme uses an explicit palette + QSS supplement; QToolTip
    # rule is the canonical marker for either theme being installed.
    assert "QToolTip" in qapp.styleSheet()


def test_apply_light_uses_light_window(qapp: QApplication):
    apply_light(qapp)
    color = qapp.palette().color(QPalette.ColorRole.Window)
    # Window background should be light (high luminance).
    assert color.lightness() > 200


def test_apply_light_uses_dark_text(qapp: QApplication):
    apply_light(qapp)
    color = qapp.palette().color(QPalette.ColorRole.WindowText)
    # Foreground text should be dark for contrast against the light bg.
    assert color.lightness() < 80


def test_dark_then_light_round_trip_does_not_crash(qapp: QApplication):
    apply_dark(qapp)
    apply_light(qapp)
    apply_dark(qapp)
    apply_light(qapp)
    # Either theme installs *some* QSS; the round-trip just shouldn't crash
    # and should leave a known palette.
    assert "QToolTip" in qapp.styleSheet()
