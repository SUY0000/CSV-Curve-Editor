from __future__ import annotations

from .calculations import engine_rpm_to_speed_kmh, speed_to_engine_rpm
from .interpolation import interpolate_keyframes
from .models import Keyframe, ProjectSettings

LINKED_PARAMETERS = {"speed_kmh", "rpm", "gear"}


def sync_speed_rpm(project: ProjectSettings, source_name: str | None = None) -> None:
    if not project.speed_rpm_link_enabled:
        return
    if source_name not in {"speed_kmh", "rpm"}:
        source_name = project.speed_rpm_link_source
    if source_name not in {"speed_kmh", "rpm"}:
        source_name = "speed_kmh"

    source = project.get_parameter(source_name)
    target_name = "rpm" if source_name == "speed_kmh" else "speed_kmh"
    target = project.get_parameter(target_name)
    gear = project.get_parameter("gear")
    if not source or not target or not gear:
        return

    project.speed_rpm_link_source = source_name
    source.ensure_endpoints(project.frame_count)
    gear.ensure_endpoints(project.frame_count)
    source_values = interpolate_keyframes(source.keyframes, project.frame_count)
    gear_values = interpolate_keyframes(gear.keyframes, project.frame_count)
    settings = project.vehicle_settings

    frames = sorted({keyframe.frame for keyframe in source.keyframes} | {keyframe.frame for keyframe in gear.keyframes})
    synced_keyframes: list[Keyframe] = []
    for frame in frames:
        frame = min(max(0, frame), project.frame_count - 1)
        gear_number = int(round(gear_values[frame]))
        if source_name == "speed_kmh":
            value = speed_to_engine_rpm(
                source_values[frame],
                gear_number,
                settings.gear_ratios,
                settings.final_ratio,
                settings.wheel_radius_m,
            )
        else:
            gear_ratio = gear_ratio_for_number(gear_number, settings.gear_ratios)
            value = engine_rpm_to_speed_kmh(
                source_values[frame],
                gear_ratio,
                settings.final_ratio,
                settings.wheel_radius_m,
            )
        synced_keyframes.append(Keyframe(frame, target.apply_precision(value), 0.0))

    target.replace_keyframes(synced_keyframes, project.frame_count)


def sync_after_parameter_edit(project: ProjectSettings, parameter_name: str) -> None:
    if parameter_name in {"speed_kmh", "rpm"}:
        sync_speed_rpm(project, parameter_name)
    elif parameter_name == "gear":
        sync_speed_rpm(project, project.speed_rpm_link_source)


def gear_ratio_for_number(gear_number: int, gear_ratios: list[float]) -> float:
    if not gear_ratios:
        return 1.0
    gear_number = min(max(1, int(round(gear_number))), len(gear_ratios))
    return gear_ratios[gear_number - 1]
