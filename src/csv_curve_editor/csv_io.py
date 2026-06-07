from __future__ import annotations

import csv
from pathlib import Path
from typing import TextIO

from .calculations import longitudinal_g_from_speed, speed_to_engine_rpm
from .interpolation import interpolate_keyframes
from .models import CurveParameter, Keyframe, ProjectSettings

BASE_COLUMNS = ["frame", "time_seconds"]


def sample_project(project: ProjectSettings) -> dict[str, list[float]]:
    project.ensure_parameter_endpoints()
    sampled = {
        parameter.name: interpolate_keyframes(parameter.keyframes, project.frame_count)
        for parameter in project.parameters
    }

    if project.auto_rpm and "speed_kmh" in sampled and "gear" in sampled:
        settings = project.vehicle_settings
        sampled["rpm"] = [
            speed_to_engine_rpm(
                speed,
                int(round(gear)),
                settings.gear_ratios,
                settings.final_ratio,
                settings.wheel_radius_m,
            )
            for speed, gear in zip(sampled["speed_kmh"], sampled["gear"], strict=True)
        ]

    if project.auto_longitudinal_g and "speed_kmh" in sampled:
        sampled["longitudinal_g"] = longitudinal_g_from_speed(sampled["speed_kmh"], project.fps)

    return sampled


def project_to_rows(project: ProjectSettings) -> list[dict[str, float | int]]:
    sampled = sample_project(project)
    parameter_names = [parameter.name for parameter in project.parameters]
    rows: list[dict[str, float | int]] = []
    for frame in range(project.frame_count):
        row: dict[str, float | int] = {
            "frame": frame,
            "time_seconds": frame / project.fps,
        }
        for name in parameter_names:
            row[name] = sampled.get(name, [0.0] * project.frame_count)[frame]
        rows.append(row)
    return rows


def export_csv(project: ProjectSettings, path: str | Path) -> None:
    rows = project_to_rows(project)
    fieldnames = BASE_COLUMNS + [parameter.name for parameter in project.parameters]
    with Path(path).open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def import_csv(path: str | Path, fps: int | None = None) -> ProjectSettings:
    with Path(path).open("r", newline="", encoding="utf-8-sig") as file:
        return _import_csv_file(file, fps)


def _import_csv_file(file: TextIO, fps: int | None = None) -> ProjectSettings:
    reader = csv.DictReader(file)
    rows = list(reader)
    if not rows:
        return ProjectSettings.create_default(fps=fps or 25, duration_seconds=1.0)

    inferred_fps = fps or _infer_fps(rows) or 25
    frame_numbers = [int(float(row.get("frame", index))) for index, row in enumerate(rows)]
    duration_seconds = max(1.0 / inferred_fps, (max(frame_numbers) + 1) / inferred_fps)
    project = ProjectSettings(fps=inferred_fps, duration_seconds=duration_seconds)

    columns = [name for name in (reader.fieldnames or []) if name not in BASE_COLUMNS]
    for column in columns:
        parameter = CurveParameter(column, _guess_unit(column))
        parameter.keyframes = [
            Keyframe(frame, _to_float(row.get(column, "0")), 0.0)
            for frame, row in zip(frame_numbers, rows, strict=True)
        ]
        parameter.ensure_endpoints(project.frame_count)
        project.parameters.append(parameter)

    existing = {parameter.name for parameter in project.parameters}
    for name, unit, value in (
        ("speed_kmh", "km/h", 0.0),
        ("rpm", "rpm", 900.0),
        ("gear", "gear", 1.0),
        ("longitudinal_g", "g", 0.0),
        ("lateral_g", "g", 0.0),
    ):
        if name not in existing:
            parameter = CurveParameter(name, unit)
            parameter.ensure_endpoints(project.frame_count, value)
            project.parameters.append(parameter)
    return project


def _infer_fps(rows: list[dict[str, str]]) -> int | None:
    if len(rows) < 2 or "time_seconds" not in rows[0]:
        return None
    try:
        first = float(rows[0]["time_seconds"])
        second = float(rows[1]["time_seconds"])
    except (KeyError, TypeError, ValueError):
        return None
    delta = second - first
    if delta <= 0:
        return None
    fps = int(round(1.0 / delta))
    return fps if fps in (24, 25, 30, 50, 60, 120) else None


def _guess_unit(name: str) -> str:
    return {
        "speed_kmh": "km/h",
        "rpm": "rpm",
        "gear": "gear",
        "longitudinal_g": "g",
        "lateral_g": "g",
    }.get(name, "")


def _to_float(value: str | None) -> float:
    try:
        return float(value or 0.0)
    except ValueError:
        return 0.0
