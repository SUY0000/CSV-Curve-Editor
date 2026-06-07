from __future__ import annotations

import csv

from csv_curve_editor.csv_io import export_csv, project_to_rows
from csv_curve_editor.models import ProjectSettings


def test_project_to_rows_matches_fps_and_duration() -> None:
    project = ProjectSettings.create_default(fps=25, duration_seconds=10.0)
    rows = project_to_rows(project)

    assert len(rows) == 250
    assert rows[0]["frame"] == 0
    assert rows[-1]["frame"] == 249


def test_export_csv_has_default_columns(tmp_path) -> None:
    project = ProjectSettings.create_default(fps=60, duration_seconds=1.0)
    path = tmp_path / "curve.csv"

    export_csv(project, path)

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    assert len(rows) == 60
    assert reader.fieldnames == [
        "frame",
        "time_seconds",
        "speed_kmh",
        "rpm",
        "gear",
        "longitudinal_g",
        "lateral_g",
    ]


def test_custom_parameter_is_exported() -> None:
    project = ProjectSettings.create_default(fps=24, duration_seconds=1.0)
    project.add_parameter("boost", "bar", 1.5)
    rows = project_to_rows(project)

    assert len(rows) == 24
    assert rows[0]["boost"] == 1.5
