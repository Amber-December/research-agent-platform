from __future__ import annotations

import json
from pathlib import Path

from research_agent_platform import agent as agent_module
from research_agent_platform.agent import ResearchAgentService
from research_agent_platform.models import UploadBatchRecord
from research_agent_platform.rebuttal import resolve_rebuttal_source_config
from research_agent_platform.uploads import classify_upload

from .conftest import run


def _write_rebuttal_sources(session) -> tuple[Path, Path]:
    workspace = Path(session.workspace_root)
    paper = workspace / "paper" / "FINAL_PAPER.md"
    review = workspace / "rebuttal" / "uploads" / "reviewer_comments.txt"
    paper.parent.mkdir(parents=True, exist_ok=True)
    review.parent.mkdir(parents=True, exist_ok=True)
    paper.write_text(
        "# Completed Paper\n\n## Method\nWe use method A.\n\n## Experiments\nTable 2 reports accuracy.",
        encoding="utf-8",
    )
    review.write_text(
        "Reviewer 1, Comment 1: Please justify method A and add a robustness experiment.",
        encoding="utf-8",
    )
    session.upload_batches.append(
        UploadBatchRecord(relative_paths=["paper/FINAL_PAPER.md", "rebuttal/uploads/reviewer_comments.txt"])
    )
    return paper, review


def test_review_named_upload_routes_to_rebuttal():
    assert classify_upload("reviewer_comments.docx") == "rebuttal"
    assert classify_upload("审稿意见.pdf") == "rebuttal"
    assert classify_upload("final_paper.pdf") == "paper"


def test_rebuttal_source_set_uses_latest_uploaded_paper_and_review(service: ResearchAgentService):
    session = service.store.create_session()
    _write_rebuttal_sources(session)
    service.store.save_session(session)

    config = resolve_rebuttal_source_config(
        "/rebuttal 回复审稿人",
        Path(session.workspace_root),
        session.upload_batches,
    )

    assert config.paper_refs == ["paper/FINAL_PAPER.md"]
    assert config.review_refs == ["rebuttal/uploads/reviewer_comments.txt"]
    assert config.upload_batch_ids == [session.upload_batches[-1].upload_batch_id]


def test_rebuttal_requires_completed_paper(service: ResearchAgentService):
    session = service.store.create_session()
    review = Path(session.workspace_root, "rebuttal", "uploads", "reviewer_comments.txt")
    review.parent.mkdir(parents=True, exist_ok=True)
    review.write_text("Reviewer 1: Clarify the method.", encoding="utf-8")
    session.upload_batches.append(
        UploadBatchRecord(relative_paths=["rebuttal/uploads/reviewer_comments.txt"])
    )
    service.store.save_session(session)

    result = run(service.chat(session.session_id, "/rebuttal 回复审稿意见"))

    assert result["status"] == "failed"
    assert "完成后的论文" in result["text"]
    assert result["checkpoint"] is None


def test_rebuttal_requires_reviewer_comments(service: ResearchAgentService):
    session = service.store.create_session()
    paper = Path(session.workspace_root, "paper", "FINAL_PAPER.md")
    paper.parent.mkdir(parents=True, exist_ok=True)
    paper.write_text("# Completed Paper", encoding="utf-8")
    session.upload_batches.append(UploadBatchRecord(relative_paths=["paper/FINAL_PAPER.md"]))
    service.store.save_session(session)

    result = run(service.chat(session.session_id, "/rebuttal 回复审稿意见"))

    assert result["status"] == "failed"
    assert "审稿人意见" in result["text"]
    assert result["checkpoint"] is None


def test_rebuttal_does_not_treat_intermediate_paper_artifact_as_completed_paper(
    service: ResearchAgentService,
):
    session = service.store.create_session()
    plan = Path(session.workspace_root, "paper", "PAPER_PLAN.md")
    review = Path(session.workspace_root, "rebuttal", "uploads", "reviewer_comments.txt")
    plan.parent.mkdir(parents=True, exist_ok=True)
    review.parent.mkdir(parents=True, exist_ok=True)
    plan.write_text("# Paper Plan", encoding="utf-8")
    review.write_text("Reviewer 1: Clarify the method.", encoding="utf-8")
    service.store.save_session(session)

    result = run(service.chat(session.session_id, "/rebuttal 回复审稿意见"))

    assert result["status"] == "failed"
    assert "完成后的论文" in result["text"]


def test_rebuttal_maps_comments_to_paper_and_runs_without_routine_checkpoint(
    service: ResearchAgentService, monkeypatch
):
    session = service.store.create_session()
    _write_rebuttal_sources(session)
    service.store.save_session(session)
    prompts: list[str] = []

    async def generate_rebuttal(*, system_prompt, user_prompt, model=None, temperature=0.3):
        prompts.append(user_prompt)
        if "Current stage: Review to Paper Map" in user_prompt:
            return (
                "# Review to Paper Map\n\n"
                "## Reviewer and Comment Index\n- R1.C1 robustness\n\n"
                "## Comment to Section Map\n- R1.C1 -> Experiments\n\n"
                "## Claim and Evidence Map\n- Current claim: Table 2 reports accuracy.\n\n"
                "## Figure and Table Map\n- R1.C1 -> Table 2\n\n"
                "## Unaddressed Evidence Gaps\n- Robustness experiment missing.\n\n"
                "## Traceability Checks\n- R1.C1 mapped to Experiments and Table 2."
            )
        if "Current stage: Response Strategy" in user_prompt:
            return (
                "# Response Strategy\n\n## Strategy by Comment\n- R1.C1: accept and add robustness.\n\n"
                "## Accepted and Partially Accepted Points\n- R1.C1 accepted.\n\n"
                "## Clarifications and Evidence-Based Disagreements\n- None.\n\n"
                "## New Experiments or Analysis\n- Robustness evaluation.\n\n"
                "## Risks and Dependencies\n- Compute availability.\n\n## Decision Required\nNone."
            )
        if "Current stage: Revised Manuscript" in user_prompt:
            return (
                "# Revised Paper\n\n## Abstract\nUpdated.\n\n## Introduction\nContext.\n\n"
                "## Method\nMethod A is justified.\n\n## Experiments or Results\nTable 2 reports accuracy.\n\n"
                "## Limitations\nRobustness remains planned.\n\n## Conclusion\nBounded conclusion.\n\n"
                "## References\nExisting references.\n\n## Unresolved Author Inputs\n- R1.C1 robustness experiment."
            )
        if "Current stage: Revision Ledger" in user_prompt:
            return (
                "# Revision Ledger\n\n## Coverage Summary\n- R1.C1 covered.\n\n"
                "## Comment Revision Ledger\n- R1.C1 | Status: planned | Experiments | robustness promised.\n\n"
                "## Implemented Changes\n- R1.C1 method clarification.\n\n## Planned Changes\n- R1.C1 robustness.\n\n"
                "## Unresolved Changes\n- None.\n\n## Author Verification\n- Verify R1.C1."
            )
        return "# Rebuttal Artifact\n\n- R1.C1 remains traceable to Experiments and Table 2."

    monkeypatch.setattr(agent_module, "generate_text", generate_rebuttal)
    result = run(service.chat(session.session_id, "/rebuttal 回复审稿人"))
    task = service.get_task(result["task_id"])

    assert result["status"] == "completed"
    assert result["checkpoint"] is None
    assert task is not None and task.rebuttal_source is not None
    assert Path(task.artifact_root, "rebuttal", "REBUTTAL_INPUTS.md").exists()
    mapping = Path(task.artifact_root, "rebuttal", "REVIEW_TO_PAPER_MAP.md").read_text(encoding="utf-8")
    assert "R1.C1 -> Experiments" in mapping
    selection = json.loads(
        Path(task.artifact_root, "Content", "REBUTTAL_SOURCE_SELECTION.json").read_text(encoding="utf-8")
    )
    assert selection["paper_files_read"] == ["paper/FINAL_PAPER.md"]
    assert selection["review_files_read"] == ["rebuttal/uploads/reviewer_comments.txt"]
    assert any("## Method" in prompt and "Reviewer 1, Comment 1" in prompt for prompt in prompts)
    assert Path(task.artifact_root, "paper", "PAPER_REVISED_AFTER_REVIEW.md").exists()
    assert Path(task.artifact_root, "rebuttal", "REVISION_LEDGER.md").exists()
    closure = json.loads(
        Path(task.artifact_root, "rebuttal", "REBUTTAL_CLOSURE_REPORT.json").read_text(encoding="utf-8")
    )
    assert closure["status"] == "pass"
    assert closure["coverage"][0]["comment_id"] == "R1.C1"
    assert closure["coverage"][0]["declared_revision_status"] == "planned"


def test_rebuttal_checkpoints_only_for_mutually_exclusive_strategies(
    service: ResearchAgentService, monkeypatch
):
    session = service.store.create_session()
    _write_rebuttal_sources(session)
    service.store.save_session(session)

    async def generate_with_choice(*, system_prompt, user_prompt, model=None, temperature=0.3):
        if "Current stage: Response Strategy" in user_prompt:
            return (
                "# Response Strategy\n\n## Strategy by Comment\n- R1.C1 is unresolved.\n\n"
                "## Accepted and Partially Accepted Points\n- None.\n\n"
                "## Clarifications and Evidence-Based Disagreements\n- Possible.\n\n"
                "## New Experiments or Analysis\n- Possible.\n\n"
                "## Risks and Dependencies\n- Deadline.\n\n"
                "## Decision Required\n"
                "Blocking: Yes\n"
                "Question: Choose the response commitment.\n"
                "Why user input is necessary: The choice changes cost and the manuscript claim.\n"
                "Option A: add the expensive experiment\n"
                "Option B: narrow the paper claim\n"
                "Recommended Default: Option B."
            )
        return "# Rebuttal Artifact\n\n- Source-grounded output."

    monkeypatch.setattr(agent_module, "generate_text", generate_with_choice)
    result = run(service.chat(session.session_id, "/rebuttal 回复审稿人"))

    assert result["status"] == "waiting_human"
    assert result["checkpoint"]["title"] == "Rebuttal Strategy Decision"
