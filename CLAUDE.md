# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 常用命令

本项目使用 Conda 管理开发环境；当前没有 `pyproject.toml` 或安装包配置，运行源码和测试时需要设置 `PYTHONPATH=src`。

```bash
# 创建并启用 Conda 环境
conda env create -f environment.yml
conda activate csv-curve-editor

# 已有环境时同步依赖
conda env update -f environment.yml --prune
conda activate csv-curve-editor

# 启动 GUI
PYTHONPATH=src python -m csv_curve_editor.main

# 运行全部测试
PYTHONPATH=src pytest

# 运行单个测试文件
PYTHONPATH=src pytest tests/test_calculations.py

# 运行单个测试用例
PYTHONPATH=src pytest tests/test_calculations.py::test_speed_engine_rpm_roundtrip

# Python 语法/导入编译检查
PYTHONPATH=src python -m compileall src
```

当前依赖在 `environment.yml` 中维护，主要包括 `PySide6`、`pyqtgraph`、`pytest`；没有配置专门的 lint 或 formatter 命令。

## 项目定位

这是一个影视车拍后期用的桌面 CSV 曲线编辑器，用于生成每帧一行的 UI 特效数据。默认支持 `speed_kmh`、`rpm`、`gear`、`longitudinal_g`、`lateral_g`、`throttle_pct`、`brake_pct`、`oil_temp_c`，并允许新增自定义参数。CSV 基础列为 `frame` 和影视时间码 `timecode`（`HH:MM:SS:FF`）。`rpm` 可由 `speed_kmh` 和 `gear` 单向自动派生；`rpm`、`gear` 等参数按各自精度编辑和导出。

## 架构概览

- `src/csv_curve_editor/main.py` 是 GUI 入口，创建 `QApplication` 并显示 `MainWindow`。
- `src/csv_curve_editor/main_window.py` 是主窗口和应用状态协调层：持有一个 `ProjectSettings`，管理帧率、时长、参数列表、CSV 打开/导出、自动派生开关和车辆设置对话框。
- `src/csv_curve_editor/models.py` 定义核心数据模型：
  - `ProjectSettings`：帧率、总帧数、参数集合、车辆设置、RPM 自动派生开关、自动纵向 G 开关。
  - `CurveParameter`：一个 CSV 参数列及其关键帧、数值精度、显示范围，以及每参数独立的导出抖动设置。
  - `JitterSettings`：导出抖动配置（启用、幅度、周期、细节、Seed、相对幅度、参与派生）。
  - `Keyframe`：`frame`、`value`、`smooth`。
  - `VehicleSettings`：gear ratios、final ratio、wheel radius、RPM 范围。
- `src/csv_curve_editor/interpolation.py` 负责把关键帧采样为逐帧数值。`smooth=0` 为线性；`smooth>0` 在线性插值和基于相邻关键帧切线的三次 Hermite/PCHIP 风格插值之间混合，以减少关键帧处锐角；局部峰值/谷值会把切线压到 0，避免明显过冲。`Keyframe.smooth` 和新打关键帧默认都是 `1.0`，CSV 导入未显式 smooth 时也使用默认平滑。
- `src/csv_curve_editor/calculations.py` 只放纯计算：速度/轮速/RPM 换算，以及由时速差分计算纵向 G；自动 RPM 计算允许传入浮点挡位，并在相邻 gear ratio 间插值；纵向 G 的中间帧使用中心差分，头尾帧使用前向/后向差分。
- `src/csv_curve_editor/jitter.py` 负责导出抖动：使用确定性带限平滑随机噪声 / fractal value noise，避免逐帧白噪声；同一 Seed 导出稳定。
- `src/csv_curve_editor/csv_io.py` 是导入导出和整项目采样层：
  - `sample_project(apply_export_jitter=True)` 插值所有参数并应用参数精度，导出时对开启抖动的普通参数叠加 jitter，再在自动模式下覆盖 `rpm` 和 `longitudinal_g` 的派生值；自动派生参数自身在自动模式下不应用抖动；源参数默认不影响派生，只有开启 `jitter.affects_derived`/“参与派生”时才用抖动后的源值参与 `rpm`/`longitudinal_g` 计算。`gear` 自身采样为前值保持的整数阶梯，换挡点位于目标挡位关键帧；自动 RPM 由 `speed_kmh`、`gear` 原始插值值、gear ratios、final ratio、wheel radius 单向计算，因此关键帧之间的浮点挡位可让转速回落渐变；自动纵向 G 默认使用 `speed_kmh` 的原始插值值计算，避免先按 0.1km/h 精度量化后再求导造成阶梯抖动。
  - `project_to_rows()` 生成每帧一行的导出数据。
  - `import_csv()` 会把已有 CSV 每行作为关键帧导入；当前没有曲线拟合或稀疏化步骤。
- `src/csv_curve_editor/curve_editor.py` 封装 pyqtgraph 曲线交互：双击添加关键帧、拖动关键帧、选中关键帧。左侧“多选显示”默认关闭时仅显示当前参数；开启后可勾选多个参数叠加显示，多参数叠加时按各自 Y 范围归一化。编辑器调用 `sample_project(..., apply_export_jitter=False)` 保持主曲线不被导出抖动影响；开启抖动时用虚线显示导出预览。Y 轴范围写回不要使用 `pyqtgraph.sigRangeChanged`，该信号会被启动初始化和程序化 `setYRange()` 触发；当前只在用户鼠标释放拖动画布或滚轮缩放后读取 ViewBox 范围并同步到 `Y Min / Y Max`。
- `src/csv_curve_editor/vehicle_settings.py` 是车辆传动设置对话框，点 OK 后更新 `ProjectSettings.vehicle_settings`；弹窗支持应用、保存、删除车辆预设。
- `src/csv_curve_editor/vehicle_presets.py` 负责本机车辆预设 JSON 读写，路径为 `~/.csv_curve_editor_vehicle_presets.json`；预设只保存 `VehicleSettings`，不保存曲线参数或关键帧。

## 关键数据流

1. 用户在 `MainWindow` 修改帧率、总帧数或参数关键帧。
2. `ProjectSettings.ensure_parameter_endpoints()` 保证每个参数有首尾关键帧，且头尾关键帧不可删除。
3. `CurveEditor.refresh()` 显示当前活动参数和勾选叠加参数；多参数叠加时只改变显示比例，不改变真实 CSV 数值。默认 `speed_kmh` 显示范围为 `0–300`，不要让启动时 pyqtgraph 对全 0 曲线的默认 `-0.5–0.5` 范围写回覆盖参数显示范围。
4. 导出 CSV 时，`export_csv()` → `project_to_rows()` → `sample_project()`，因此导出的数值会应用参数精度和每参数导出抖动，`rpm` 和 `longitudinal_g` 会反映各自自动派生开关状态；抖动默认不参与派生，除非源参数开启“参与派生”。

## 测试结构

- `tests/test_calculations.py` 覆盖车辆传动换算与纵向 G 计算。
- `tests/test_rpm_auto_sync.py` 覆盖 RPM 单向自动派生。
- `tests/test_interpolation.py` 覆盖线性和平滑插值。
- `tests/test_csv_io.py` 覆盖帧数、默认列、自定义参数导出、整数精度导出，以及导出抖动与自动派生交互。
- `tests/test_jitter.py` 覆盖导出抖动的开关、Seed 稳定性、平滑性和范围 clamp。
- `tests/test_vehicle_presets.py` 覆盖车辆预设保存、覆盖、删除和损坏 JSON 容错。

修改参数精度、派生曲线、CSV 列结构、插值规则、导出抖动或车辆预设读写时，优先更新对应测试文件。
