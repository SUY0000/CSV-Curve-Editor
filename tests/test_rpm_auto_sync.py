from __future__ import annotations

import pytest

from csv_curve_editor.calculations import speed_to_engine_rpm
from csv_curve_editor.csv_io import sample_project
from csv_curve_editor.models import Keyframe, ProjectSettings


def test_auto_rpm_is_derived_from_speed_and_gear() -> None:
    project = ProjectSettings.create_default(fps=25, total_frames=25)
    speed = project.get_parameter("speed_kmh")
    gear = project.get_parameter("gear")
    assert speed and gear
    speed.replace_keyframes([Keyframe(0, 100.0), Keyframe(24, 100.0)], project.frame_count)
    gear.replace_keyframes([Keyframe(0, 1.0), Keyframe(24, 1.0)], project.frame_count)

    sampled = sample_project(project)

    expected = speed_to_engine_rpm(100.0, 1, project.vehicle_settings.gear_ratios, 3.9, 0.33)
    assert sampled["rpm"][0] == pytest.approx(round(expected))


def test_manual_rpm_is_used_when_auto_rpm_is_disabled() -> None:
    project = ProjectSettings.create_default(fps=25, total_frames=25)
    project.auto_rpm = False
    rpm = project.get_parameter("rpm")
    speed = project.get_parameter("speed_kmh")
    assert rpm and speed
    rpm.replace_keyframes([Keyframe(0, 3000.0), Keyframe(24, 3000.0)], project.frame_count)
    speed.replace_keyframes([Keyframe(0, 100.0), Keyframe(24, 100.0)], project.frame_count)

    sampled = sample_project(project)

    assert sampled["rpm"] == [3000.0] * project.frame_count


def test_editing_rpm_does_not_change_speed() -> None:
    project = ProjectSettings.create_default(fps=25, total_frames=25)
    project.auto_rpm = False
    rpm = project.get_parameter("rpm")
    speed = project.get_parameter("speed_kmh")
    assert rpm and speed
    speed.replace_keyframes([Keyframe(0, 80.0), Keyframe(24, 80.0)], project.frame_count)

    rpm.replace_keyframes([Keyframe(0, 3000.0), Keyframe(24, 3000.0)], project.frame_count)

    assert [keyframe.value for keyframe in speed.keyframes] == [80.0, 80.0]


def test_gear_output_shifts_on_keyframe() -> None:
    project = ProjectSettings.create_default(fps=25, total_frames=5)
    gear = project.get_parameter("gear")
    assert gear
    gear.replace_keyframes([Keyframe(0, 1.0), Keyframe(4, 2.0)], project.frame_count)

    sampled = sample_project(project)

    assert sampled["gear"] == [1.0, 1.0, 1.0, 1.0, 2.0]


def test_auto_rpm_uses_fractional_gear_between_keyframes() -> None:
    project = ProjectSettings.create_default(fps=25, total_frames=5)
    speed = project.get_parameter("speed_kmh")
    gear = project.get_parameter("gear")
    assert speed and gear
    speed.replace_keyframes([Keyframe(0, 100.0), Keyframe(4, 100.0)], project.frame_count)
    gear.replace_keyframes([Keyframe(0, 1.0), Keyframe(4, 2.0)], project.frame_count)

    sampled = sample_project(project)

    assert sampled["rpm"][0] > sampled["rpm"][1] > sampled["rpm"][2] > sampled["rpm"][3] > sampled["rpm"][4]
