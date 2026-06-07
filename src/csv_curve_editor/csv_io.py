from __future__ import annotations

import csv
from pathlib import Path
from typing import TextIO

from .calculations import longitudinal_g_from_speed, speed_to_engine_rpm
from .interpolation import interpolate_keyframes
from .jitter import apply_jitter
from .models import CurveParameter, Keyframe, ProjectSettings, create_parameter_from_name

BASE_COLUMNS = ["frame", "timecode", "t"]
LEGACY_BASE_COLUMNS = ["frame", "time_seconds"]


def sample_project(project: ProjectSettings, apply_export_jitter: bool = True) -> dict[str, list[float]]:
    project.ensure_parameter_endpoints()
    sampled = {}
    raw_values_by_name = {}
    derived_input_values_by_name = {}
    for parameter in project.parameters:
        values = interpolate_keyframes(parameter.keyframes, project.frame_count)
        raw_values_by_name[parameter.name] = values
        parameter_values = _sample_parameter_values(parameter, values, project.frame_count)
        export_values = parameter_values
        if apply_export_jitter and not project.is_derived(parameter.name):
            export_values = apply_jitter(parameter_values, parameter)
        sampled[parameter.name] = export_values
        derived_input_values_by_name[parameter.name] = (
            export_values if apply_export_jitter and parameter.jitter.affects_derived else values
        )

    speed_values = derived_input_values_by_name.get("speed_kmh")
    gear_values = raw_values_by_name.get("gear")
    rpm = project.get_parameter("rpm")
    if project.auto_rpm and rpm and speed_values is not None and gear_values is not None:
        settings = project.vehicle_settings
        sampled["rpm"] = [
            rpm.apply_precision(
                speed_to_engine_rpm(
                    speed,
                    gear,
                    settings.gear_ratios,
                    settings.final_ratio,
                    settings.wheel_radius_m,
                )
            )
            for speed, gear in zip(speed_values, gear_values, strict=True)
        ]

    longitudinal_g = project.get_parameter("longitudinal_g")
    if project.auto_longitudinal_g and longitudinal_g and speed_values is not None:
        sampled["longitudinal_g"] = [
            longitudinal_g.apply_precision(value)
            for value in longitudinal_g_from_speed(speed_values, project.fps)
        ]

    return sampled


def _sample_parameter_values(parameter: CurveParameter, interpolated_values: list[float], frame_count: int) -> list[float]:
    if parameter.name != "gear":
        return [parameter.apply_precision(value) for value in interpolated_values]

    parameter.ensure_endpoints(frame_count)
    values = [parameter.apply_precision(parameter.keyframes[0].value)] * frame_count
    keyframes = sorted(parameter.keyframes, key=lambda keyframe: keyframe.frame)
    for index, keyframe in enumerate(keyframes):
        start = min(max(0, keyframe.frame), frame_count)
        end = min(max(0, keyframes[index + 1].frame if index + 1 < len(keyframes) else frame_count), frame_count)
        for frame in range(start, end):
            values[frame] = parameter.apply_precision(keyframe.value)
    return values


def project_to_rows(project: ProjectSettings) -> list[dict[str, float | int | str]]:
    sampled = sample_project(project)
    rows: list[dict[str, float | int | str]] = []
    for frame in range(project.frame_count):
        row: dict[str, float | int | str] = {
            "frame": frame,
            "timecode": frame_to_timecode(frame, project.fps),
            "t": round(frame / project.fps, 6),
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
        return ProjectSettings.create_default(fps=fps or 25, total_frames=1)

    inferred_fps = fps or _infer_fps(rows) or 25
    frame_numbers = [int(float(row.get("frame", index))) for index, row in enumerate(rows)]
    total_frames = max(1, max(frame_numbers) + 1)
    project = ProjectSettings(fps=inferred_fps, total_frames=total_frames)

    base_columns = set(BASE_COLUMNS) | set(LEGACY_BASE_COLUMNS)
    columns = [name for name in (reader.fieldnames or []) if name not in base_columns]
    for column in columns:
        parameter = create_parameter_from_name(column, _guess_unit(column))
        parameter.keyframes = [
            Keyframe(frame, parameter.apply_precision(_to_float(row.get(column, "0"))))
            for frame, row in zip(frame_numbers, rows, strict=True)
        ]
        parameter.ensure_endpoints(project.frame_count)
        project.parameters.append(parameter)

    existing = {parameter.name for parameter in project.parameters}
    defaults = ProjectSettings.create_default(project.fps, total_frames=project.frame_count)
    for parameter in defaults.parameters:
        if parameter.name not in existing:
            project.parameters.append(parameter)
    return project


def _infer_fps(rows: list[dict[str, str]]) -> int | None:
    if len(rows) < 2:
        return None
    if "time_seconds" in rows[0]:
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
    return None


def frame_to_timecode(frame: int, fps: int) -> str:
    if fps <= 0:
        raise ValueError("fps 必须大于 0")
    frame = max(0, int(frame))
    hours, remainder = divmod(frame, fps * 60 * 60)
    minutes, remainder = divmod(remainder, fps * 60)
    seconds, frames = divmod(remainder, fps)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"


def _guess_unit(name: str) -> str:
    return {
        "speed_kmh": "km/h",
        "rpm": "rpm",
        "gear": "gear",
        "throttle": "",
        "brake": "",
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
