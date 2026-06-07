from __future__ import annotations

import pytest

from csv_curve_editor.binding import align_linked_keyframes, delete_linked_keyframes, move_linked_keyframes, sync_linked_smooth, sync_speed_rpm
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


def test_aligned_linked_parameters_add_missing_same_frame_keyframes() -> None:
    project = ProjectSettings.create_default(fps=25, duration_seconds=1.0)
    speed = project.get_parameter("speed_kmh")
    rpm = project.get_parameter("rpm")
    gear = project.get_parameter("gear")
    longitudinal_g = project.get_parameter("longitudinal_g")
    assert speed and rpm and gear and longitudinal_g
    speed.add_keyframe(12, 80.0)

    align_linked_keyframes(project)

    for parameter in [speed, rpm, gear, longitudinal_g]:
        assert 12 in {keyframe.frame for keyframe in parameter.keyframes}


def test_delete_linked_keyframes_removes_same_frame_from_linked_parameters() -> None:
    project = ProjectSettings.create_default(fps=25, duration_seconds=1.0)
    for name in ["speed_kmh", "rpm", "gear", "longitudinal_g"]:
        parameter = project.get_parameter(name)
        assert parameter
        parameter.add_keyframe(12, 1.0)

    assert delete_linked_keyframes(project, 12)

    for name in ["speed_kmh", "rpm", "gear", "longitudinal_g"]:
        parameter = project.get_parameter(name)
        assert parameter
        assert 12 not in {keyframe.frame for keyframe in parameter.keyframes}


def test_move_linked_keyframes_moves_same_frame_without_leaving_old_frame() -> None:
    project = ProjectSettings.create_default(fps=25, duration_seconds=1.0)
    for name in ["speed_kmh", "rpm", "gear", "longitudinal_g"]:
        parameter = project.get_parameter(name)
        assert parameter
        parameter.add_keyframe(12, 10.0, 0.25)

    move_linked_keyframes(project, "speed_kmh", 12, 14, 80.0, 0.75)

    for name in ["speed_kmh", "rpm", "gear", "longitudinal_g"]:
        parameter = project.get_parameter(name)
        assert parameter
        frames = {keyframe.frame for keyframe in parameter.keyframes}
        assert 12 not in frames
        assert 14 in frames
        keyframe = next(keyframe for keyframe in parameter.keyframes if keyframe.frame == 14)
        assert keyframe.smooth == pytest.approx(0.75)


def test_sync_linked_smooth_updates_same_frame_smooth() -> None:
    project = ProjectSettings.create_default(fps=25, duration_seconds=1.0)
    for name in ["speed_kmh", "rpm", "gear", "longitudinal_g"]:
        parameter = project.get_parameter(name)
        assert parameter
        parameter.add_keyframe(12, 10.0, 0.1)

    sync_linked_smooth(project, 12, 0.6)

    for name in ["speed_kmh", "rpm", "gear", "longitudinal_g"]:
        parameter = project.get_parameter(name)
        assert parameter
        keyframe = next(keyframe for keyframe in parameter.keyframes if keyframe.frame == 12)
        assert keyframe.smooth == pytest.approx(0.6)


def test_endpoint_keyframes_cannot_be_deleted() -> None:
    project = ProjectSettings.create_default(fps=25, duration_seconds=1.0)
    speed = project.get_parameter("speed_kmh")
    assert speed

    assert not speed.delete_keyframe(0, project.frame_count)
    assert not delete_linked_keyframes(project, 0)

    assert {keyframe.frame for keyframe in speed.keyframes} == {0, project.frame_count - 1}


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
