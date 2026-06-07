from __future__ import annotations

from csv_curve_editor.jitter import apply_jitter
from csv_curve_editor.models import CurveParameter


def test_apply_jitter_returns_values_when_disabled() -> None:
    parameter = CurveParameter("speed_kmh", decimals=3)
    values = [10.0, 10.0, 10.0]

    assert apply_jitter(values, parameter) == values


def test_apply_jitter_is_stable_for_same_seed() -> None:
    parameter = CurveParameter("speed_kmh", decimals=3)
    parameter.jitter.enabled = True
    parameter.jitter.amplitude = 2.0
    parameter.jitter.period_frames = 8
    parameter.jitter.seed = 42
    values = [50.0] * 12

    assert apply_jitter(values, parameter) == apply_jitter(values, parameter)


def test_apply_jitter_changes_with_seed() -> None:
    parameter = CurveParameter("speed_kmh", decimals=3)
    parameter.jitter.enabled = True
    parameter.jitter.amplitude = 2.0
    parameter.jitter.period_frames = 8
    values = [50.0] * 12

    parameter.jitter.seed = 1
    first = apply_jitter(values, parameter)
    parameter.jitter.seed = 2
    second = apply_jitter(values, parameter)

    assert first != second


def test_apply_jitter_zero_amplitude_does_not_change_values() -> None:
    parameter = CurveParameter("speed_kmh", decimals=3)
    parameter.jitter.enabled = True
    parameter.jitter.amplitude = 0.0

    assert apply_jitter([1.0, 2.0, 3.0], parameter) == [1.0, 2.0, 3.0]


def test_apply_jitter_is_smooth_between_frames() -> None:
    parameter = CurveParameter("speed_kmh", decimals=3)
    parameter.jitter.enabled = True
    parameter.jitter.amplitude = 10.0
    parameter.jitter.period_frames = 12
    parameter.jitter.octaves = 2
    values = [100.0] * 24

    jittered = apply_jitter(values, parameter)
    adjacent_diffs = [abs(right - left) for left, right in zip(jittered, jittered[1:])]

    assert jittered != values
    assert max(adjacent_diffs) < 10.0


def test_apply_jitter_respects_parameter_limits() -> None:
    parameter = CurveParameter("throttle", decimals=3, minimum=0.0, maximum=1.0)
    parameter.jitter.enabled = True
    parameter.jitter.amplitude = 0.5
    values = [0.0, 1.0]

    jittered = apply_jitter(values, parameter)

    assert all(0.0 <= value <= 1.0 for value in jittered)
