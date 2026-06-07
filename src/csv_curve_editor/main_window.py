from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QDoubleSpinBox,
    QSplitter,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from .csv_io import export_csv, import_csv
from .curve_editor import CurveEditor
from .models import CurveParameter, Keyframe, ProjectSettings, SUPPORTED_FPS
from .vehicle_settings import VehicleSettingsDialog


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("CSV Curve Editor")
        self.project = ProjectSettings.create_default()
        self.selected_keyframe_index = -1
        self.updating_fields = False

        self._build_toolbar()
        self._build_central_widget()
        self.setStatusBar(QStatusBar())
        self.refresh_all()

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("工具栏")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        new_button = QPushButton("新建")
        open_button = QPushButton("打开 CSV")
        export_button = QPushButton("导出 CSV")
        vehicle_button = QPushButton("车辆设置")

        self.fps_combo = QComboBox()
        for fps in SUPPORTED_FPS:
            self.fps_combo.addItem(f"{fps} fps", fps)
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(0.04, 60 * 60)
        self.duration_spin.setDecimals(2)
        self.duration_spin.setSuffix(" s")
        self.duration_spin.setValue(self.project.duration_seconds)
        self.duration_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.PlusMinus)

        self.auto_rpm_check = QCheckBox("RPM 自动绑定")
        self.auto_g_check = QCheckBox("纵向 G 自动计算")
        self.auto_rpm_check.setChecked(self.project.auto_rpm)
        self.auto_g_check.setChecked(self.project.auto_longitudinal_g)

        toolbar.addWidget(new_button)
        toolbar.addWidget(open_button)
        toolbar.addWidget(export_button)
        toolbar.addSeparator()
        toolbar.addWidget(QLabel("帧率 "))
        toolbar.addWidget(self.fps_combo)
        toolbar.addWidget(QLabel(" 时长 "))
        toolbar.addWidget(self.duration_spin)
        toolbar.addSeparator()
        toolbar.addWidget(vehicle_button)
        toolbar.addWidget(self.auto_rpm_check)
        toolbar.addWidget(self.auto_g_check)

        new_button.clicked.connect(self.new_project)
        open_button.clicked.connect(self.open_csv)
        export_button.clicked.connect(self.export_csv)
        vehicle_button.clicked.connect(self.edit_vehicle_settings)
        self.fps_combo.currentIndexChanged.connect(self.update_fps)
        self.duration_spin.valueChanged.connect(self.update_duration)
        self.auto_rpm_check.toggled.connect(self.update_auto_flags)
        self.auto_g_check.toggled.connect(self.update_auto_flags)

    def _build_central_widget(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(QLabel("参数"))
        self.parameter_list = QListWidget()
        self.add_parameter_button = QPushButton("新增自定义参数")
        left_layout.addWidget(self.parameter_list)
        left_layout.addWidget(self.add_parameter_button)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        self.curve_editor = CurveEditor()
        right_layout.addWidget(self.curve_editor, stretch=1)
        right_layout.addWidget(self._build_keyframe_group())

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 5)
        root_layout.addWidget(splitter)
        self.setCentralWidget(root)

        self.parameter_list.currentRowChanged.connect(self.select_parameter)
        self.add_parameter_button.clicked.connect(self.add_custom_parameter)
        self.curve_editor.curve_changed.connect(self.on_curve_changed)
        self.curve_editor.keyframe_selected.connect(self.load_keyframe_fields)

    def _build_keyframe_group(self) -> QGroupBox:
        group = QGroupBox("关键帧")
        layout = QHBoxLayout(group)

        self.frame_spin = QSpinBox()
        self.frame_spin.setRange(0, self.project.frame_count - 1)
        self.value_spin = QDoubleSpinBox()
        self.value_spin.setRange(-1_000_000, 1_000_000)
        self.value_spin.setDecimals(4)
        self.smooth_spin = QDoubleSpinBox()
        self.smooth_spin.setRange(0.0, 1.0)
        self.smooth_spin.setDecimals(3)
        self.smooth_spin.setSingleStep(0.05)
        self.delete_keyframe_button = QPushButton("删除关键帧")

        form = QFormLayout()
        form.addRow("Frame", self.frame_spin)
        form.addRow("Value", self.value_spin)
        form.addRow("Smooth", self.smooth_spin)
        layout.addLayout(form)
        layout.addWidget(self.delete_keyframe_button)
        layout.addStretch(1)

        self.frame_spin.valueChanged.connect(self.update_selected_keyframe)
        self.value_spin.valueChanged.connect(self.update_selected_keyframe)
        self.smooth_spin.valueChanged.connect(self.update_selected_keyframe)
        self.delete_keyframe_button.clicked.connect(self.delete_selected_keyframe)
        return group

    def refresh_all(self) -> None:
        self.project.ensure_parameter_endpoints()
        self.updating_fields = True
        self.fps_combo.setCurrentIndex(self.fps_combo.findData(self.project.fps))
        self.duration_spin.setValue(self.project.duration_seconds)
        self.auto_rpm_check.setChecked(self.project.auto_rpm)
        self.auto_g_check.setChecked(self.project.auto_longitudinal_g)
        self.frame_spin.setRange(0, self.project.frame_count - 1)
        self.updating_fields = False
        self.refresh_parameter_list()
        self.select_parameter(self.parameter_list.currentRow())
        self.update_status()

    def refresh_parameter_list(self) -> None:
        current_name = self.current_parameter().name if self.current_parameter() else None
        self.parameter_list.clear()
        for parameter in self.project.parameters:
            item = QListWidgetItem(parameter.name)
            item.setToolTip(parameter.unit)
            self.parameter_list.addItem(item)
        row = 0
        if current_name:
            for index, parameter in enumerate(self.project.parameters):
                if parameter.name == current_name:
                    row = index
                    break
        self.parameter_list.setCurrentRow(row if self.project.parameters else -1)

    def select_parameter(self, row: int) -> None:
        parameter = self.project.parameters[row] if 0 <= row < len(self.project.parameters) else None
        self.selected_keyframe_index = -1
        self.curve_editor.set_curve(self.project, parameter)
        self.load_keyframe_fields(0 if parameter and parameter.keyframes else -1)

    def current_parameter(self) -> CurveParameter | None:
        row = self.parameter_list.currentRow()
        if 0 <= row < len(self.project.parameters):
            return self.project.parameters[row]
        return None

    def new_project(self) -> None:
        self.project = ProjectSettings.create_default(
            fps=self.fps_combo.currentData(),
            duration_seconds=self.duration_spin.value(),
        )
        self.refresh_all()

    def open_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "打开 CSV", "", "CSV Files (*.csv);;All Files (*)")
        if not path:
            return
        try:
            self.project = import_csv(path)
        except Exception as error:  # noqa: BLE001
            QMessageBox.critical(self, "打开失败", str(error))
            return
        self.refresh_all()
        self.statusBar().showMessage(f"已打开：{path}")

    def export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "导出 CSV", "curve.csv", "CSV Files (*.csv);;All Files (*)")
        if not path:
            return
        try:
            export_csv(self.project, path)
        except Exception as error:  # noqa: BLE001
            QMessageBox.critical(self, "导出失败", str(error))
            return
        self.statusBar().showMessage(f"已导出：{path}")

    def update_fps(self) -> None:
        if self.updating_fields:
            return
        self.project.set_fps(self.fps_combo.currentData())
        self.refresh_all()

    def update_duration(self) -> None:
        if self.updating_fields:
            return
        self.project.set_duration(self.duration_spin.value())
        self.refresh_all()

    def update_auto_flags(self) -> None:
        if self.updating_fields:
            return
        self.project.auto_rpm = self.auto_rpm_check.isChecked()
        self.project.auto_longitudinal_g = self.auto_g_check.isChecked()
        self.curve_editor.refresh()
        self.load_keyframe_fields(self.selected_keyframe_index)

    def edit_vehicle_settings(self) -> None:
        dialog = VehicleSettingsDialog(self.project.vehicle_settings, self)
        if dialog.exec():
            self.curve_editor.refresh()
            self.statusBar().showMessage("车辆传动设置已更新")

    def add_custom_parameter(self) -> None:
        name, ok = QInputDialog.getText(self, "新增参数", "参数名（CSV 列名）")
        if not ok or not name.strip():
            return
        unit, ok = QInputDialog.getText(self, "新增参数", "单位（可留空）")
        if not ok:
            return
        initial_value, ok = QInputDialog.getDouble(self, "新增参数", "初始值", 0.0, -1_000_000, 1_000_000, 4)
        if not ok:
            return
        try:
            self.project.add_parameter(name, unit, initial_value)
        except ValueError as error:
            QMessageBox.warning(self, "新增失败", str(error))
            return
        self.refresh_all()
        self.parameter_list.setCurrentRow(len(self.project.parameters) - 1)

    def load_keyframe_fields(self, index: int) -> None:
        parameter = self.current_parameter()
        read_only = bool(parameter and self.project.is_derived(parameter.name))
        enabled = bool(parameter and not read_only and 0 <= index < len(parameter.keyframes))
        self.selected_keyframe_index = index if enabled else -1

        self.updating_fields = True
        if enabled and parameter:
            keyframe = parameter.keyframes[index]
            self.frame_spin.setValue(keyframe.frame)
            self.value_spin.setValue(keyframe.value)
            self.smooth_spin.setValue(keyframe.smooth)
        self.frame_spin.setEnabled(enabled)
        self.value_spin.setEnabled(enabled)
        self.smooth_spin.setEnabled(enabled)
        self.delete_keyframe_button.setEnabled(enabled and len(parameter.keyframes) > 2 if parameter else False)
        self.updating_fields = False

    def update_selected_keyframe(self) -> None:
        if self.updating_fields:
            return
        parameter = self.current_parameter()
        index = self.selected_keyframe_index
        if not parameter or self.project.is_derived(parameter.name) or not (0 <= index < len(parameter.keyframes)):
            return
        parameter.keyframes[index] = Keyframe(
            self.frame_spin.value(),
            self.value_spin.value(),
            self.smooth_spin.value(),
        )
        parameter.ensure_endpoints(self.project.frame_count)
        self.curve_editor.refresh()
        self.update_status()

    def delete_selected_keyframe(self) -> None:
        parameter = self.current_parameter()
        if not parameter or self.project.is_derived(parameter.name):
            return
        parameter.delete_keyframe(self.selected_keyframe_index, self.project.frame_count)
        self.curve_editor.refresh()
        self.load_keyframe_fields(min(self.selected_keyframe_index, len(parameter.keyframes) - 1))
        self.update_status()

    def on_curve_changed(self) -> None:
        self.update_status()

    def update_status(self) -> None:
        self.statusBar().showMessage(
            f"{self.project.fps}fps / {self.project.duration_seconds:.2f}s / {self.project.frame_count} frames"
        )
