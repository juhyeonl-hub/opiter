# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 juhyeonl
"""Custom QTabBar that prevents tabs from drifting off the bar's edge
during a drag-reorder.

Qt does not clip the dragged tab's position to the bar's width — drag
past the left or right edge and the tab visually disappears until
drop. We override ``mouseMoveEvent`` and clamp the x coordinate so
the tab stays on screen throughout.

(An earlier version also wrapped the bar's QStyle with a proxy that
zeroed out animation durations to avoid a tab-body / close-button
animation desync during reorder. That hard-pinned the bar to the
style installed at construction time, which broke later light-mode
QSS that depends on the global style being Fusion. Dropping the
proxy is the lesser evil — the desync is a mild visual quirk;
unreadable tab labels are not.)
"""
from __future__ import annotations

from PySide6.QtCore import QPointF
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QTabBar


class SmoothTabBar(QTabBar):
    """Drop-in QTabBar with drag clamped inside the bar's own width."""

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
