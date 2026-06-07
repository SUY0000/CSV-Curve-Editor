from __future__ import annotations

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtWidgets import QVBoxLayout, QWidget
import pyqtgraph as pg

from .csv_io import sample_project
from .interpolation import interpolate_keyframes
from .models import CurveParameter, Keyframe, ProjectSettings


class KeyframePlotWidget(pg.PlotWidget):
    keyframe_added = Signal(int, float)
    keyframe_selected = Signal(int)
    keyframe_moved = Signal(int, int, float)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.frame_count = 1
        self.keyframes: list[Keyframe] = []
        self.read_only = False
        self.drag_index: int | None = None
        self.plotItem.showGrid(x=True, y=True, alpha=0.25)
        self.setLabel("bottom", "Frame")
        self.setLabel("left", "Value")

    def set_keyframes(self, keyframes: list[Keyframe], frame_count: int, read_only: bool) -> None:
        self.keyframes = keyframes
        self.frame_count = max(1, frame_count)
        self.read_only = read_only

    def mousePressEvent(self, event) -> None:
        if self.read_only or event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        index = self._nearest_keyframe_index(event.position())
        if index is None:
            super().mousePressEvent(event)
            return
        self.drag_index = index
        self.keyframe_selected.emit(index)
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self.drag_index is None:
            super().mouseMoveEvent(event)
            return
        point = self._event_to_view(event.position())
        frame = min(max(0, int(round(point.x()))), self.frame_count - 1)
        self.keyframe_moved.emit(self.drag_index, frame, float(point.y()))
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if self.drag_index is not None:
            self.drag_index = None
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if self.read_only or event.button() != Qt.MouseButton.LeftButton:
            super().mouseDoubleClickEvent(event)
            return
        point = self._event_to_view(event.position())
        frame = min(max(0, int(round(point.x()))), self.frame_count - 1)
        self.keyframe_added.emit(frame, float(point.y()))
        event.accept()

    def _event_to_view(self, position: QPointF) -> QPointF:
        scene_pos = self.mapToScene(position.toPoint())
        return self.plotItem.vb.mapSceneToView(scene_pos)

    def _nearest_keyframe_index(self, position: QPointF) -> int | None:
        if not self.keyframes:
            return None
        scene_pos = self.mapToScene(position.toPoint())
        best_index: int | None = None
        best_distance = 12.0
        for index, keyframe in enumerate(self.keyframes):
            point = self.plotItem.vb.mapViewToScene(QPointF(keyframe.frame, keyframe.value))
            distance = ((point.x() - scene_pos.x()) ** 2 + (point.y() - scene_pos.y()) ** 2) ** 0.5
            if distance <= best_distance:
                best_distance = distance
                best_index = index
        return best_index


class CurveEditor(QWidget):
    curve_changed = Signal()
    keyframe_selected = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.project: ProjectSettings | None = None
        self.parameter: CurveParameter | None = None
        self.selected_index = -1

        self.plot = KeyframePlotWidget()
        self.curve_item = self.plot.plot(pen=pg.mkPen("#33aaff", width=2))
        self.points_item = pg.ScatterPlotItem(size=11, brush=pg.mkBrush("#ffaa33"), pen=pg.mkPen("#222222", width=1))
        self.plot.addItem(self.points_item)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plot)

        self.plot.keyframe_added.connect(self._add_keyframe)
        self.plot.keyframe_selected.connect(self._select_keyframe)
        self.plot.keyframe_moved.connect(self._move_keyframe)

    def set_curve(self, project: ProjectSettings, parameter: CurveParameter | None) -> None:
        self.project = project
        self.parameter = parameter
        self.selected_index = -1
        self.refresh()

    def refresh(self) -> None:
        self.curve_item.clear()
        self.points_item.clear()
        if not self.project or not self.parameter:
            self.plot.set_keyframes([], 1, True)
            return

        frame_count = self.project.frame_count
        read_only = self.project.is_derived(self.parameter.name)
        self.parameter.ensure_endpoints(frame_count)
        if read_only:
            values = sample_project(self.project).get(self.parameter.name, [0.0] * frame_count)
        else:
            values = interpolate_keyframes(self.parameter.keyframes, frame_count)
        x_values = list(range(frame_count))
        self.curve_item.setData(x_values, values)
        self.points_item.setData(
            [keyframe.frame for keyframe in self.parameter.keyframes],
            [keyframe.value for keyframe in self.parameter.keyframes],
        )
        self.plot.set_keyframes(self.parameter.keyframes, frame_count, read_only)
        self.plot.setTitle(f"{self.parameter.name} ({'自动派生，只读' if read_only else '可编辑'})")

    def select_keyframe(self, index: int) -> None:
        self._select_keyframe(index)

    def _add_keyframe(self, frame: int, value: float) -> None:
        if not self.project or not self.parameter:
            return
        self.parameter.add_keyframe(frame, value)
        self.selected_index = next(
            index for index, keyframe in enumerate(self.parameter.keyframes) if keyframe.frame == frame
        )
        self.refresh()
        self.keyframe_selected.emit(self.selected_index)
        self.curve_changed.emit()

    def _select_keyframe(self, index: int) -> None:
        self.selected_index = index
        self.keyframe_selected.emit(index)

    def _move_keyframe(self, index: int, frame: int, value: float) -> None:
        if not self.project or not self.parameter or not (0 <= index < len(self.parameter.keyframes)):
            return
        smooth = self.parameter.keyframes[index].smooth
        self.parameter.keyframes[index] = Keyframe(frame, value, smooth)
        self.parameter.ensure_endpoints(self.project.frame_count)
        self.selected_index = next(
            (
                item_index
                for item_index, keyframe in enumerate(self.parameter.keyframes)
                if keyframe.frame == frame and keyframe.smooth == smooth
            ),
            min(index, len(self.parameter.keyframes) - 1),
        )
        self.refresh()
        self.keyframe_selected.emit(self.selected_index)
        self.curve_changed.emit()
