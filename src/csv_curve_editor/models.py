from __future__ import annotations

from dataclasses import dataclass, field

SUPPORTED_FPS = (24, 25, 30, 50, 60, 120)
DEFAULT_PARAMETER_SPECS = (
    ("speed_kmh", "km/h", 0.0, 1, 0.1, 0.0, None, 0.0, 300.0),
    ("rpm", "rpm", 900.0, 0, 1.0, 0.0, None, 0.0, 8000.0),
    ("gear", "gear", 1.0, 0, 1.0, 1.0, None, 1.0, 6.0),
    ("longitudinal_g", "g", 0.0, 3, 0.001, None, None, -2.0, 2.0),
    ("lateral_g", "g", 0.0, 3, 0.001, None, None, -2.0, 2.0),
)


@dataclass
class Keyframe:
    frame: int
    value: float
    smooth: float = 0.0

    def __post_init__(self) -> None:
        self.frame = int(round(self.frame))
        self.value = float(self.value)
        self.smooth = min(1.0, max(0.0, float(self.smooth)))


@dataclass
class CurveParameter:
    name: str
    unit: str = ""
    keyframes: list[Keyframe] = field(default_factory=list)
    decimals: int = 3
    step: float = 0.001
    minimum: float | None = None
    maximum: float | None = None
    display_min: float | None = None
    display_max: float | None = None

    def apply_precision(self, value: float) -> float:
        value = float(value)
        if self.minimum is not None:
            value = max(self.minimum, value)
        if self.maximum is not None:
            value = min(self.maximum, value)
        return float(round(value, self.decimals))

    def ensure_endpoints(self, frame_count: int, default_value: float = 0.0) -> None:
        last_frame = max(0, frame_count - 1)
        self._clamp_and_dedupe(frame_count)
        if not self.keyframes:
            value = self.apply_precision(default_value)
            self.keyframes = [Keyframe(0, value), Keyframe(last_frame, value)]
            return

        self.keyframes.sort(key=lambda item: item.frame)
        if self.keyframes[0].frame != 0:
            self.keyframes.insert(0, Keyframe(0, self.keyframes[0].value, self.keyframes[0].smooth))
        if self.keyframes[-1].frame != last_frame:
            self.keyframes.append(Keyframe(last_frame, self.keyframes[-1].value, self.keyframes[-1].smooth))
        self._clamp_and_dedupe(frame_count)

    def add_keyframe(self, frame: int, value: float, smooth: float = 0.0) -> int:
        target_frame = int(round(frame))
        keyframe = Keyframe(target_frame, self.apply_precision(value), smooth)
        for index, existing in enumerate(self.keyframes):
            if existing.frame == target_frame:
                self.keyframes[index] = keyframe
                self.keyframes.sort(key=lambda item: item.frame)
                return next(index for index, item in enumerate(self.keyframes) if item.frame == target_frame)
        self.keyframes.append(keyframe)
        self.keyframes.sort(key=lambda item: item.frame)
        return next(index for index, item in enumerate(self.keyframes) if item.frame == target_frame)

    def replace_keyframes(self, keyframes: list[Keyframe], frame_count: int, default_value: float = 0.0) -> None:
        self.keyframes = [Keyframe(item.frame, self.apply_precision(item.value), item.smooth) for item in keyframes]
        self.ensure_endpoints(frame_count, default_value)

    def delete_keyframe(self, index: int, frame_count: int) -> bool:
        if not 0 <= index < len(self.keyframes):
            return False
        frame = self.keyframes[index].frame
        if frame in {0, max(0, frame_count - 1)}:
            return False
        del self.keyframes[index]
        self.ensure_endpoints(frame_count)
        return True

    def _clamp_and_dedupe(self, frame_count: int) -> None:
        last_frame = max(0, frame_count - 1)
        by_frame: dict[int, Keyframe] = {}
        for keyframe in self.keyframes:
            frame = min(max(0, keyframe.frame), last_frame)
            by_frame[frame] = Keyframe(frame, self.apply_precision(keyframe.value), keyframe.smooth)
        self.keyframes = [by_frame[frame] for frame in sorted(by_frame)]


@dataclass
class VehicleSettings:
    gear_ratios: list[float] = field(default_factory=lambda: [3.5, 2.1, 1.4, 1.0, 0.82])
    final_ratio: float = 3.9
    wheel_radius_m: float = 0.33
    rpm_idle: float = 900.0
    rpm_redline: float = 7000.0


@dataclass
class ProjectSettings:
    fps: int = 25
    total_frames: int = 250
    parameters: list[CurveParameter] = field(default_factory=list)
    vehicle_settings: VehicleSettings = field(default_factory=VehicleSettings)
    speed_rpm_link_enabled: bool = True
    speed_rpm_link_source: str = "speed_kmh"
    auto_longitudinal_g: bool = True

    @property
    def frame_count(self) -> int:
        return max(1, int(round(self.total_frames)))

    @property
    def duration_seconds(self) -> float:
        return self.frame_count / self.fps

    @classmethod
    def create_default(
        cls,
        fps: int = 25,
        total_frames: int | None = None,
        duration_seconds: float | None = None,
    ) -> ProjectSettings:
        if total_frames is None:
            total_frames = int(round(fps * duration_seconds)) if duration_seconds is not None else 250
        project = cls(fps=fps, total_frames=total_frames)
        for spec in DEFAULT_PARAMETER_SPECS:
            name, unit, value, decimals, step, minimum, maximum, display_min, display_max = spec
            parameter = CurveParameter(
                name=name,
                unit=unit,
                decimals=decimals,
                step=step,
                minimum=minimum,
                maximum=maximum,
                display_min=display_min,
                display_max=display_max,
            )
            parameter.ensure_endpoints(project.frame_count, value)
            project.parameters.append(parameter)
        return project

    def set_fps(self, fps: int) -> None:
        if fps not in SUPPORTED_FPS:
            raise ValueError(f"不支持的帧率：{fps}")
        self.fps = fps
        self.ensure_parameter_endpoints()

    def set_total_frames(self, total_frames: int) -> None:
        if total_frames <= 0:
            raise ValueError("总帧数必须大于 0")
        self.total_frames = int(round(total_frames))
        self.ensure_parameter_endpoints()

    def set_duration(self, duration_seconds: float) -> None:
        if duration_seconds <= 0:
            raise ValueError("时长必须大于 0")
        self.set_total_frames(int(round(self.fps * duration_seconds)))

    def ensure_parameter_endpoints(self) -> None:
        defaults = {name: value for name, _unit, value, *_rest in DEFAULT_PARAMETER_SPECS}
        for parameter in self.parameters:
            parameter.ensure_endpoints(self.frame_count, defaults.get(parameter.name, 0.0))

    def get_parameter(self, name: str) -> CurveParameter | None:
        return next((parameter for parameter in self.parameters if parameter.name == name), None)

    def add_parameter(self, name: str, unit: str = "", initial_value: float = 0.0) -> CurveParameter:
        if not name.strip():
            raise ValueError("参数名不能为空")
        if self.get_parameter(name):
            raise ValueError(f"参数已存在：{name}")
        parameter = CurveParameter(name.strip(), unit.strip())
        parameter.ensure_endpoints(self.frame_count, initial_value)
        self.parameters.append(parameter)
        return parameter

    def is_derived(self, parameter_name: str) -> bool:
        return parameter_name == "longitudinal_g" and self.auto_longitudinal_g


def create_parameter_from_name(name: str, unit: str = "") -> CurveParameter:
    for spec in DEFAULT_PARAMETER_SPECS:
        spec_name, spec_unit, _value, decimals, step, minimum, maximum, display_min, display_max = spec
        if spec_name == name:
            return CurveParameter(
                name=name,
                unit=unit or spec_unit,
                decimals=decimals,
                step=step,
                minimum=minimum,
                maximum=maximum,
                display_min=display_min,
                display_max=display_max,
            )
    return CurveParameter(name=name, unit=unit)
