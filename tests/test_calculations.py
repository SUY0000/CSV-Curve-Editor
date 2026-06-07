from __future__ import annotations

import math

import pytest

from csv_curve_editor.calculations import (
    engine_rpm_to_speed_kmh,
    longitudinal_g_from_speed,
    speed_to_engine_rpm,
    speed_to_wheel_rpm,
)


def test_speed_engine_rpm_roundtrip() -> None:
    speed = 100.0
    gear_ratio = 1.0
    final_ratio = 4.0
    wheel_radius = 0.33

    rpm = speed_to_engine_rpm(speed, 1, [gear_ratio], final_ratio, wheel_radius)
    restored_speed = engine_rpm_to_speed_kmh(rpm, gear_ratio, final_ratio, wheel_radius)

    assert restored_speed == pytest.approx(speed)


def test_lower_gear_has_higher_rpm() -> None:
    low_gear = speed_to_engine_rpm(80.0, 1, [3.5, 1.0], 3.9, 0.33)
    high_gear = speed_to_engine_rpm(80.0, 2, [3.5, 1.0], 3.9, 0.33)

    assert low_gear > high_gear


def test_wheel_rpm_requires_positive_radius() -> None:
    with pytest.raises(ValueError):
        speed_to_wheel_rpm(50.0, 0.0)


def test_longitudinal_g_is_zero_for_constant_speed() -> None:
    values = longitudinal_g_from_speed([60.0, 60.0, 60.0], 25)

    assert values == pytest.approx([0.0, 0.0, 0.0])


def test_longitudinal_g_matches_acceleration() -> None:
    values = longitudinal_g_from_speed([0.0, 36.0], 1)

    assert values == pytest.approx([10.0 / 9.80665, 10.0 / 9.80665])
