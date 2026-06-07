from __future__ import annotations

from collections.abc import Sequence

from .models import Keyframe


def smoothstep(t: float) -> float:
    return t * t * (3.0 - 2.0 * t)


def interpolate_keyframes(keyframes: Sequence[Keyframe], frame_count: int) -> list[float]:
    if frame_count <= 0:
        return []
    if not keyframes:
        return [0.0] * frame_count

    points = _normalized_points(keyframes, frame_count)
    if len(points) == 1:
        return [points[0].value] * frame_count

    values: list[float] = []
    segment = 0
    for frame in range(frame_count):
        while segment < len(points) - 2 and frame > points[segment + 1].frame:
            segment += 1
        left = points[segment]
        right = points[segment + 1]
        values.append(_interpolate_between(left, right, frame))
    return values


def _normalized_points(keyframes: Sequence[Keyframe], frame_count: int) -> list[Keyframe]:
    last_frame = max(0, frame_count - 1)
    by_frame: dict[int, Keyframe] = {}
    for keyframe in keyframes:
        frame = min(max(0, int(round(keyframe.frame))), last_frame)
        by_frame[frame] = Keyframe(frame, float(keyframe.value), keyframe.smooth)
    return [by_frame[frame] for frame in sorted(by_frame)]


def _interpolate_between(left: Keyframe, right: Keyframe, frame: int) -> float:
    if right.frame <= left.frame:
        return right.value
    if frame <= left.frame:
        return left.value
    if frame >= right.frame:
        return right.value

    t = (frame - left.frame) / (right.frame - left.frame)
    smooth = min(1.0, max(0.0, (left.smooth + right.smooth) / 2.0))
    eased_t = (1.0 - smooth) * t + smooth * smoothstep(t)
    return left.value + (right.value - left.value) * eased_t
