from __future__ import annotations

import csv
from pathlib import Path
from typing import TextIO

from .calculations import longitudinal_g_from_speed
from .interpolation import interpolate_keyframes
from .models import Keyframe, ProjectSettings, create_parameter_from_name

BASE_COLUMNS = ["frame", "time_seconds"]


def sample_project(project: ProjectSettings) -> dict[str, list[float]]:
    project.ensure_parameter_endpoints()
    sampled = {}
    raw_values_by_name = {}
    for parameter in project.parameters:
        values = interpolate_keyframes(parameter.keyframes, project.frame_count)
        raw_values_by_name[parameter.name] = values
        sampled[parameter.name] = [parameter.apply_precision(value) for value in values]

    longitudinal_g = project.get_parameter("longitudinal_g")
    speed_values = raw_values_by_name.get("speed_kmh")
    if project.auto_longitudinal_g and longitudinal_g and speed_values is not None:
        sampled["longitudinal_g"] = [
            longitudinal_g.apply_precision(value)
            for value in longitudinal_g_from_speed(speed_values, project.fps)
        ]

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
        for parameter in project.parameters:
            value = sampled.get(parameter.name, [0.0] * project.frame_count)[frame]
            row[parameter.name] = _csv_value(parameter.decimals, value)
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
        parameter = create_parameter_from_name(column, _guess_unit(column))
        parameter.keyframes = [
            Keyframe(frame, parameter.apply_precision(_to_float(row.get(column, "0"))), 0.0)
            for frame, row in zip(frame_numbers, rows, strict=True)
        ]
        parameter.ensure_endpoints(project.frame_count)
        project.parameters.append(parameter)

    existing = {parameter.name for parameter in project.parameters}
    defaults = ProjectSettings.create_default(project.fps, project.duration_seconds)
    for parameter in defaults.parameters:
        if parameter.name not in existing:
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


def _csv_value(decimals: int, value: float) -> float | int:
    if decimals == 0:
        return int(round(value))
    return round(float(value), decimals)
