"""User preferences — persisted as JSON at XDG_CONFIG_HOME/opiter/preferences.json.

Schema is additive: unknown fields in the file are ignored on load so older
versions stay forward-compatible, and missing fields fall back to defaults.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from opiter.utils.paths import preferences_path


@dataclass
class Preferences:
    # Window
    window_width: int = 1024
    window_height: int = 768
    window_x: int | None = None
    window_y: int | None = None
    window_maximized: bool = False

    # Thumbnails dock
    dock_visible: bool = True
    dock_area: str = "left"  # "left" or "right"
    thumbnail_width_px: int = 140

    # Theme
    dark_mode: bool = False

    # Recent files (MRU) — newest first, max 10
    recent_files: list[str] = field(default_factory=list)

    # Keymapping overrides (action_id → QKeySequence string). Empty = use defaults.
    keymap: dict[str, str] = field(default_factory=dict)

    # Annotation colors (each is a "r,g,b" string of 0..1 floats for JSON portability)
    color_highlight: str = "1.0,1.0,0.0"
    color_underline: str = "0.0,0.0,1.0"
    color_strikeout: str = "1.0,0.0,0.0"
    color_rect: str = "1.0,0.0,0.0"
    color_ellipse: str = "1.0,0.0,0.0"
    color_arrow: str = "1.0,0.0,0.0"
    color_pen: str = "0.0,0.0,0.0"
    color_textbox: str = "0.0,0.0,0.0"


_MAX_RECENT = 10


def parse_color(s: str) -> tuple[float, float, float]:
    """Parse a ``"r,g,b"`` string of 0..1 floats into a 3-tuple. Lenient: clamp
    each channel; default to (0,0,0) on malformed input."""
    try:
        parts = [float(p.strip()) for p in s.split(",")]
        if len(parts) != 3:
            return (0.0, 0.0, 0.0)
        return tuple(max(0.0, min(1.0, v)) for v in parts)  # type: ignore[return-value]
    except ValueError:
        return (0.0, 0.0, 0.0)


def format_color(rgb: tuple[float, float, float]) -> str:
    return f"{rgb[0]},{rgb[1]},{rgb[2]}"


def load() -> Preferences:
    """Load preferences from disk; return defaults on any error."""
    path = preferences_path()
    if not path.exists():
        return Preferences()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return Preferences()
    # Only accept known fields — ignore unknown keys silently.
    known = {f for f in Preferences.__dataclass_fields__}
    filtered = {k: v for k, v in raw.items() if k in known}
    try:
        return Preferences(**filtered)
    except TypeError:
        # Field type mismatch etc. — fall back to defaults.
        return Preferences()


def save(prefs: Preferences) -> None:
    """Write preferences atomically (temp + rename)."""
    path = preferences_path()
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(asdict(prefs), indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def push_recent_file(prefs: Preferences, file_path: str | Path) -> None:
    """Prepend *file_path* to recent_files, deduplicate, trim to MAX."""
    s = str(Path(file_path).resolve())
    if s in prefs.recent_files:
        prefs.recent_files.remove(s)
    prefs.recent_files.insert(0, s)
    del prefs.recent_files[_MAX_RECENT:]


def prune_missing_recent_files(prefs: Preferences) -> None:
    """Remove entries in recent_files that no longer exist on disk."""
    prefs.recent_files = [p for p in prefs.recent_files if Path(p).exists()]
