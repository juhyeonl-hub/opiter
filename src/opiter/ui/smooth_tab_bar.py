# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 juhyeonl
"""Custom QTabBar that smooths over two Qt-default visual quirks
encountered while reordering tabs by drag-and-drop.

1. **Off-edge invisibility** — dragging a tab past the bar's left or
   right edge makes the tab temporarily disappear until drop because
   Qt does not clip the dragged tab's position to the bar's width.
   We override ``mouseMoveEvent`` and clamp the x coordinate so the
   tab always stays on screen.

2. **Close-button vs. tab-body animation desync** — with
   ``setMovable(True)`` Qt animates non-dragged tabs sliding to make
   room (~250 ms), but the per-tab close button is repositioned to its
   final destination immediately at the start of the move, which makes
   the × visibly arrive a fraction of a second before the rest of the
   tab. We zero out the style's animation duration via a ``QProxyStyle``
   so both transitions happen on the same frame.
"""
from __future__ import annotations

from PySide6.QtCore import QPointF
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QProxyStyle, QStyle, QTabBar


class _NoAnimStyle(QProxyStyle):
    """Reports zero duration for animations so QTabBar tab moves apply
    instantly. Other style behavior is delegated unchanged."""

    def styleHint(  # type: ignore[override]
        self, hint, option=None, widget=None, returnData=None
    ) -> int:
        if hint == QStyle.StyleHint.SH_Widget_Animation_Duration:
            return 0
        return super().styleHint(hint, option, widget, returnData)


class SmoothTabBar(QTabBar):
    """Drop-in QTabBar with clamped drag and instant tab reorder."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setStyle(_NoAnimStyle(self.style()))

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        pos = event.position()
        max_x = float(max(0, self.width() - 1))
        clamped_x = min(max_x, max(0.0, pos.x()))
        if clamped_x != pos.x():
            event = QMouseEvent(
                event.type(),
                QPointF(clamped_x, pos.y()),
                event.button(),
                event.buttons(),
                event.modifiers(),
            )
        super().mouseMoveEvent(event)
