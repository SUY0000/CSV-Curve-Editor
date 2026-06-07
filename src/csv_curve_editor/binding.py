from __future__ import annotations

from .calculations import engine_rpm_to_speed_kmh, longitudinal_g_from_speed, speed_to_engine_rpm
from .interpolation import interpolate_keyframes
from .models import Keyframe, ProjectSettings

LINKED_PARAMETERS = {"speed_kmh", "rpm", "gear", "longitudinal_g"}
SPEED_RPM_PARAMETERS = {"speed_kmh", "rpm", "gear"}


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
        synced_keyframes.append(Keyframe(frame, target.apply_precision(value), linked_smooth_for_frame(project, frame)))

    target.replace_keyframes(synced_keyframes, project.frame_count)


def sync_after_parameter_edit(project: ProjectSettings, parameter_name: str) -> None:
    if parameter_name in {"speed_kmh", "rpm"}:
        sync_speed_rpm(project, parameter_name)
    elif parameter_name == "gear":
        sync_speed_rpm(project, project.speed_rpm_link_source)
    if parameter_name in LINKED_PARAMETERS:
        align_linked_keyframes(project)


def move_linked_keyframes(
    project: ProjectSettings,
    source_name: str,
    old_frame: int,
    new_frame: int,
    source_value: float,
    smooth: float,
) -> None:
    source = project.get_parameter(source_name)
    if not source or source_name not in LINKED_PARAMETERS:
        return
    new_frame = min(max(0, int(round(new_frame))), project.frame_count - 1)
    if old_frame in {0, project.frame_count - 1}:
        new_frame = old_frame

    old_values = {}
    for parameter in project.parameters:
        if parameter.name not in LINKED_PARAMETERS:
            continue
        old_keyframe = next((keyframe for keyframe in parameter.keyframes if keyframe.frame == old_frame), None)
        if old_keyframe is not None:
            old_values[parameter.name] = old_keyframe.value

    for parameter in project.parameters:
        if parameter.name not in LINKED_PARAMETERS:
            continue
        old_index = next((index for index, keyframe in enumerate(parameter.keyframes) if keyframe.frame == old_frame), None)
        if old_index is not None:
            parameter.keyframes.pop(old_index)
        if parameter.name == source_name:
            value = source_value
        else:
            value = old_values.get(parameter.name, value_at_frame(project, parameter.name, new_frame))
        parameter.add_keyframe(new_frame, value, smooth)
        parameter.ensure_endpoints(project.frame_count)

    sync_after_parameter_edit(project, source_name)
    sync_linked_smooth(project, new_frame, smooth)


def sync_linked_smooth(project: ProjectSettings, frame: int, smooth: float) -> None:
    if frame in {0, project.frame_count - 1}:
        return
    for parameter in project.parameters:
        if parameter.name not in LINKED_PARAMETERS:
            continue
        for index, keyframe in enumerate(parameter.keyframes):
            if keyframe.frame == frame:
                parameter.keyframes[index] = Keyframe(keyframe.frame, keyframe.value, smooth)
                break


def align_linked_keyframes(project: ProjectSettings) -> None:
    linked = [parameter for parameter in project.parameters if parameter.name in LINKED_PARAMETERS]
    if not linked:
        return
    frames = sorted({keyframe.frame for parameter in linked for keyframe in parameter.keyframes})
    for parameter in linked:
        existing_frames = {keyframe.frame for keyframe in parameter.keyframes}
        for frame in frames:
            if frame not in existing_frames:
                parameter.add_keyframe(frame, value_at_frame(project, parameter.name, frame), linked_smooth_for_frame(project, frame))
        parameter.ensure_endpoints(project.frame_count)


def delete_linked_keyframes(project: ProjectSettings, frame: int) -> bool:
    if frame in {0, project.frame_count - 1}:
        return False

    deleted = False
    for parameter in project.parameters:
        if parameter.name not in LINKED_PARAMETERS:
            continue
        for index, keyframe in enumerate(list(parameter.keyframes)):
            if keyframe.frame == frame:
                deleted = parameter.delete_keyframe(index, project.frame_count) or deleted
                break
    if deleted:
        sync_speed_rpm(project, project.speed_rpm_link_source)
    return deleted


def linked_smooth_for_frame(project: ProjectSettings, frame: int) -> float:
    for parameter in project.parameters:
        if parameter.name not in LINKED_PARAMETERS:
            continue
        for keyframe in parameter.keyframes:
            if keyframe.frame == frame:
                return keyframe.smooth
    return 0.0


def value_at_frame(project: ProjectSettings, parameter_name: str, frame: int) -> float:
    parameter = project.get_parameter(parameter_name)
    if not parameter:
        return 0.0
    frame = min(max(0, frame), project.frame_count - 1)

    if parameter_name == "longitudinal_g" and project.auto_longitudinal_g:
        speed = project.get_parameter("speed_kmh")
        if speed:
            speed_values = interpolate_keyframes(speed.keyframes, project.frame_count)
            return parameter.apply_precision(longitudinal_g_from_speed(speed_values, project.fps)[frame])

    values = interpolate_keyframes(parameter.keyframes, project.frame_count)
    return parameter.apply_precision(values[frame])


def gear_ratio_for_number(gear_number: int, gear_ratios: list[float]) -> float:
    if not gear_ratios:
        return 1.0
    gear_number = min(max(1, int(round(gear_number))), len(gear_ratios))
    return gear_ratios[gear_number - 1]
