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
        "t",
        "speed_kmh",
        "rpm",
        "gear",
        "longitudinal_g",
        "lateral_g",
        "throttle",
        "brake",
        "oil_temp_c",
    ]
    assert rows[0]["timecode"] == "00:00:00:00"
    assert rows[0]["t"] == "0.0"
    assert rows[1]["t"] == "0.016667"
    assert rows[-1]["timecode"] == "00:00:00:59"


def test_custom_parameter_is_exported() -> None:
    project = ProjectSettings.create_default(fps=24, total_frames=24)
    project.add_parameter("boost", "bar", 1.5)
    rows = project_to_rows(project)

    assert len(rows) == 24
    assert rows[0]["boost"] == 1.5


def test_default_throttle_and_brake_use_target_ratio_format() -> None:
    project = ProjectSettings.create_default()
    throttle = project.get_parameter("throttle")
    brake = project.get_parameter("brake")

    assert throttle
    assert brake
    assert project.get_parameter("throttle_pct") is None
    assert project.get_parameter("brake_pct") is None
    assert throttle.minimum == 0.0
    assert throttle.maximum == 1.0
    assert brake.minimum == 0.0
    assert brake.maximum == 1.0


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


def test_sample_project_applies_export_jitter_to_regular_parameters() -> None:
    project = ProjectSettings.create_default(fps=24, total_frames=8)
    throttle = project.get_parameter("throttle")
    assert throttle
    throttle.replace_keyframes([Keyframe(0, 0.5), Keyframe(7, 0.5)], project.frame_count)
    throttle.jitter.enabled = True
    throttle.jitter.amplitude = 0.05
    throttle.jitter.period_frames = 4
    throttle.jitter.seed = 7

    jittered = sample_project(project)["throttle"]
    original = sample_project(project, apply_export_jitter=False)["throttle"]

    assert original == [0.5] * 8
    assert jittered != original
    assert jittered == sample_project(project)["throttle"]


def test_sample_project_does_not_apply_jitter_to_auto_derived_parameter() -> None:
    project = ProjectSettings.create_default(fps=24, total_frames=4)
    longitudinal_g = project.get_parameter("longitudinal_g")
    assert longitudinal_g
    longitudinal_g.jitter.enabled = True
    longitudinal_g.jitter.amplitude = 1.0

    assert sample_project(project)["longitudinal_g"] == [0.0, 0.0, 0.0, 0.0]


def test_source_jitter_does_not_affect_derived_values_by_default() -> None:
    project = ProjectSettings.create_default(fps=24, total_frames=4)
    speed = project.get_parameter("speed_kmh")
    assert speed
    speed.replace_keyframes([Keyframe(0, 50.0), Keyframe(3, 50.0)], project.frame_count)
    speed.jitter.enabled = True
    speed.jitter.amplitude = 5.0
    speed.jitter.period_frames = 4

    assert sample_project(project)["longitudinal_g"] == [0.0, 0.0, 0.0, 0.0]


def test_source_jitter_can_affect_derived_values() -> None:
    project = ProjectSettings.create_default(fps=24, total_frames=4)
    speed = project.get_parameter("speed_kmh")
    assert speed
    speed.replace_keyframes([Keyframe(0, 50.0), Keyframe(3, 50.0)], project.frame_count)
    speed.jitter.enabled = True
    speed.jitter.amplitude = 5.0
    speed.jitter.period_frames = 4
    speed.jitter.affects_derived = True

    assert sample_project(project)["longitudinal_g"] != [0.0, 0.0, 0.0, 0.0]
