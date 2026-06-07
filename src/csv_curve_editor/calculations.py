from __future__ import annotations

import math
from collections.abc import Sequence

GRAVITY = 9.80665


def speed_to_wheel_rpm(speed_kmh: float, wheel_radius_m: float) -> float:
    if wheel_radius_m <= 0:
        raise ValueError("wheel_radius_m 必须大于 0")
    speed_mps = speed_kmh / 3.6
    circumference = 2.0 * math.pi * wheel_radius_m
    return speed_mps / circumference * 60.0


def wheel_rpm_to_engine_rpm(wheel_rpm: float, gear_ratio: float, final_ratio: float) -> float:
    return wheel_rpm * gear_ratio * final_ratio


def engine_rpm_to_speed_kmh(
    rpm: float,
    gear_ratio: float,
    final_ratio: float,
    wheel_radius_m: float,
) -> float:
    if wheel_radius_m <= 0:
        raise ValueError("wheel_radius_m 必须大于 0")
    total_ratio = gear_ratio * final_ratio
    if total_ratio <= 0:
        raise ValueError("gear_ratio * final_ratio 必须大于 0")
    wheel_rpm = rpm / total_ratio
    speed_mps = wheel_rpm * (2.0 * math.pi * wheel_radius_m) / 60.0
    return speed_mps * 3.6


def speed_to_engine_rpm(
    speed_kmh: float,
    gear_number: float,
    gear_ratios: Sequence[float],
    final_ratio: float,
    wheel_radius_m: float,
) -> float:
    if not gear_ratios:
        return 0.0
    gear_ratio = _gear_ratio_for_number(gear_number, gear_ratios)
    wheel_rpm = speed_to_wheel_rpm(speed_kmh, wheel_radius_m)
    return wheel_rpm_to_engine_rpm(wheel_rpm, gear_ratio, final_ratio)


def _gear_ratio_for_number(gear_number: float, gear_ratios: Sequence[float]) -> float:
    gear = min(max(1.0, float(gear_number)), float(len(gear_ratios)))
    lower_number = int(math.floor(gear))
    upper_number = int(math.ceil(gear))
    lower_ratio = gear_ratios[lower_number - 1]
    upper_ratio = gear_ratios[upper_number - 1]
    return lower_ratio + (upper_ratio - lower_ratio) * (gear - lower_number)


def longitudinal_g_from_speed(speed_kmh_values: Sequence[float], fps: int) -> list[float]:
    if fps <= 0:
        raise ValueError("fps 必须大于 0")
    if not speed_kmh_values:
        return []
    if len(speed_kmh_values) == 1:
        return [0.0]

    dt = 1.0 / fps
    speed_mps = [value / 3.6 for value in speed_kmh_values]
    g_values = [0.0] * len(speed_mps)
    for index in range(len(speed_mps)):
        if index == 0:
            acceleration = (speed_mps[1] - speed_mps[0]) / dt
        elif index == len(speed_mps) - 1:
            acceleration = (speed_mps[index] - speed_mps[index - 1]) / dt
        else:
            acceleration = (speed_mps[index + 1] - speed_mps[index - 1]) / (2.0 * dt)
        g_values[index] = acceleration / GRAVITY
    return g_values
