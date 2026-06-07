from __future__ import annotations

from collections.abc import Sequence

from .models import Keyframe


def interpolate_keyframes(keyframes: Sequence[Keyframe], frame_count: int) -> list[float]:
    if frame_count <= 0:
        return []
    if not keyframes:
        return [0.0] * frame_count

    points = _normalized_points(keyframes, frame_count)
    if len(points) == 1:
        return [points[0].value] * frame_count

    tangents = _smooth_tangents(points)
    values: list[float] = []
    segment = 0
    for frame in range(frame_count):
        while segment < len(points) - 2 and frame > points[segment + 1].frame:
            segment += 1
        left = points[segment]
        right = points[segment + 1]
        values.append(_interpolate_between(left, right, tangents[segment], tangents[segment + 1], frame))
    return values


def _normalized_points(keyframes: Sequence[Keyframe], frame_count: int) -> list[Keyframe]:
    last_frame = max(0, frame_count - 1)
    by_frame: dict[int, Keyframe] = {}
    for keyframe in keyframes:
        frame = min(max(0, int(round(keyframe.frame))), last_frame)
        by_frame[frame] = Keyframe(frame, float(keyframe.value), keyframe.smooth)
    return [by_frame[frame] for frame in sorted(by_frame)]


def _smooth_tangents(points: Sequence[Keyframe]) -> list[float]:
    slopes = [
        (right.value - left.value) / (right.frame - left.frame)
        for left, right in zip(points, points[1:])
    ]
    tangents = [0.0] * len(points)
    tangents[0] = slopes[0]
    tangents[-1] = slopes[-1]

    for index in range(1, len(points) - 1):
        previous_slope = slopes[index - 1]
        next_slope = slopes[index]
        if previous_slope * next_slope <= 0.0:
            tangents[index] = 0.0
        else:
            tangents[index] = 2.0 * previous_slope * next_slope / (previous_slope + next_slope)
    return tangents


def _interpolate_between(left: Keyframe, right: Keyframe, left_tangent: float, right_tangent: float, frame: int) -> float:
    if right.frame <= left.frame:
        return right.value
    if frame <= left.frame:
        return left.value
    if frame >= right.frame:
        return right.value

    span = right.frame - left.frame
    t = (frame - left.frame) / span
    smooth = min(1.0, max(0.0, (left.smooth + right.smooth) / 2.0))
    linear_value = left.value + (right.value - left.value) * t
    smooth_value = _hermite_value(left.value, right.value, left_tangent * span, right_tangent * span, t)
    return (1.0 - smooth) * linear_value + smooth * smooth_value


def _hermite_value(left_value: float, right_value: float, left_tangent: float, right_tangent: float, t: float) -> float:
    t2 = t * t
    t3 = t2 * t
    return (
        (2.0 * t3 - 3.0 * t2 + 1.0) * left_value
        + (t3 - 2.0 * t2 + t) * left_tangent
        + (-2.0 * t3 + 3.0 * t2) * right_value
        + (t3 - t2) * right_tangent
    )
