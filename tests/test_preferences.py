"""Tests for opiter.core.preferences and XDG path helpers."""
from __future__ import annotations

from pathlib import Path

import pytest

from opiter.core import preferences as prefs_mod
from opiter.core.preferences import (
    Preferences,
    load,
    prune_missing_recent_files,
    push_recent_file,
    save,
)


@pytest.fixture(autouse=True)
def redirect_xdg(monkeypatch, tmp_path: Path):
    """Point XDG dirs at tmp_path so tests never touch the real user config."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))


def test_load_returns_defaults_when_no_file():
    p = load()
    assert isinstance(p, Preferences)
    assert p.window_width == 1024
    assert p.window_height == 768
    assert p.dark_mode is False
    assert p.recent_files == []


def test_save_then_load_round_trip():
    p = Preferences(
        window_width=1600,
        window_height=900,
        window_x=10,
        window_y=20,
        dark_mode=True,
        dock_area="right",
        recent_files=["/tmp/a.pdf", "/tmp/b.pdf"],
    )
    save(p)
    loaded = load()
    assert loaded.window_width == 1600
    assert loaded.window_height == 900
    assert loaded.window_x == 10
    assert loaded.window_y == 20
    assert loaded.dark_mode is True
    assert loaded.dock_area == "right"
    assert loaded.recent_files == ["/tmp/a.pdf", "/tmp/b.pdf"]


def test_load_ignores_unknown_fields():
    from opiter.utils.paths import preferences_path
    import json

    preferences_path().write_text(json.dumps({
        "window_width": 1280,
        "future_unknown_key": "whatever",
    }))
    loaded = load()
    assert loaded.window_width == 1280
    # future_unknown_key silently dropped


def test_load_returns_defaults_on_malformed_json():
    from opiter.utils.paths import preferences_path

    preferences_path().write_text("{not json")
    loaded = load()
    assert loaded.window_width == 1024  # default


def test_push_recent_file_dedupes_and_promotes():
    p = Preferences()
    push_recent_file(p, "/tmp/a.pdf")
    push_recent_file(p, "/tmp/b.pdf")
    push_recent_file(p, "/tmp/a.pdf")  # re-push a
    # a should now be first, b second, no duplicates
    assert p.recent_files[0].endswith("a.pdf")
    assert p.recent_files[1].endswith("b.pdf")
    assert len(p.recent_files) == 2


def test_push_recent_file_caps_at_max(tmp_path):
    p = Preferences()
    for i in range(15):
        (tmp_path / f"f{i}.pdf").write_text("")
        push_recent_file(p, tmp_path / f"f{i}.pdf")
    assert len(p.recent_files) == 10


def test_prune_missing_recent_files(tmp_path):
    real = tmp_path / "real.pdf"
    real.write_text("")
    p = Preferences(recent_files=[str(real), "/does/not/exist.pdf"])
    prune_missing_recent_files(p)
    assert len(p.recent_files) == 1
    assert p.recent_files[0] == str(real)


def test_save_is_atomic_via_temp_file(tmp_path):
    """On successful save there must be no lingering .tmp sibling."""
    p = Preferences()
    save(p)
    from opiter.utils.paths import preferences_path
    path = preferences_path()
    tmp = path.with_suffix(path.suffix + ".tmp")
    assert not tmp.exists()
    assert path.exists()
