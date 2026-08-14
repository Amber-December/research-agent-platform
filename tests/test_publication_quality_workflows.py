from __future__ import annotations

import json
from pathlib import Path

from research_agent_platform.agent import ResearchAgentService

from .conftest import run


def _manuscript(session) -> None:
    root = Path(session.workspace_root)
    path = root / "paper" / "uploads" / "paper.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# Test Paper\n\n## Abstract\nText.\n\n## Introduction\nContext [@known].\n\n## Method\nMethod.\n\n## Limitations\nBounded.\n\n## Conclusion\nDone.",
        encoding="utf-8",
    )
    bib = root / "bib" / "uploads" / "references.bib"
    bib.parent.mkdir(parents=True, exist_ok=True)
    bib.write_text("@article{known,title={Known}}", encoding="utf-8")


def test_peer_review_writes_structured_simulated_package(service: ResearchAgentService):
    session = service.store.create_session()
    _manuscript(session)
    result = run(service.chat(session.session_id, "/peer-review"))
    task = service.get_task(result["task_id"])

    assert result["status"] == "completed"
    payload = json.loads(Path(task.artifact_root, "rebuttal/reviews/REVIEW_PACKAGE.json").read_text())
    assert payload["review_mode"] == "simulated-peer-review"
    assert payload["decision"] in {"PASS", "REVISE"}


def test_peer_review_accepts_generic_uploaded_markdown(service: ResearchAgentService):
    session = service.store.create_session()
    root = Path(session.workspace_root)
    manuscript = root / "Content" / "uploads" / "uploaded-paper.md"
    manuscript.parent.mkdir(parents=True, exist_ok=True)
    manuscript.write_text(
        "# Uploaded Paper\n\n## Abstract\nText.\n\n## Introduction\nContext.\n\n## Method\nMethod.\n\n## Conclusion\nDone.",
        encoding="utf-8",
    )

    result = run(service.chat(session.session_id, "/peer-review"))

    assert result["status"] == "completed"


def test_final_check_blocks_unknown_citation(service: ResearchAgentService):
    session = service.store.create_session()
    _manuscript(session)
    path = Path(session.workspace_root, "paper/uploads/paper.md")
    path.write_text(path.read_text(encoding="utf-8").replace("@known", "@unknown"), encoding="utf-8")
    result = run(service.chat(session.session_id, "/final-check"))
    task = service.get_task(result["task_id"])
    payload = json.loads(Path(task.artifact_root, "paper/FINAL_GATE_REPORT.json").read_text())

    assert result["status"] == "completed"
    assert payload["decision"] == "BLOCK"
