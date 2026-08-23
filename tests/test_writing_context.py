from __future__ import annotations

import json
from pathlib import Path

from research_agent_platform.agent import ResearchAgentService
from research_agent_platform.publication_quality import build_writing_context

from .conftest import run


def test_write_emits_structured_writing_context(service: ResearchAgentService):
    session = service.store.create_session()
    root = Path(session.workspace_root)
    source = root / "plan" / "objective.md"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("AI method objective", encoding="utf-8")
    service.store.save_session(session)

    result = run(service.chat(session.session_id, "/write --source workspace 中文 AI 论文"))
    task = service.get_task(result["task_id"])

    assert result["status"] == "completed"
    assert task.workflow_mode == "research_materials_writing"
    context = json.loads(Path(task.artifact_root, "Content/WRITING_CONTEXT.json").read_text())
    assert context["schema_version"] == "writing-context/v1"
    assert context["discipline"] == "ai_computer_science"
    assert context["language"] == "zh"
    writing_package = json.loads(Path(task.artifact_root, "Content/WRITING_PACKAGE.json").read_text())
    manuscript_context = json.loads(Path(task.artifact_root, "Content/MANUSCRIPT_CONTEXT.json").read_text())
    assert writing_package["source_ids"] == ["plan/objective.md"]
    assert manuscript_context["writing_package_id"] == writing_package["package_id"]
    final_gate = json.loads(Path(task.artifact_root, "paper/FINAL_GATE_REPORT.json").read_text())
    assert final_gate["decision"] in {"PASS", "REVISE", "BLOCK"}
    contracts = json.loads(Path(task.artifact_root, "paper/PARAGRAPH_CONTRACTS.json").read_text())
    assert contracts[0]["section"] == "Abstract"
    assert all(contract["author_input_needed"] for contract in contracts)


def test_write_resolves_environmental_discipline_for_rubric(service: ResearchAgentService):
    session = service.store.create_session()
    root = Path(session.workspace_root)
    source = root / "results" / "summary.md"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("Nitrate concentration was measured in mg N/L.", encoding="utf-8")

    result = run(service.chat(session.session_id, "/write --source workspace 环境科学论文"))
    task = service.get_task(result["task_id"])

    context = json.loads(Path(task.artifact_root, "Content/WRITING_CONTEXT.json").read_text())
    evaluation = json.loads(
        Path(task.artifact_root, "Content/WRITING_EVALUATION_REPORT.json").read_text()
    )
    assert context["discipline"] == "environmental_science_engineering"
    assert evaluation["rubric"]["discipline"] == "environmental_science_engineering"


def test_writing_context_detects_explicit_section_role():
    context = build_writing_context("润色中文论文的研究方法部分", [], {})

    assert context["section_role"]["role"] == "methods"
    assert context["section_role"]["confidence"] == "medium"
