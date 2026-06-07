# CSV Curve Editor

影视车拍后期用图形化 CSV 曲线编辑器，用于制作时速表、转速表、档位和 G 值等 UI 特效数据。

## 功能

- 支持 24、25、30、50、60、120fps。
- 根据帧率和总帧数生成每帧一行的 CSV。
- 默认参数：`speed_kmh`、`rpm`、`gear`、`longitudinal_g`、`lateral_g`。
- 支持新增自定义参数。
- 可设置 gear ratio、final ratio、wheel radius，由时速和挡位自动派生转速。
- 可根据时速曲线自动反推纵向 G 值。
- 支持双击添加关键帧、拖动关键帧、编辑 smooth 平滑程度；头尾关键帧不可删除。
- `rpm`、`gear` 等参数支持按各自精度编辑和导出。
- 支持勾选多个参数叠加到同一张图表；多参数显示时会按各自 Y 范围归一化，避免曲线被比例压扁。
- 支持 CSV 导入导出。

## 安装

本项目使用 Conda 管理开发环境。

```bash
conda env create -f environment.yml
conda activate csv-curve-editor
```

如果环境已经存在，使用下面的命令同步依赖：

```bash
conda env update -f environment.yml --prune
conda activate csv-curve-editor
```

## 启动

```bash
PYTHONPATH=src python -m csv_curve_editor.main
```

## 测试

```bash
PYTHONPATH=src pytest
```

运行单个测试文件：

```bash
PYTHONPATH=src pytest tests/test_calculations.py
```

运行单个测试用例：

```bash
PYTHONPATH=src pytest tests/test_calculations.py::test_speed_engine_rpm_roundtrip
```

## 使用建议

1. 先选择帧率和总帧数。
2. 保持“RPM 自动绑定”开启时，编辑 `speed_kmh` 和 `gear` 会在导出/采样时自动派生 `rpm`；关闭后可手动编辑 `rpm`。
3. 编辑 `gear` 曲线，并在“车辆设置”里输入 gear ratios、final ratio、wheel radius。
4. 保持“纵向 G 自动计算”开启，让 `longitudinal_g` 随时速自动更新。
5. 在参数列表中勾选多个参数可叠加显示，选中的行是当前可编辑参数。
6. 使用 `Y Min / Y Max` 手动控制当前参数的显示范围；也可以直接拖动/缩放图表的 Y 轴，输入框会同步更新。多参数叠加时，各参数按自己的 Y 范围归一化显示。
7. 导出 CSV 给后期 UI 特效使用。
