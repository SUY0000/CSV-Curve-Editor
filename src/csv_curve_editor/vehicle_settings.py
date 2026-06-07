from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from .models import VehicleSettings
from .vehicle_presets import delete_vehicle_preset, load_vehicle_presets, save_vehicle_preset


class VehicleSettingsDialog(QDialog):
    def __init__(self, settings: VehicleSettings, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("车辆传动设置")
        self.settings = settings
        self.presets = load_vehicle_presets()

        self.preset_combo = QComboBox()
        self.preset_combo.addItems(sorted(self.presets))
        self.apply_preset_button = QPushButton("应用预设")
        self.save_preset_button = QPushButton("保存为预设")
        self.delete_preset_button = QPushButton("删除预设")

        self.gear_ratios_edit = QLineEdit(", ".join(str(value) for value in settings.gear_ratios))
        self.final_ratio_spin = _double_spin(settings.final_ratio, 0.01, 20.0, 3)
        self.wheel_radius_spin = _double_spin(settings.wheel_radius_m, 0.01, 2.0, 3)
        self.idle_spin = _double_spin(settings.rpm_idle, 0.0, 5000.0, 0)
        self.redline_spin = _double_spin(settings.rpm_redline, 1000.0, 20000.0, 0)

        preset_layout = QHBoxLayout()
        preset_layout.addWidget(self.preset_combo)
        preset_layout.addWidget(self.apply_preset_button)
        preset_layout.addWidget(self.save_preset_button)
        preset_layout.addWidget(self.delete_preset_button)

        form = QFormLayout()
        form.addRow("车辆预设", preset_layout)
        form.addRow("Gear ratios（逗号分隔）", self.gear_ratios_edit)
        form.addRow("Final ratio", self.final_ratio_spin)
        form.addRow("Wheel radius (m)", self.wheel_radius_spin)
        form.addRow("Idle RPM", self.idle_spin)
        form.addRow("Redline RPM", self.redline_spin)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.apply_preset_button.clicked.connect(self.apply_selected_preset)
        self.save_preset_button.clicked.connect(self.save_current_preset)
        self.delete_preset_button.clicked.connect(self.delete_selected_preset)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def apply_selected_preset(self) -> None:
        preset = self.presets.get(self.preset_combo.currentText())
        if preset:
            self.load_settings(preset)

    def save_current_preset(self) -> None:
        settings = self.settings_from_fields()
        if not settings:
            return
        name, ok = QInputDialog.getText(self, "保存车辆预设", "预设名")
        if not ok:
            return
        try:
            save_vehicle_preset(name, settings)
        except ValueError as error:
            QMessageBox.warning(self, "保存失败", str(error))
            return
        self.refresh_presets(name.strip())

    def delete_selected_preset(self) -> None:
        name = self.preset_combo.currentText()
        if not name:
            return
        result = QMessageBox.question(self, "删除车辆预设", f"确定删除预设“{name}”吗？")
        if result != QMessageBox.StandardButton.Yes:
            return
        delete_vehicle_preset(name)
        self.refresh_presets()

    def refresh_presets(self, selected_name: str = "") -> None:
        self.presets = load_vehicle_presets()
        self.preset_combo.clear()
        self.preset_combo.addItems(sorted(self.presets))
        if selected_name:
            self.preset_combo.setCurrentText(selected_name)

    def load_settings(self, settings: VehicleSettings) -> None:
        self.gear_ratios_edit.setText(", ".join(str(value) for value in settings.gear_ratios))
        self.final_ratio_spin.setValue(settings.final_ratio)
        self.wheel_radius_spin.setValue(settings.wheel_radius_m)
        self.idle_spin.setValue(settings.rpm_idle)
        self.redline_spin.setValue(settings.rpm_redline)

    def settings_from_fields(self) -> VehicleSettings | None:
        try:
            ratios = [float(part.strip()) for part in self.gear_ratios_edit.text().split(",") if part.strip()]
        except ValueError:
            QMessageBox.warning(self, "输入错误", "Gear ratios 只能包含数字和逗号。")
            return None
        if not ratios or any(value <= 0 for value in ratios):
            QMessageBox.warning(self, "输入错误", "至少需要一个大于 0 的 gear ratio。")
            return None

        return VehicleSettings(
            gear_ratios=ratios,
            final_ratio=self.final_ratio_spin.value(),
            wheel_radius_m=self.wheel_radius_spin.value(),
            rpm_idle=self.idle_spin.value(),
            rpm_redline=self.redline_spin.value(),
        )

    def accept(self) -> None:
        settings = self.settings_from_fields()
        if not settings:
            return
        self.settings.gear_ratios = settings.gear_ratios
        self.settings.final_ratio = settings.final_ratio
        self.settings.wheel_radius_m = settings.wheel_radius_m
        self.settings.rpm_idle = settings.rpm_idle
        self.settings.rpm_redline = settings.rpm_redline
        super().accept()


def _double_spin(value: float, minimum: float, maximum: float, decimals: int) -> QDoubleSpinBox:
    spin = QDoubleSpinBox()
    spin.setRange(minimum, maximum)
    spin.setDecimals(decimals)
    spin.setValue(value)
    return spin
