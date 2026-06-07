from __future__ import annotations

import pytest

from csv_curve_editor.binding import sync_speed_rpm
from csv_curve_editor.calculations import engine_rpm_to_speed_kmh, speed_to_engine_rpm
from csv_curve_editor.models import Keyframe, ProjectSettings


def test_edit_speed_syncs_rpm_keyframes() -> None:
    project = ProjectSettings.create_default(fps=25, duration_seconds=1.0)
    speed = project.get_parameter("speed_kmh")
    rpm = project.get_parameter("rpm")
    assert speed and rpm
    speed.replace_keyframes([Keyframe(0, 100.0), Keyframe(24, 100.0)], project.frame_count)

    sync_speed_rpm(project, "speed_kmh")

    expected = speed_to_engine_rpm(100.0, 1, project.vehicle_settings.gear_ratios, 3.9, 0.33)
    assert rpm.keyframes[0].value == pytest.approx(round(expected))
    assert project.speed_rpm_link_source == "speed_kmh"


def test_edit_rpm_syncs_speed_keyframes() -> None:
    project = ProjectSettings.create_default(fps=25, duration_seconds=1.0)
    speed = project.get_parameter("speed_kmh")
    rpm = project.get_parameter("rpm")
    assert speed and rpm
    rpm.replace_keyframes([Keyframe(0, 3000.0), Keyframe(24, 3000.0)], project.frame_count)

    sync_speed_rpm(project, "rpm")

    expected = engine_rpm_to_speed_kmh(3000.0, project.vehicle_settings.gear_ratios[0], 3.9, 0.33)
    assert speed.keyframes[0].value == pytest.approx(round(expected, 1))
    assert project.speed_rpm_link_source == "rpm"


def test_gear_keyframes_are_included_when_syncing_rpm() -> None:
    project = ProjectSettings.create_default(fps=25, duration_seconds=1.0)
    speed = project.get_parameter("speed_kmh")
    rpm = project.get_parameter("rpm")
    gear = project.get_parameter("gear")
    assert speed and rpm and gear
    speed.replace_keyframes([Keyframe(0, 100.0), Keyframe(24, 100.0)], project.frame_count)
    gear.replace_keyframes([Keyframe(0, 1.0), Keyframe(12, 2.0), Keyframe(24, 2.0)], project.frame_count)

    sync_speed_rpm(project, "speed_kmh")

    assert [keyframe.frame for keyframe in rpm.keyframes] == [0, 12, 24]
    assert rpm.keyframes[0].value > rpm.keyframes[1].value


def test_disabled_link_does_not_sync() -> None:
    project = ProjectSettings.create_default(fps=25, duration_seconds=1.0)
    project.speed_rpm_link_enabled = False
    rpm = project.get_parameter("rpm")
    speed = project.get_parameter("speed_kmh")
    assert rpm and speed
    old_rpm = rpm.keyframes[0].value
    speed.replace_keyframes([Keyframe(0, 120.0), Keyframe(24, 120.0)], project.frame_count)

    sync_speed_rpm(project, "speed_kmh")

    assert rpm.keyframes[0].value == old_rpm
