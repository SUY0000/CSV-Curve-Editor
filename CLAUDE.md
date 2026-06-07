# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 常用命令

本项目当前没有 `pyproject.toml` 或安装包配置，运行源码和测试时需要设置 `PYTHONPATH=src`。

```bash
# 创建并启用虚拟环境
python -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

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

当前依赖只有 `PySide6`、`pyqtgraph`、`pytest`；没有配置专门的 lint 或 formatter 命令。

## 项目定位

这是一个影视车拍后期用的桌面 CSV 曲线编辑器，用于生成每帧一行的 UI 特效数据。默认支持 `speed_kmh`、`rpm`、`gear`、`longitudinal_g`、`lateral_g`，并允许新增自定义参数。CSV 基础列为 `frame` 和 `time_seconds`。

## 架构概览

- `src/csv_curve_editor/main.py` 是 GUI 入口，创建 `QApplication` 并显示 `MainWindow`。
- `src/csv_curve_editor/main_window.py` 是主窗口和应用状态协调层：持有一个 `ProjectSettings`，管理帧率、时长、参数列表、CSV 打开/导出、自动派生开关和车辆设置对话框。
- `src/csv_curve_editor/models.py` 定义核心数据模型：
  - `ProjectSettings`：帧率、时长、参数集合、车辆设置、自动 RPM / 自动纵向 G 开关。
  - `CurveParameter`：一个 CSV 参数列及其关键帧。
  - `Keyframe`：`frame`、`value`、`smooth`。
  - `VehicleSettings`：gear ratios、final ratio、wheel radius、RPM 范围。
- `src/csv_curve_editor/interpolation.py` 负责把关键帧采样为逐帧数值。`smooth=0` 为线性；`smooth>0` 用 smoothstep 与线性插值混合。
- `src/csv_curve_editor/calculations.py` 只放纯计算：速度/轮速/RPM 换算，以及由时速差分计算纵向 G。
- `src/csv_curve_editor/csv_io.py` 是导入导出和整项目采样层：
  - `sample_project()` 先插值所有参数，再在自动模式下覆盖 `rpm` 和 `longitudinal_g` 的派生值。
  - `project_to_rows()` 生成每帧一行的导出数据。
  - `import_csv()` 会把已有 CSV 每行作为关键帧导入；当前没有曲线拟合或稀疏化步骤。
- `src/csv_curve_editor/curve_editor.py` 封装 pyqtgraph 曲线交互：双击添加关键帧、拖动关键帧、选中关键帧。派生参数只读显示，并通过 `sample_project()` 展示实际派生曲线。
- `src/csv_curve_editor/vehicle_settings.py` 是车辆传动设置对话框，直接更新 `ProjectSettings.vehicle_settings` 内的数据。

## 关键数据流

1. 用户在 `MainWindow` 修改帧率、时长或参数关键帧。
2. `ProjectSettings.ensure_parameter_endpoints()` 保证每个参数有首尾关键帧，避免采样边界为空。
3. `CurveEditor.refresh()` 显示当前参数曲线；普通参数使用 `interpolate_keyframes()`，派生参数使用 `sample_project()` 的结果。
4. 导出 CSV 时，`export_csv()` → `project_to_rows()` → `sample_project()`，因此导出的 `rpm` 和 `longitudinal_g` 会反映自动派生开关的状态。

## 测试结构

- `tests/test_calculations.py` 覆盖车辆传动换算与纵向 G 计算。
- `tests/test_interpolation.py` 覆盖线性和平滑插值。
- `tests/test_csv_io.py` 覆盖帧数、默认列和自定义参数导出。

修改派生曲线、CSV 列结构或插值规则时，优先更新对应测试文件。