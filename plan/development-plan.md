# CSV 曲线编辑器开发计划

## 目标

从零实现一个简洁的桌面图形化 CSV 曲线编辑器，用于影视车拍后期制作中的时速表、G 值表等 UI 特效数据生成。

## 技术方案

采用 Python + PySide6 + pyqtgraph。核心计算和 CSV 处理使用标准库实现，降低依赖复杂度；GUI 只负责交互展示。

## 第一版功能

1. 支持 24、25、30、50、60、120fps，并按帧率与时长生成 CSV 行数。
2. 默认参数：`speed_kmh`、`rpm`、`gear`、`longitudinal_g`、`lateral_g`。
3. 支持自定义参数。
4. 通过 gear ratio、final ratio、wheel radius 从时速和档位推导 rpm。
5. 通过时速差分反推纵向 G 值。
6. 支持曲线关键帧新增、拖动、删除和 smooth 平滑参数。
7. 支持 CSV 导入导出。

## 实施文件

```text
requirements.txt
src/csv_curve_editor/main.py
src/csv_curve_editor/models.py
src/csv_curve_editor/calculations.py
src/csv_curve_editor/interpolation.py
src/csv_curve_editor/csv_io.py
src/csv_curve_editor/curve_editor.py
src/csv_curve_editor/vehicle_settings.py
src/csv_curve_editor/main_window.py
tests/test_calculations.py
tests/test_interpolation.py
tests/test_csv_io.py
```

## 验证

- 运行 `pytest` 验证计算、插值和 CSV。
- 运行 `PYTHONPATH=src python -m csv_curve_editor.main` 启动 GUI。
- 手动新建 25fps、10秒项目，导出 CSV 后确认 250 行、列完整、rpm 与纵向 G 可自动推导。
