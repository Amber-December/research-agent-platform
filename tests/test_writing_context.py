from __future__ import annotations

import json
from pathlib import Path

from research_agent_platform.agent import ResearchAgentService

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
    context = json.loads(Path(task.artifact_root, "Content/WRITING_CONTEXT.json").read_text())
    assert context["schema_version"] == "writing-context/v1"
    assert context["discipline"] == "ai"
    assert context["language"] == "zh"
