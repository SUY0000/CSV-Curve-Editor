from __future__ import annotations

import pytest

from csv_curve_editor.interpolation import interpolate_keyframes
from csv_curve_editor.models import Keyframe


def test_linear_interpolation() -> None:
    values = interpolate_keyframes([Keyframe(0, 0.0), Keyframe(4, 40.0)], 5)

    assert values == pytest.approx([0.0, 10.0, 20.0, 30.0, 40.0])


def test_smooth_interpolation_keeps_endpoints() -> None:
    values = interpolate_keyframes([Keyframe(0, 0.0, 1.0), Keyframe(4, 40.0, 1.0)], 5)

    assert values[0] == pytest.approx(0.0)
    assert values[-1] == pytest.approx(40.0)
    assert values == pytest.approx([0.0, 10.0, 20.0, 30.0, 40.0])


def test_smooth_interpolation_uses_neighboring_keyframes_for_curve_shape() -> None:
    values = interpolate_keyframes(
        [Keyframe(0, 0.0, 1.0), Keyframe(4, 40.0, 1.0), Keyframe(8, 120.0, 1.0)],
        9,
    )

    assert values[0] == pytest.approx(0.0)
    assert values[4] == pytest.approx(40.0)
    assert values[-1] == pytest.approx(120.0)
    assert values[2] < 20.0
    assert values[6] < 80.0


def test_empty_keyframes_default_to_zero() -> None:
    assert interpolate_keyframes([], 3) == [0.0, 0.0, 0.0]
