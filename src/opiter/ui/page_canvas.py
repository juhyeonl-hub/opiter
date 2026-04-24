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

    # ------------------------------------------------------------ public API
    def set_tool(self, tool: ToolMode) -> None:
        self._tool = tool
        # Reset cursor for visual feedback
        if tool == ToolMode.NONE:
            self.unsetCursor()
        elif tool == ToolMode.NOTE:
            self.setCursor(Qt.CursorShape.WhatsThisCursor)
        elif tool == ToolMode.PEN:
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setCursor(Qt.CursorShape.CrossCursor)
        self._reset_drag()
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
        if self._zoom <= 0:
            return (0.0, 0.0)
        return (p.x() / self._zoom, p.y() / self._zoom)

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

        if self._tool == ToolMode.NOTE:
            self.canvas_clicked.emit(self._tool.value, self.pixel_to_pdf(pos))
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
        pos = event.position().toPoint()
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

        if tool == ToolMode.PEN and len(self._pen_points) >= 2:
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
        if not self._drag_active or self._base_pixmap is None:
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
