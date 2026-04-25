# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 juhyeonl
"""Custom QLabel that hosts the rendered PDF page plus an interactive overlay.

Responsibilities split with :class:`opiter.ui.viewer_widget.ViewerWidget`:
  * ViewerWidget owns the document, zoom, page index, and high-level navigation.
  * PageCanvas owns the rendered pixmap and the in-progress annotation
    preview (rect / line / freehand stroke). Mouse events are dispatched
    here based on the active tool mode, and a final tool-specific signal
    is emitted on release for the parent to apply to the document.

Coordinates: mouse positions in this widget are in label pixels at the
current zoom. Helpers convert to PDF points with :py:meth:`pixel_to_pdf`.
"""
from __future__ import annotations

from enum import Enum, auto

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QLabel, QWidget


class ToolMode(Enum):
    NONE = auto()
    POINTER = auto()       # select / move / delete existing annotations
    HIGHLIGHT = auto()
    UNDERLINE = auto()
    STRIKEOUT = auto()
    NOTE = auto()
    PEN = auto()
    RECT = auto()
    ELLIPSE = auto()
    ARROW = auto()
    TEXTBOX = auto()


# --- Signal payload helpers --------------------------------------------------
# All payloads are PDF coordinates (points). The parent uses them directly
# with annotations.* helpers without re-converting.

class PageCanvas(QLabel):
    """Page display + interactive annotation overlay."""

    # Drag selection (text marking) — emitted on release with the PDF rect.
    text_drag_finished = Signal(int, tuple)  # tool_mode value, (x0,y0,x1,y1) in pts

    # Single click — for sticky notes.
    canvas_clicked = Signal(int, tuple)  # tool_mode value, (x, y) in pts

    # Pen — emitted on release with the full stroke as a list of (x,y) pts.
    stroke_finished = Signal(list)  # [(x,y), ...]

    # Shapes / textbox — emitted on release with the bounding rect.
    rect_drag_finished = Signal(int, tuple)  # tool_mode value, (x0,y0,x1,y1)

    # Arrow — start + end points
    arrow_drag_finished = Signal(tuple, tuple)  # start, end (each (x,y))

    # POINTER tool — pure selection click and (after-selection) drag-to-move.
    pointer_clicked = Signal(tuple)               # (x, y) PDF pts
    pointer_drag_finished = Signal(tuple, tuple)  # (start_pdf, end_pdf)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText("(No document loaded — File → Open to begin)")
        self.setMouseTracking(True)

        self._tool: ToolMode = ToolMode.NONE
        self._zoom: float = 1.0
        self._base_pixmap: QPixmap | None = None

        # Drag state
        self._drag_start_label: QPoint | None = None
        self._drag_current_label: QPoint | None = None
        self._drag_active: bool = False

        # Pen state — list of label-coord points
        self._pen_points: list[QPoint] = []

        # POINTER tool — selection rect to draw (in PDF/rotated coords;
        # converted to label coords at paint time).
        self._selection_rect_pdf: tuple[float, float, float, float] | None = None

    # ------------------------------------------------------------ public API
    def set_tool(self, tool: ToolMode) -> None:
        self._tool = tool
        # Reset cursor for visual feedback
        if tool == ToolMode.NONE:
            self.unsetCursor()
        elif tool == ToolMode.POINTER:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        elif tool == ToolMode.NOTE:
            self.setCursor(Qt.CursorShape.WhatsThisCursor)
        elif tool == ToolMode.PEN:
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setCursor(Qt.CursorShape.CrossCursor)
        # Leaving POINTER clears the visible selection.
        if tool != ToolMode.POINTER:
            self._selection_rect_pdf = None
        self._reset_drag()
        self.update()

    def set_selection_rect(
        self, rect_pdf: tuple[float, float, float, float] | None
    ) -> None:
        """Show or clear the dashed selection box (rotated/visible coords)."""
        self._selection_rect_pdf = rect_pdf
        self.update()

    def current_tool(self) -> ToolMode:
        return self._tool

    def set_page_pixmap(self, pixmap: QPixmap, zoom: float) -> None:
        """Install the rendered page and the zoom factor used to render it."""
        self._base_pixmap = pixmap
        self._zoom = zoom
        self.setPixmap(pixmap)
        self.adjustSize()

    def clear_page(self) -> None:
        self._base_pixmap = None
        self._zoom = 1.0
        self.clear()
        self.setText("(No document loaded — File → Open to begin)")

    def pixel_to_pdf(self, p: QPoint) -> tuple[float, float]:
        """Translate a label-local pixel point to PDF point coordinates.

        The pixmap is rendered at the natural ``page_width × zoom`` size but
        the QLabel itself is grown by the parent QScrollArea's
        ``widgetResizable=True`` to fill the viewport. With AlignCenter the
        pixmap sits centered inside the larger label — so we must subtract
        the centering offset before dividing by zoom, or every annotation
        ends up shifted right/down.
        """
        if self._zoom <= 0:
            return (0.0, 0.0)
        ox, oy = self._pixmap_offset()
        return ((p.x() - ox) / self._zoom, (p.y() - oy) / self._zoom)

    def _pixmap_offset(self) -> tuple[int, int]:
        """Top-left of the pixmap inside this label, in label-local pixels."""
        if self._base_pixmap is None:
            return (0, 0)
        pm_w = self._base_pixmap.width()
        pm_h = self._base_pixmap.height()
        ox = max(0, (self.width() - pm_w) // 2)
        oy = max(0, (self.height() - pm_h) // 2)
        return (ox, oy)

    def _is_inside_pixmap(self, p: QPoint) -> bool:
        if self._base_pixmap is None:
            return False
        ox, oy = self._pixmap_offset()
        return (
            ox <= p.x() < ox + self._base_pixmap.width()
            and oy <= p.y() < oy + self._base_pixmap.height()
        )

    def _clamp_to_pixmap(self, p: QPoint) -> QPoint:
        if self._base_pixmap is None:
            return p
        ox, oy = self._pixmap_offset()
        pm_w = self._base_pixmap.width()
        pm_h = self._base_pixmap.height()
        return QPoint(
            max(ox, min(ox + pm_w - 1, p.x())),
            max(oy, min(oy + pm_h - 1, p.y())),
        )

    # --------------------------------------------------------------- mouse
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if (
            self._tool == ToolMode.NONE
            or self._base_pixmap is None
            or event.button() != Qt.MouseButton.LeftButton
        ):
            super().mousePressEvent(event)
            return

        pos = event.position().toPoint()
        # Ignore clicks that landed in the centering margin around the
        # pixmap — they would otherwise produce annotations placed off the
        # page (negative or oversized PDF coordinates).
        if not self._is_inside_pixmap(pos):
            super().mousePressEvent(event)
            return

        if self._tool == ToolMode.NOTE:
            self.canvas_clicked.emit(self._tool.value, self.pixel_to_pdf(pos))
            event.accept()
            return

        if self._tool == ToolMode.POINTER:
            # Always emit click — the parent decides whether it hit an
            # existing annotation (and if so, may begin tracking a drag).
            self.pointer_clicked.emit(self.pixel_to_pdf(pos))
            # Begin drag tracking for potential move; if no annot is
            # selected, the release will be a no-op.
            self._drag_active = True
            self._drag_start_label = pos
            self._drag_current_label = pos
            event.accept()
            return

        # Drag-based tools — start tracking
        self._drag_active = True
        self._drag_start_label = pos
        self._drag_current_label = pos
        if self._tool == ToolMode.PEN:
            self._pen_points = [pos]
        self.update()
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self._drag_active:
            super().mouseMoveEvent(event)
            return
        # Clamp to the pixmap so drag handles still produce sane PDF coords
        # if the cursor wanders into the centering margin.
        pos = self._clamp_to_pixmap(event.position().toPoint())
        self._drag_current_label = pos
        if self._tool == ToolMode.PEN:
            self._pen_points.append(pos)
        self.update()
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if not self._drag_active or event.button() != Qt.MouseButton.LeftButton:
            super().mouseReleaseEvent(event)
            return

        tool = self._tool
        start = self._drag_start_label
        end = self._drag_current_label or start

        if tool == ToolMode.POINTER:
            if (start - end).manhattanLength() > 2:
                self.pointer_drag_finished.emit(
                    self.pixel_to_pdf(start), self.pixel_to_pdf(end)
                )
        elif tool == ToolMode.PEN and len(self._pen_points) >= 2:
            stroke = [self.pixel_to_pdf(p) for p in self._pen_points]
            self.stroke_finished.emit(stroke)
        elif tool in (ToolMode.HIGHLIGHT, ToolMode.UNDERLINE, ToolMode.STRIKEOUT):
            rect = _normalized_rect(start, end)
            if rect.width() > 1 and rect.height() > 1:
                pdf_rect = self._rect_to_pdf(rect)
                self.text_drag_finished.emit(tool.value, pdf_rect)
        elif tool in (ToolMode.RECT, ToolMode.ELLIPSE, ToolMode.TEXTBOX):
            rect = _normalized_rect(start, end)
            if rect.width() > 1 and rect.height() > 1:
                pdf_rect = self._rect_to_pdf(rect)
                self.rect_drag_finished.emit(tool.value, pdf_rect)
        elif tool == ToolMode.ARROW:
            if (start - end).manhattanLength() > 2:
                self.arrow_drag_finished.emit(
                    self.pixel_to_pdf(start), self.pixel_to_pdf(end)
                )

        self._reset_drag()
        self.update()
        event.accept()

    # --------------------------------------------------------------- paint
    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)  # draws the base pixmap
        if self._base_pixmap is None:
            return

        # Persistent overlay: selection box (POINTER tool) — drawn even
        # when not actively dragging.
        if self._selection_rect_pdf is not None:
            painter = QPainter(self)
            try:
                pen = QPen(QColor(0, 120, 215, 230), 2, Qt.PenStyle.DashLine)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                ox, oy = self._pixmap_offset()
                x0, y0, x1, y1 = self._selection_rect_pdf
                painter.drawRect(
                    QRectF(
                        ox + x0 * self._zoom,
                        oy + y0 * self._zoom,
                        (x1 - x0) * self._zoom,
                        (y1 - y0) * self._zoom,
                    )
                )
            finally:
                painter.end()

        if not self._drag_active:
            return

        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            tool = self._tool

            if tool in (ToolMode.HIGHLIGHT, ToolMode.UNDERLINE, ToolMode.STRIKEOUT):
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(255, 240, 0, 90))
                painter.drawRect(_normalized_rect(self._drag_start_label, self._drag_current_label))
            elif tool == ToolMode.RECT:
                painter.setPen(QPen(QColor(255, 0, 0, 220), 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(_normalized_rect(self._drag_start_label, self._drag_current_label))
            elif tool == ToolMode.ELLIPSE:
                painter.setPen(QPen(QColor(255, 0, 0, 220), 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(_normalized_rect(self._drag_start_label, self._drag_current_label))
            elif tool == ToolMode.ARROW:
                painter.setPen(QPen(QColor(255, 0, 0, 220), 2))
                painter.drawLine(self._drag_start_label, self._drag_current_label)
            elif tool == ToolMode.TEXTBOX:
                pen = QPen(QColor(0, 0, 0, 200), 1, Qt.PenStyle.DashLine)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(_normalized_rect(self._drag_start_label, self._drag_current_label))
            elif tool == ToolMode.PEN and len(self._pen_points) >= 2:
                painter.setPen(QPen(QColor(0, 0, 0, 220), 2))
                for i in range(1, len(self._pen_points)):
                    painter.drawLine(self._pen_points[i - 1], self._pen_points[i])
        finally:
            painter.end()

    # --------------------------------------------------------------- helpers
    def _rect_to_pdf(self, r: QRect) -> tuple[float, float, float, float]:
        x0, y0 = self.pixel_to_pdf(r.topLeft())
        x1, y1 = self.pixel_to_pdf(r.bottomRight())
        return (x0, y0, x1, y1)

    def _reset_drag(self) -> None:
        self._drag_active = False
        self._drag_start_label = None
        self._drag_current_label = None
        self._pen_points = []


def _normalized_rect(a: QPoint, b: QPoint) -> QRect:
    """Build a rect from two corners regardless of drag direction."""
    return QRect(a, b).normalized()
