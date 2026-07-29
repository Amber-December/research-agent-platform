from __future__ import annotations

import asyncio
import io
import json
from pathlib import Path

from openpyxl import Workbook
from PIL import Image

from research_agent_platform import agent as agent_module
from research_agent_platform.figure_pipeline import render_code_figure
from research_agent_platform.models import ArtifactRecord, TaskRun, UploadBatchRecord
from research_agent_platform.router.intent import explicit_route
from research_agent_platform.upstream import GeneratedImage


def test_fig_routes_explicitly():
    route = explicit_route("/fig 根据数据生成图")

    assert route is not None
    assert route.command == "/fig"


def test_csv_category_and_value_generates_bar_chart(tmp_path: Path):
    source = tmp_path / "Content" / "uploads" / "results.csv"
    source.parent.mkdir(parents=True)
    source.write_text("method,accuracy\nbaseline,0.81\nours,0.92\n", encoding="utf-8")

    result = render_code_figure(tmp_path, objective="/fig 模型准确率")

    assert result.chart_type == "bar"
    assert result.source_ref == "Content/uploads/results.csv"
    assert result.png_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    assert b"<svg" in result.svg_bytes[:500]


def test_two_numeric_columns_generate_scatter_chart(tmp_path: Path):
    source = tmp_path / "figures" / "uploads" / "measurements.tsv"
    source.parent.mkdir(parents=True)
    source.write_text("rainfall\trunoff\n10\t3\n20\t8\n30\t15\n", encoding="utf-8")

    result = render_code_figure(tmp_path)

    assert result.chart_type == "scatter"
    assert result.x_column == "rainfall"
    assert result.y_columns == ["runoff"]


def test_xlsx_time_series_generates_line_chart(tmp_path: Path):
    source = tmp_path / "paper" / "uploads" / "experiment.xlsx"
    source.parent.mkdir(parents=True)
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "metrics"
    worksheet.append(["epoch", "loss", "accuracy"])
    worksheet.append([1, 0.8, 0.6])
    worksheet.append([2, 0.5, 0.76])
    worksheet.append([3, 0.3, 0.86])
    workbook.save(source)

    result = render_code_figure(tmp_path)

    assert result.chart_type == "line"
    assert result.sheet_name == "metrics"
    assert result.y_columns == ["loss", "accuracy"]


def test_figure_workflow_uses_code_for_valid_uploaded_data(service, monkeypatch):
    session = service.store.create_session()
    source = Path(session.workspace_root, "Content", "uploads", "results.csv")
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("method,score\nA,0.7\nB,0.9\n", encoding="utf-8")
    session.upload_batches.append(
        UploadBatchRecord(relative_paths=["Content/uploads/results.csv"])
    )
    service.store.save_session(session)

    async def unexpected_generate_image(**kwargs):
        raise AssertionError("Image-2 must not render precise tabular data")

    monkeypatch.setattr(agent_module, "generate_image", unexpected_generate_image)
    result = asyncio.run(service.chat(session.session_id, "/fig ?????"))

    assert result["status"] == "completed"
    manifest_path = Path(session.workspace_root, "figures", "generated", "FIGURE_DELIVERY.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["mode"] == "code"
    assert Path(session.workspace_root, "figures", "generated", "FIGURE_01.png").exists()


def test_figure_workflow_falls_back_to_image2_without_data(service):
    result = asyncio.run(service.chat(None, "/fig ???????????"))

    assert result["status"] == "completed"
    task = service.get_task(result["task_id"])
    assert task is not None
    manifest = json.loads(
        Path(task.artifact_root, "figures", "generated", "FIGURE_DELIVERY.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["mode"] == "image2"
    assert manifest["model"] == "gpt-image-2"
