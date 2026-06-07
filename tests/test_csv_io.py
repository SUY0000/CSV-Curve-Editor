from __future__ import annotations

import csv

from csv_curve_editor.csv_io import export_csv, frame_to_timecode, project_to_rows, sample_project
from csv_curve_editor.models import Keyframe, ProjectSettings


def test_project_to_rows_matches_total_frames() -> None:
    project = ProjectSettings.create_default(fps=25, total_frames=123)
    rows = project_to_rows(project)

    assert len(rows) == 123
    assert rows[0]["frame"] == 0
    assert rows[-1]["frame"] == 122


def test_default_speed_display_range_is_0_to_300() -> None:
    project = ProjectSettings.create_default()
    speed = project.get_parameter("speed_kmh")

    assert speed
    assert speed.display_min == 0.0
    assert speed.display_max == 300.0


def test_export_csv_has_default_columns(tmp_path) -> None:
    project = ProjectSettings.create_default(fps=60, total_frames=60)
    path = tmp_path / "curve.csv"

    export_csv(project, path)

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    assert len(rows) == 60
    assert reader.fieldnames == [
        "frame",
        "timecode",
        "speed_kmh",
        "rpm",
        "gear",
        "longitudinal_g",
        "lateral_g",
    ]
    assert rows[0]["timecode"] == "00:00:00:00"
    assert rows[-1]["timecode"] == "00:00:00:59"


def test_custom_parameter_is_exported() -> None:
    project = ProjectSettings.create_default(fps=24, total_frames=24)
    project.add_parameter("boost", "bar", 1.5)
    rows = project_to_rows(project)

    assert len(rows) == 24
    assert rows[0]["boost"] == 1.5


def test_frame_to_timecode_uses_film_style_frame_count() -> None:
    assert frame_to_timecode(0, 25) == "00:00:00:00"
    assert frame_to_timecode(24, 25) == "00:00:00:24"
    assert frame_to_timecode(25, 25) == "00:00:01:00"
    assert frame_to_timecode(25 * 60 * 60 + 1, 25) == "01:00:00:01"


def test_integer_precision_parameters_export_as_ints() -> None:
    project = ProjectSettings.create_default(fps=24, total_frames=24)
    project.auto_rpm = False
    rpm = project.get_parameter("rpm")
    gear = project.get_parameter("gear")
    assert rpm and gear
    rpm.replace_keyframes([Keyframe(0, 1234.56), Keyframe(23, 2345.67)], project.frame_count)
    gear.replace_keyframes([Keyframe(0, 1.2), Keyframe(23, 2.8)], project.frame_count)

    rows = project_to_rows(project)

    assert isinstance(rows[0]["rpm"], int)
    assert isinstance(rows[0]["gear"], int)
    assert rows[0]["rpm"] == 1235
    assert rows[-1]["gear"] == 3


def test_auto_longitudinal_g_uses_unrounded_speed_values() -> None:
    project = ProjectSettings.create_default(fps=1, total_frames=3)
    speed = project.get_parameter("speed_kmh")
    assert speed
    speed.replace_keyframes([Keyframe(0, 0.0), Keyframe(2, 0.1)], project.frame_count)

    sampled = sample_project(project)

    assert sampled["speed_kmh"] == [0.0, 0.1, 0.1]
    assert sampled["longitudinal_g"] == [0.001, 0.001, 0.001]
