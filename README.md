# CSV Curve Editor

影视车拍后期用图形化 CSV 曲线编辑器，用于制作时速表、转速表、档位和 G 值等 UI 特效数据。

## 功能

- 支持 24、25、30、50、60、120fps。
- 根据帧率和时长生成每帧一行的 CSV。
- 默认参数：`speed_kmh`、`rpm`、`gear`、`longitudinal_g`、`lateral_g`。
- 支持新增自定义参数。
- 可设置 gear ratio、final ratio、wheel radius，用时速和档位推导 RPM。
- 可根据时速曲线自动反推纵向 G 值。
- 支持双击添加关键帧、拖动关键帧、编辑 smooth 平滑程度。
- 支持 CSV 导入导出。

## 安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 启动

```bash
PYTHONPATH=src python -m csv_curve_editor.main
```

## 测试

```bash
PYTHONPATH=src pytest
```

## 使用建议

1. 先选择帧率和时长。
2. 编辑 `speed_kmh` 与 `gear` 曲线。
3. 在“车辆设置”里输入 gear ratios、final ratio、wheel radius。
4. 保持“RPM 自动绑定”和“纵向 G 自动计算”开启。
5. 导出 CSV 给后期 UI 特效使用。
