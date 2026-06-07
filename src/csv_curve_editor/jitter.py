from __future__ import annotations

import math
import random

from .models import CurveParameter


def apply_jitter(values: list[float], parameter: CurveParameter) -> list[float]:
    settings = parameter.jitter
    if not settings.enabled or settings.amplitude == 0.0 or not values:
        return values

    return [parameter.apply_precision(value + _offset_for_frame(index, value, parameter)) for index, value in enumerate(values)]


def jittered_values_for_preview(values: list[float], parameter: CurveParameter) -> list[float]:
    return apply_jitter(values, parameter)


def _offset_for_frame(frame: int, value: float, parameter: CurveParameter) -> float:
    settings = parameter.jitter
    amplitude = abs(settings.amplitude)
    if settings.relative:
        amplitude *= abs(value)
    return amplitude * _fractal_noise(frame, settings.period_frames, settings.octaves, settings.seed)


def _fractal_noise(frame: int, period_frames: int, octaves: int, seed: int) -> float:
    period = max(1.0, float(period_frames))
    octave_count = min(max(1, int(octaves)), 4)
    total = 0.0
    weight = 0.0
    amplitude = 1.0
    for octave in range(octave_count):
        total += amplitude * _smooth_noise(frame / period, seed + octave * 10_000)
        weight += amplitude
        amplitude *= 0.5
        period = max(1.0, period * 0.5)
    return total / weight if weight else 0.0


def _smooth_noise(position: float, seed: int) -> float:
    left = math.floor(position)
    right = left + 1
    t = position - left
    t = t * t * (3.0 - 2.0 * t)
    return _lerp(_noise_at(left, seed), _noise_at(right, seed), t)


def _noise_at(index: int, seed: int) -> float:
    return random.Random(seed + index * 1_000_003).uniform(-1.0, 1.0)


def _lerp(left: float, right: float, t: float) -> float:
    return left + (right - left) * t
