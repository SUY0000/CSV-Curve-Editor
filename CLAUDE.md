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

这是一个影视车拍后期用的桌面 CSV 曲线编辑器，用于生成每帧一行的 UI 特效数据。默认支持 `speed_kmh`、`rpm`、`gear`、`longitudinal_g`、`lateral_g`，并允许新增自定义参数。CSV 基础列为 `frame` 和影视时间码 `timecode`（`HH:MM:SS:FF`）。时速和转速可双向绑定；`rpm`、`gear` 等参数按各自精度编辑和导出。

## 架构概览

- `src/csv_curve_editor/main.py` 是 GUI 入口，创建 `QApplication` 并显示 `MainWindow`。
- `src/csv_curve_editor/main_window.py` 是主窗口和应用状态协调层：持有一个 `ProjectSettings`，管理帧率、时长、参数列表、CSV 打开/导出、自动派生开关和车辆设置对话框。
- `src/csv_curve_editor/models.py` 定义核心数据模型：
  - `ProjectSettings`：帧率、时长、参数集合、车辆设置、时速/转速绑定状态、自动纵向 G 开关。
  - `CurveParameter`：一个 CSV 参数列及其关键帧、数值精度、显示范围。
  - `Keyframe`：`frame`、`value`、`smooth`。
  - `VehicleSettings`：gear ratios、final ratio、wheel radius、RPM 范围。
- `src/csv_curve_editor/interpolation.py` 负责把关键帧采样为逐帧数值。`smooth=0` 为线性；`smooth>0` 用 smoothstep 与线性插值混合。
- `src/csv_curve_editor/calculations.py` 只放纯计算：速度/轮速/RPM 换算，以及由时速差分计算纵向 G；纵向 G 的中间帧使用中心差分，头尾帧使用前向/后向差分。
- `src/csv_curve_editor/binding.py` 实现时速/转速双向绑定和关联关键帧同步：最近编辑的 `speed_kmh` 或 `rpm` 作为源，另一方按当前 `gear`、gear ratios、final ratio、wheel radius 重建关键帧；`speed_kmh`、`rpm`、`gear`、`longitudinal_g` 新增、移动、删除中间关键帧时会同步到其它关联参数，同帧关联关键帧的 `smooth` 也会同步。
- `src/csv_curve_editor/csv_io.py` 是导入导出和整项目采样层：
  - `sample_project()` 插值所有参数并应用参数精度，再在自动模式下覆盖 `longitudinal_g` 的派生值；自动纵向 G 使用 `speed_kmh` 的原始插值值计算，避免先按 0.1km/h 精度量化后再求导造成阶梯抖动。
  - `project_to_rows()` 生成每帧一行的导出数据。
  - `import_csv()` 会把已有 CSV 每行作为关键帧导入；当前没有曲线拟合或稀疏化步骤。
- `src/csv_curve_editor/curve_editor.py` 封装 pyqtgraph 曲线交互：双击添加关键帧、拖动关键帧、选中关键帧。支持一个活动编辑参数和多个勾选叠加显示参数；多参数叠加时按各自 Y 范围归一化。Y 轴范围写回不要使用 `pyqtgraph.sigRangeChanged`，该信号会被启动初始化和程序化 `setYRange()` 触发；当前只在用户鼠标释放拖动画布或滚轮缩放后读取 ViewBox 范围并同步到 `Y Min / Y Max`。
- `src/csv_curve_editor/vehicle_settings.py` 是车辆传动设置对话框，直接更新 `ProjectSettings.vehicle_settings` 内的数据。

## 关键数据流

1. 用户在 `MainWindow` 修改帧率、时长或参数关键帧。
2. `ProjectSettings.ensure_parameter_endpoints()` 保证每个参数有首尾关键帧，且头尾关键帧不可删除。
3. `binding.align_linked_keyframes()` / `move_linked_keyframes()` / `delete_linked_keyframes()` 让 `speed_kmh`、`rpm`、`gear`、`longitudinal_g` 的中间关键帧同帧新增、移动、删除，并同步同帧 `smooth`。
4. 若时速/转速绑定开启，`binding.sync_speed_rpm()` 根据最近编辑源同步另一方；`speed_kmh`、`rpm`、`gear` 变化都会触发同步。
5. `CurveEditor.refresh()` 显示当前活动参数和勾选叠加参数；多参数叠加时只改变显示比例，不改变真实 CSV 数值。默认 `speed_kmh` 显示范围为 `0–300`，不要让启动时 pyqtgraph 对全 0 曲线的默认 `-0.5–0.5` 范围写回覆盖参数显示范围。
6. 导出 CSV 时，`export_csv()` → `project_to_rows()` → `sample_project()`，因此导出的数值会应用参数精度，`longitudinal_g` 会反映自动派生开关状态。

## 测试结构

- `tests/test_calculations.py` 覆盖车辆传动换算与纵向 G 计算。
- `tests/test_binding.py` 覆盖时速/转速双向绑定和 gear 变化同步。
- `tests/test_interpolation.py` 覆盖线性和平滑插值。
- `tests/test_csv_io.py` 覆盖帧数、默认列、自定义参数导出和整数精度导出。

修改绑定逻辑、参数精度、派生曲线、CSV 列结构或插值规则时，优先更新对应测试文件。
