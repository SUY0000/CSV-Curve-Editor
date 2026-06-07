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
        self.updating_parameter_list = False

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
        self.total_frames_spin = QSpinBox()
        self.total_frames_spin.setRange(1, 1_000_000)
        self.total_frames_spin.setValue(self.project.frame_count)
        self.total_frames_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.PlusMinus)

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
        toolbar.addWidget(QLabel(" 总帧数 "))
        toolbar.addWidget(self.total_frames_spin)
        toolbar.addSeparator()
        toolbar.addWidget(vehicle_button)
        toolbar.addWidget(self.auto_rpm_check)
        toolbar.addWidget(self.auto_g_check)

        new_button.clicked.connect(self.new_project)
        open_button.clicked.connect(self.open_csv)
        export_button.clicked.connect(self.export_csv)
        vehicle_button.clicked.connect(self.edit_vehicle_settings)
        self.fps_combo.currentIndexChanged.connect(self.update_fps)
        self.total_frames_spin.valueChanged.connect(self.update_total_frames)
        self.auto_rpm_check.toggled.connect(self.update_auto_flags)
        self.auto_g_check.toggled.connect(self.update_auto_flags)

    def _build_central_widget(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        self.parameter_list_label = QLabel("参数（选中为编辑）")
        self.multi_select_check = QCheckBox("多选显示")
        self.parameter_list = QListWidget()
        self.add_parameter_button = QPushButton("新增自定义参数")
        left_layout.addWidget(self.parameter_list_label)
        left_layout.addWidget(self.multi_select_check)
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
        self.parameter_list.itemChanged.connect(self.update_overlay_selection)
        self.multi_select_check.toggled.connect(self.update_multi_select_mode)
        self.add_parameter_button.clicked.connect(self.add_custom_parameter)
        self.curve_editor.curve_changed.connect(self.on_curve_changed)
        self.curve_editor.keyframe_selected.connect(self.load_keyframe_fields)
        self.curve_editor.y_range_changed.connect(self.load_y_range_from_plot)

    def _build_keyframe_group(self) -> QGroupBox:
        group = QGroupBox("关键帧 / 显示范围")
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

        keyframe_form = QFormLayout()
        keyframe_form.addRow("Frame", self.frame_spin)
        keyframe_form.addRow("Value", self.value_spin)
        keyframe_form.addRow("Smooth", self.smooth_spin)
        layout.addLayout(keyframe_form)
        layout.addWidget(self.delete_keyframe_button)

        self.y_min_spin = QDoubleSpinBox()
        self.y_min_spin.setRange(-1_000_000, 1_000_000)
        self.y_min_spin.setDecimals(3)
        self.y_max_spin = QDoubleSpinBox()
        self.y_max_spin.setRange(-1_000_000, 1_000_000)
        self.y_max_spin.setDecimals(3)

        range_form = QFormLayout()
        range_form.addRow("Y Min", self.y_min_spin)
        range_form.addRow("Y Max", self.y_max_spin)
        layout.addLayout(range_form)
        layout.addWidget(self._build_jitter_group())
        layout.addStretch(1)

        self.frame_spin.valueChanged.connect(self.update_selected_keyframe)
        self.value_spin.valueChanged.connect(self.update_selected_keyframe)
        self.smooth_spin.valueChanged.connect(self.update_selected_keyframe)
        self.delete_keyframe_button.clicked.connect(self.delete_selected_keyframe)
        self.y_min_spin.valueChanged.connect(self.update_display_range)
        self.y_max_spin.valueChanged.connect(self.update_display_range)
        return group

    def _build_jitter_group(self) -> QGroupBox:
        group = QGroupBox("导出抖动")
        form = QFormLayout(group)

        self.jitter_enabled_check = QCheckBox("启用")
        self.jitter_amplitude_spin = QDoubleSpinBox()
        self.jitter_amplitude_spin.setRange(0.0, 1_000_000.0)
        self.jitter_amplitude_spin.setDecimals(3)
        self.jitter_amplitude_spin.setSingleStep(0.1)
        self.jitter_period_spin = QSpinBox()
        self.jitter_period_spin.setRange(1, 1000)
        self.jitter_octaves_spin = QSpinBox()
        self.jitter_octaves_spin.setRange(1, 4)
        self.jitter_seed_spin = QSpinBox()
        self.jitter_seed_spin.setRange(0, 999_999)
        self.jitter_relative_check = QCheckBox("相对幅度")
        self.jitter_affects_derived_check = QCheckBox("参与派生")

        form.addRow(self.jitter_enabled_check)
        form.addRow("幅度", self.jitter_amplitude_spin)
        form.addRow("周期(Frame)", self.jitter_period_spin)
        form.addRow("细节", self.jitter_octaves_spin)
        form.addRow("Seed", self.jitter_seed_spin)
        form.addRow(self.jitter_relative_check)
        form.addRow(self.jitter_affects_derived_check)

        self.jitter_enabled_check.toggled.connect(self.update_jitter_settings)
        self.jitter_amplitude_spin.valueChanged.connect(self.update_jitter_settings)
        self.jitter_period_spin.valueChanged.connect(self.update_jitter_settings)
        self.jitter_octaves_spin.valueChanged.connect(self.update_jitter_settings)
        self.jitter_seed_spin.valueChanged.connect(self.update_jitter_settings)
        self.jitter_relative_check.toggled.connect(self.update_jitter_settings)
        self.jitter_affects_derived_check.toggled.connect(self.update_jitter_settings)
        return group

    def refresh_all(self) -> None:
        self.project.ensure_parameter_endpoints()
        self.updating_fields = True
        self.fps_combo.setCurrentIndex(self.fps_combo.findData(self.project.fps))
        self.total_frames_spin.setValue(self.project.frame_count)
        self.auto_rpm_check.setChecked(self.project.auto_rpm)
        self.auto_g_check.setChecked(self.project.auto_longitudinal_g)
        self.frame_spin.setRange(0, self.project.frame_count - 1)
        self.updating_fields = False
        self.refresh_parameter_list()
        self.select_parameter(self.parameter_list.currentRow())
        self.update_status()

    def refresh_parameter_list(self) -> None:
        current_name = self.current_parameter().name if self.current_parameter() else None
        checked_names = self.checked_parameter_names()
        self.updating_parameter_list = True
        multi_select = self.multi_select_check.isChecked()
        self.parameter_list.clear()
        for index, parameter in enumerate(self.project.parameters):
            item = QListWidgetItem(parameter.name)
            item.setToolTip(parameter.unit)
            if multi_select:
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                checked = parameter.name in checked_names or (not checked_names and index == 0)
                item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
            else:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
            self.parameter_list.addItem(item)
        row = 0
        if current_name:
            for index, parameter in enumerate(self.project.parameters):
                if parameter.name == current_name:
                    row = index
                    break
        self.parameter_list.setCurrentRow(row if self.project.parameters else -1)
        self.updating_parameter_list = False

    def select_parameter(self, row: int) -> None:
        parameter = self.project.parameters[row] if 0 <= row < len(self.project.parameters) else None
        if parameter and self.multi_select_check.isChecked():
            item = self.parameter_list.item(row)
            if item and item.checkState() != Qt.CheckState.Checked:
                self.updating_parameter_list = True
                item.setCheckState(Qt.CheckState.Checked)
                self.updating_parameter_list = False
        self.selected_keyframe_index = -1
        self.configure_value_spin(parameter)
        self.load_display_range(parameter)
        self.load_jitter_settings(parameter)
        self.curve_editor.set_curve(self.project, parameter, self.overlay_parameters())
        self.load_keyframe_fields(0 if parameter and parameter.keyframes else -1)

    def current_parameter(self) -> CurveParameter | None:
        row = self.parameter_list.currentRow()
        if 0 <= row < len(self.project.parameters):
            return self.project.parameters[row]
        return None

    def checked_parameter_names(self) -> set[str]:
        names = set()
        if not hasattr(self, "parameter_list") or not self.multi_select_check.isChecked():
            return names
        for index in range(self.parameter_list.count()):
            item = self.parameter_list.item(index)
            if item.checkState() == Qt.CheckState.Checked:
                names.add(item.text())
        return names

    def overlay_parameters(self) -> list[CurveParameter]:
        checked = self.checked_parameter_names()
        active = self.current_parameter()
        overlays = [parameter for parameter in self.project.parameters if parameter.name in checked]
        if active and active not in overlays:
            overlays.insert(0, active)
        return overlays

    def update_overlay_selection(self) -> None:
        if self.updating_parameter_list:
            return
        self.curve_editor.set_curve(self.project, self.current_parameter(), self.overlay_parameters())

    def update_multi_select_mode(self) -> None:
        self.parameter_list_label.setText(
            "参数（勾选为叠加显示，选中为编辑）" if self.multi_select_check.isChecked() else "参数（选中为编辑）"
        )
        self.refresh_parameter_list()
        self.select_parameter(self.parameter_list.currentRow())

    def new_project(self) -> None:
        self.project = ProjectSettings.create_default(
            fps=self.fps_combo.currentData(),
            total_frames=self.total_frames_spin.value(),
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

    def update_total_frames(self) -> None:
        if self.updating_fields:
            return
        self.project.set_total_frames(self.total_frames_spin.value())
        self.refresh_all()

    def update_auto_flags(self) -> None:
        if self.updating_fields:
            return
        self.project.auto_rpm = self.auto_rpm_check.isChecked()
        self.project.auto_longitudinal_g = self.auto_g_check.isChecked()
        self.refresh_current_curve()

    def edit_vehicle_settings(self) -> None:
        dialog = VehicleSettingsDialog(self.project.vehicle_settings, self)
        if dialog.exec():
            self.refresh_current_curve()
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
        can_delete = False
        if enabled and parameter:
            frame = parameter.keyframes[index].frame
            can_delete = frame not in {0, self.project.frame_count - 1}
        self.frame_spin.setEnabled(enabled)
        self.value_spin.setEnabled(enabled)
        self.smooth_spin.setEnabled(enabled)
        self.delete_keyframe_button.setEnabled(can_delete)
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
            parameter.apply_precision(self.value_spin.value()),
            self.smooth_spin.value(),
        )
        parameter.ensure_endpoints(self.project.frame_count)
        self.refresh_current_curve()

    def delete_selected_keyframe(self) -> None:
        parameter = self.current_parameter()
        if not parameter or self.project.is_derived(parameter.name):
            return
        if not 0 <= self.selected_keyframe_index < len(parameter.keyframes):
            return
        parameter.delete_keyframe(self.selected_keyframe_index, self.project.frame_count)
        self.refresh_current_curve()
        self.load_keyframe_fields(min(self.selected_keyframe_index, len(parameter.keyframes) - 1))

    def on_curve_changed(self, parameter_name: str) -> None:
        self.refresh_current_curve()

    def configure_value_spin(self, parameter: CurveParameter | None) -> None:
        self.updating_fields = True
        if parameter:
            self.value_spin.setDecimals(parameter.decimals)
            self.value_spin.setSingleStep(parameter.step)
            self.value_spin.setMinimum(parameter.minimum if parameter.minimum is not None else -1_000_000)
            self.value_spin.setMaximum(parameter.maximum if parameter.maximum is not None else 1_000_000)
        self.updating_fields = False

    def load_display_range(self, parameter: CurveParameter | None) -> None:
        self.updating_fields = True
        enabled = parameter is not None
        self.y_min_spin.setEnabled(enabled)
        self.y_max_spin.setEnabled(enabled)
        if parameter:
            self.y_min_spin.setValue(parameter.display_min if parameter.display_min is not None else 0.0)
            self.y_max_spin.setValue(parameter.display_max if parameter.display_max is not None else 1.0)
        self.updating_fields = False

    def update_display_range(self) -> None:
        if self.updating_fields:
            return
        parameter = self.current_parameter()
        if not parameter:
            return
        parameter.display_min = self.y_min_spin.value()
        parameter.display_max = self.y_max_spin.value()
        self.curve_editor.refresh()

    def load_jitter_settings(self, parameter: CurveParameter | None) -> None:
        self.updating_fields = True
        enabled = bool(parameter and not self.project.is_derived(parameter.name))
        for widget in (
            self.jitter_enabled_check,
            self.jitter_amplitude_spin,
            self.jitter_period_spin,
            self.jitter_octaves_spin,
            self.jitter_seed_spin,
            self.jitter_relative_check,
            self.jitter_affects_derived_check,
        ):
            widget.setEnabled(enabled)
        if parameter:
            jitter = parameter.jitter
            self.jitter_enabled_check.setChecked(jitter.enabled)
            self.jitter_amplitude_spin.setDecimals(parameter.decimals)
            self.jitter_amplitude_spin.setSingleStep(parameter.step)
            self.jitter_amplitude_spin.setValue(abs(jitter.amplitude))
            self.jitter_period_spin.setValue(jitter.period_frames)
            self.jitter_octaves_spin.setValue(jitter.octaves)
            self.jitter_seed_spin.setValue(jitter.seed)
            self.jitter_relative_check.setChecked(jitter.relative)
            self.jitter_affects_derived_check.setChecked(jitter.affects_derived)
        else:
            self.jitter_enabled_check.setChecked(False)
            self.jitter_amplitude_spin.setValue(0.0)
            self.jitter_period_spin.setValue(12)
            self.jitter_octaves_spin.setValue(2)
            self.jitter_seed_spin.setValue(1)
            self.jitter_relative_check.setChecked(False)
            self.jitter_affects_derived_check.setChecked(False)
        self.updating_fields = False

    def update_jitter_settings(self) -> None:
        if self.updating_fields:
            return
        parameter = self.current_parameter()
        if not parameter or self.project.is_derived(parameter.name):
            return
        parameter.jitter.enabled = self.jitter_enabled_check.isChecked()
        parameter.jitter.amplitude = self.jitter_amplitude_spin.value()
        parameter.jitter.period_frames = self.jitter_period_spin.value()
        parameter.jitter.octaves = self.jitter_octaves_spin.value()
        parameter.jitter.seed = self.jitter_seed_spin.value()
        parameter.jitter.relative = self.jitter_relative_check.isChecked()
        parameter.jitter.affects_derived = self.jitter_affects_derived_check.isChecked()
        self.curve_editor.refresh()

    def load_y_range_from_plot(self, low: float, high: float) -> None:
        self.updating_fields = True
        self.y_min_spin.setValue(low)
        self.y_max_spin.setValue(high)
        self.updating_fields = False

    def refresh_current_curve(self) -> None:
        self.curve_editor.set_curve(self.project, self.current_parameter(), self.overlay_parameters())
        self.load_keyframe_fields(self.selected_keyframe_index)
        self.update_status()

    def update_status(self) -> None:
        self.statusBar().showMessage(
            f"{self.project.fps}fps / {self.project.frame_count} frames / {self.project.duration_seconds:.2f}s"
        )
