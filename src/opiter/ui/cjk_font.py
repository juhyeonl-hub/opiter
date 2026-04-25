# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 juhyeonl
"""Register a CJK-capable font for QTextEdit-based viewers.

Korean (and CJK in general) glyphs render as tofu boxes when the system
has no CJK font — common on WSL2 and minimal Linux installs. We probe
a set of well-known font paths, register the first one that exists via
``QFontDatabase.addApplicationFont``, and expose a preferred family
name for QTextEdit consumers.

Returns an empty family when no CJK font could be found; callers should
still set the family chain so Qt falls back gracefully.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QFontDatabase

# Order matters: most-preferred first. Each entry is a candidate file path.
_CANDIDATE_PATHS: tuple[str, ...] = (
    # WSL2: Windows-native Korean fonts accessible from /mnt/c
    "/mnt/c/Windows/Fonts/malgun.ttf",
    "/mnt/c/Windows/Fonts/malgunbd.ttf",
    "/mnt/c/Windows/Fonts/gulim.ttc",
    "/mnt/c/Windows/Fonts/batang.ttc",
    # Common Linux distribution packages
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/nanum/NanumGothic.ttf",
    # macOS
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
)

_loaded_family: str | None = None
_probed = False


def ensure_cjk_font_loaded() -> str:
    """Register a CJK font if available and return a usable family name.

    Idempotent — the first successful load is cached for the life of
    the process. Returns ``""`` if no candidate was found.
    """
    global _loaded_family, _probed
    if _probed:
        return _loaded_family or ""
    _probed = True

    for path in _CANDIDATE_PATHS:
        if not Path(path).exists():
            continue
        font_id = QFontDatabase.addApplicationFont(path)
        if font_id == -1:
            continue
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families:
            _loaded_family = families[0]
            return _loaded_family
    return ""


def cjk_family_chain() -> list[str]:
    """Return a font-family preference chain suitable for setFamilies()."""
    chain = []
    loaded = ensure_cjk_font_loaded()
    if loaded:
        chain.append(loaded)
    # Hinted system names as additional fallbacks for environments
    # where fontconfig knows them even if we didn't load them manually.
    chain.extend([
        "Malgun Gothic",
        "Noto Sans CJK KR",
        "Noto Sans KR",
        "NanumGothic",
        "Gulim",
        "sans-serif",
    ])
    return chain
