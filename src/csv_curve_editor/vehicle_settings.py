from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from .models import VehicleSettings


class VehicleSettingsDialog(QDialog):
    def __init__(self, settings: VehicleSettings, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("车辆传动设置")
        self.settings = settings

        self.gear_ratios_edit = QLineEdit(", ".join(str(value) for value in settings.gear_ratios))
        self.final_ratio_spin = _double_spin(settings.final_ratio, 0.01, 20.0, 3)
        self.wheel_radius_spin = _double_spin(settings.wheel_radius_m, 0.01, 2.0, 3)
        self.idle_spin = _double_spin(settings.rpm_idle, 0.0, 5000.0, 0)
        self.redline_spin = _double_spin(settings.rpm_redline, 1000.0, 20000.0, 0)

        form = QFormLayout()
        form.addRow("Gear ratios（逗号分隔）", self.gear_ratios_edit)
        form.addRow("Final ratio", self.final_ratio_spin)
        form.addRow("Wheel radius (m)", self.wheel_radius_spin)
        form.addRow("Idle RPM", self.idle_spin)
        form.addRow("Redline RPM", self.redline_spin)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def accept(self) -> None:
        try:
            ratios = [float(part.strip()) for part in self.gear_ratios_edit.text().split(",") if part.strip()]
        except ValueError:
            QMessageBox.warning(self, "输入错误", "Gear ratios 只能包含数字和逗号。")
            return
        if not ratios or any(value <= 0 for value in ratios):
            QMessageBox.warning(self, "输入错误", "至少需要一个大于 0 的 gear ratio。")
            return

        self.settings.gear_ratios = ratios
        self.settings.final_ratio = self.final_ratio_spin.value()
        self.settings.wheel_radius_m = self.wheel_radius_spin.value()
        self.settings.rpm_idle = self.idle_spin.value()
        self.settings.rpm_redline = self.redline_spin.value()
        super().accept()


def _double_spin(value: float, minimum: float, maximum: float, decimals: int) -> QDoubleSpinBox:
    spin = QDoubleSpinBox()
    spin.setRange(minimum, maximum)
    spin.setDecimals(decimals)
    spin.setValue(value)
    return spin
