from __future__ import annotations

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtWidgets import QVBoxLayout, QWidget
import pyqtgraph as pg

from .csv_io import sample_project
from .interpolation import interpolate_keyframes
from .models import CurveParameter, Keyframe, ProjectSettings

COLORS = ["#33aaff", "#ff9933", "#66cc66", "#cc66ff", "#ff5577", "#dddd55"]


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
        self.value_from_display = lambda value: float(value)
        self.plotItem.showGrid(x=True, y=True, alpha=0.25)
        self.setLabel("bottom", "Frame")
        self.setLabel("left", "Value")

    def set_keyframes(
        self,
        keyframes: list[Keyframe],
        frame_count: int,
        read_only: bool,
        value_from_display,
    ) -> None:
        self.keyframes = keyframes
        self.frame_count = max(1, frame_count)
        self.read_only = read_only
        self.value_from_display = value_from_display

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
        self.keyframe_moved.emit(self.drag_index, frame, self.value_from_display(point.y()))
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
        self.keyframe_added.emit(frame, self.value_from_display(point.y()))
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
    curve_changed = Signal(str)
    keyframe_selected = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.project: ProjectSettings | None = None
        self.parameter: CurveParameter | None = None
        self.overlay_parameters: list[CurveParameter] = []
        self.selected_index = -1
        self.multi_overlay = False
        self.active_range = (0.0, 1.0)

        self.plot = KeyframePlotWidget()
        self.plot.addLegend()
        self.points_item = pg.ScatterPlotItem(size=11, brush=pg.mkBrush("#ffaa33"), pen=pg.mkPen("#222222", width=1))
        self.plot_items: list[pg.PlotDataItem] = []
        self.plot.addItem(self.points_item)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plot)

        self.plot.keyframe_added.connect(self._add_keyframe)
        self.plot.keyframe_selected.connect(self._select_keyframe)
        self.plot.keyframe_moved.connect(self._move_keyframe)

    def set_curve(
        self,
        project: ProjectSettings,
        parameter: CurveParameter | None,
        overlay_parameters: list[CurveParameter] | None = None,
    ) -> None:
        self.project = project
        self.parameter = parameter
        self.overlay_parameters = overlay_parameters or ([parameter] if parameter else [])
        self.selected_index = -1
        self.refresh()

    def refresh(self) -> None:
        for item in self.plot_items:
            self.plot.removeItem(item)
        self.plot_items = []
        self.points_item.clear()
        if not self.project or not self.parameter:
            self.plot.set_keyframes([], 1, True, lambda value: value)
            return

        frame_count = self.project.frame_count
        active = self.parameter
        read_only = self.project.is_derived(active.name)
        sampled = sample_project(self.project)
        overlays = self._unique_overlays()
        self.multi_overlay = len(overlays) > 1
        self.active_range = self._display_range(active, sampled.get(active.name, []))
        x_values = list(range(frame_count))

        for index, parameter in enumerate(overlays):
            values = sampled.get(parameter.name, [0.0] * frame_count)
            display_values = self._values_to_display(parameter, values)
            label = self._label_for(parameter, values)
            item = self.plot.plot(
                x_values,
                display_values,
                pen=pg.mkPen(COLORS[index % len(COLORS)], width=2 if parameter is active else 1),
                name=label,
            )
            self.plot_items.append(item)

        active.ensure_endpoints(frame_count)
        self.points_item.setData(
            [keyframe.frame for keyframe in active.keyframes],
            [self._value_to_display(active, keyframe.value) for keyframe in active.keyframes],
        )
        self.plot.set_keyframes(
            [Keyframe(keyframe.frame, self._value_to_display(active, keyframe.value), keyframe.smooth) for keyframe in active.keyframes],
            frame_count,
            read_only,
            lambda value: active.apply_precision(self._display_to_value(active, value)),
        )
        self.plot.setLabel("left", "Normalized" if self.multi_overlay else f"Value ({active.unit})")
        self.plot.setTitle(f"{active.name} ({'自动派生，只读' if read_only else '可编辑'})")

    def select_keyframe(self, index: int) -> None:
        self._select_keyframe(index)

    def _unique_overlays(self) -> list[CurveParameter]:
        overlays = []
        for parameter in [self.parameter, *self.overlay_parameters]:
            if parameter and parameter not in overlays:
                overlays.append(parameter)
        return overlays

    def _add_keyframe(self, frame: int, value: float) -> None:
        if not self.project or not self.parameter:
            return
        self.parameter.add_keyframe(frame, self.parameter.apply_precision(value))
        self.selected_index = next(
            index for index, keyframe in enumerate(self.parameter.keyframes) if keyframe.frame == frame
        )
        self.refresh()
        self.keyframe_selected.emit(self.selected_index)
        self.curve_changed.emit(self.parameter.name)

    def _select_keyframe(self, index: int) -> None:
        self.selected_index = index
        self.keyframe_selected.emit(index)

    def _move_keyframe(self, index: int, frame: int, value: float) -> None:
        if not self.project or not self.parameter or not (0 <= index < len(self.parameter.keyframes)):
            return
        smooth = self.parameter.keyframes[index].smooth
        value = self.parameter.apply_precision(value)
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
        self.curve_changed.emit(self.parameter.name)

    def _values_to_display(self, parameter: CurveParameter, values: list[float]) -> list[float]:
        if not self.multi_overlay:
            return values
        low, high = self._display_range(parameter, values)
        span = high - low
        return [(value - low) / span for value in values]

    def _value_to_display(self, parameter: CurveParameter, value: float) -> float:
        if not self.multi_overlay:
            return value
        low, high = self._display_range(parameter, sample_project(self.project or ProjectSettings.create_default()).get(parameter.name, []))
        return (value - low) / (high - low)

    def _display_to_value(self, parameter: CurveParameter, value: float) -> float:
        if not self.multi_overlay:
            return value
        low, high = self._display_range(parameter, sample_project(self.project or ProjectSettings.create_default()).get(parameter.name, []))
        return low + value * (high - low)

    def _display_range(self, parameter: CurveParameter, values: list[float]) -> tuple[float, float]:
        if not parameter.display_auto_range and parameter.display_min is not None and parameter.display_max is not None:
            low, high = parameter.display_min, parameter.display_max
        elif values:
            low, high = min(values), max(values)
        else:
            low, high = 0.0, 1.0
        if low == high:
            pad = 1.0 if low == 0 else abs(low) * 0.1
            low -= pad
            high += pad
        return float(low), float(high)

    def _label_for(self, parameter: CurveParameter, values: list[float]) -> str:
        if not self.multi_overlay:
            return parameter.name
        low, high = self._display_range(parameter, values)
        return f"{parameter.name} [{low:.3g}–{high:.3g}]"
