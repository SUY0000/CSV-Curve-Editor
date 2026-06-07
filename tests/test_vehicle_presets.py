from __future__ import annotations

from csv_curve_editor.models import VehicleSettings
from csv_curve_editor.vehicle_presets import delete_vehicle_preset, load_vehicle_presets, save_vehicle_preset


def test_save_and_load_vehicle_preset(tmp_path) -> None:
    path = tmp_path / "presets.json"
    settings = VehicleSettings(
        gear_ratios=[3.2, 2.0, 1.3],
        final_ratio=4.1,
        wheel_radius_m=0.31,
        rpm_idle=850.0,
        rpm_redline=7200.0,
    )

    save_vehicle_preset("GT Car", settings, path)
    presets = load_vehicle_presets(path)

    assert list(presets) == ["GT Car"]
    assert presets["GT Car"] == settings


def test_save_vehicle_preset_overwrites_same_name(tmp_path) -> None:
    path = tmp_path / "presets.json"

    save_vehicle_preset("Car", VehicleSettings(final_ratio=3.9), path)
    save_vehicle_preset("Car", VehicleSettings(final_ratio=4.5), path)

    assert load_vehicle_presets(path)["Car"].final_ratio == 4.5


def test_load_vehicle_presets_ignores_invalid_json(tmp_path) -> None:
    path = tmp_path / "presets.json"
    path.write_text("not json", encoding="utf-8")

    assert load_vehicle_presets(path) == {}


def test_delete_vehicle_preset_removes_only_selected_name(tmp_path) -> None:
    path = tmp_path / "presets.json"
    save_vehicle_preset("A", VehicleSettings(final_ratio=3.9), path)
    save_vehicle_preset("B", VehicleSettings(final_ratio=4.5), path)

    assert delete_vehicle_preset("A", path) is True

    presets = load_vehicle_presets(path)
    assert list(presets) == ["B"]
    assert presets["B"].final_ratio == 4.5


def test_delete_vehicle_preset_returns_false_for_missing_name(tmp_path) -> None:
    path = tmp_path / "presets.json"
    save_vehicle_preset("A", VehicleSettings(), path)

    assert delete_vehicle_preset("missing", path) is False
    assert list(load_vehicle_presets(path)) == ["A"]
