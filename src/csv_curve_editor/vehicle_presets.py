from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .models import VehicleSettings

PRESET_FILE = Path.home() / ".csv_curve_editor_vehicle_presets.json"


def load_vehicle_presets(path: str | Path = PRESET_FILE) -> dict[str, VehicleSettings]:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}

    presets = {}
    for name, values in data.items():
        if not isinstance(name, str) or not isinstance(values, dict):
            continue
        settings = _settings_from_dict(values)
        if settings:
            presets[name] = settings
    return presets


def save_vehicle_preset(name: str, settings: VehicleSettings, path: str | Path = PRESET_FILE) -> None:
    preset_name = name.strip()
    if not preset_name:
        raise ValueError("预设名不能为空")

    file_path = Path(path)
    presets = load_vehicle_presets(file_path)
    presets[preset_name] = VehicleSettings(
        gear_ratios=list(settings.gear_ratios),
        final_ratio=settings.final_ratio,
        wheel_radius_m=settings.wheel_radius_m,
        rpm_idle=settings.rpm_idle,
        rpm_redline=settings.rpm_redline,
    )
    _write_vehicle_presets(presets, file_path)


def delete_vehicle_preset(name: str, path: str | Path = PRESET_FILE) -> bool:
    preset_name = name.strip()
    if not preset_name:
        return False

    file_path = Path(path)
    presets = load_vehicle_presets(file_path)
    if preset_name not in presets:
        return False
    del presets[preset_name]
    _write_vehicle_presets(presets, file_path)
    return True


def _write_vehicle_presets(presets: dict[str, VehicleSettings], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({key: asdict(value) for key, value in presets.items()}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _settings_from_dict(values: dict) -> VehicleSettings | None:
    try:
        gear_ratios = [float(value) for value in values.get("gear_ratios", [])]
        if not gear_ratios or any(value <= 0 for value in gear_ratios):
            return None
        return VehicleSettings(
            gear_ratios=gear_ratios,
            final_ratio=float(values["final_ratio"]),
            wheel_radius_m=float(values["wheel_radius_m"]),
            rpm_idle=float(values["rpm_idle"]),
            rpm_redline=float(values["rpm_redline"]),
        )
    except (KeyError, TypeError, ValueError):
        return None
