from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx

from research_agent_platform.agent import ResearchAgentService
from research_agent_platform.connectors.seafile import SeafileWorkspaceSync
from research_agent_platform.graphs.workflows import workflow_registry
from research_agent_platform.router.intent import route_message


def test_reorganized_workflow_boundaries():
    workflows = workflow_registry()

    assert [stage.name for stage in workflows["/review"].stage_definitions] == [
        "research_brief",
        "literature_synthesis",
        "evidence_map",
        "research_gaps",
    ]
    assert [stage.name for stage in workflows["/idea"].stage_definitions] == [
        "idea_candidates",
        "idea_verification",
        "final_idea",
    ]
    assert [stage.name for stage in workflows["/plan"].stage_definitions] == [
        "blueprint",
        "experiment_plan",
        "execution_checklist",
    ]
    assert [stage.name for stage in workflows["/rebuttal"].stage_definitions] == [
        "review_triage",
        "rebuttal_draft",
        "revision_plan",
    ]


def test_router_separates_literature_review_and_peer_review():
    literature = asyncio.run(route_message("帮我找文献并写一份文献综述"))
    rebuttal = asyncio.run(route_message("请分析审稿意见并回复审稿人"))
    idea = asyncio.run(route_message("围绕这个方向提出三个创新点"))
    plan = asyncio.run(route_message("给这个选题制定实验方案"))

    assert literature is not None and literature.command == "/review"
    assert rebuttal is not None and rebuttal.command == "/rebuttal"
    assert idea is not None and idea.command == "/idea"
    assert plan is not None and plan.command == "/plan"


def test_seafile_workspace_sync_is_incremental(tmp_path: Path):
    workspace = tmp_path / "agent-workspace" / "local" / "session_demo"
    source = workspace / "paper" / "draft.md"
    source.parent.mkdir(parents=True)
    source.write_text("first version", encoding="utf-8")
    uploads: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Authorization") == "Token test-token"
        if request.url.path == "/api2/repos/repo-1/dir/":
            return httpx.Response(200, json=[])
        if request.url.path == "/api2/repos/repo-1/upload-link/":
            return httpx.Response(200, json="https://cloud.example/upload/repo-1")
        if request.url.path == "/upload/repo-1":
            uploads.append(request.content.decode("latin-1"))
            return httpx.Response(200, json={"id": "file-id"})
        if request.url.path == "/api/v2.1/share-links/":
            return httpx.Response(
                200,
                json=[{"link": "https://cloud.example/d/shared-session"}],
            )
        raise AssertionError(f"Unexpected Seafile request: {request.method} {request.url}")

    sync = SeafileWorkspaceSync(
        enabled=True,
        base_url="https://cloud.example",
        api_token="test-token",
        repo_id="repo-1",
        remote_root="research-agent",
        transport=httpx.MockTransport(handler),
    )

    first = asyncio.run(
        sync.sync_workspace(workspace, user_id="local", session_id="session_demo")
    )
    second = asyncio.run(
        sync.sync_workspace(workspace, user_id="local", session_id="session_demo")
    )

    assert first.status == "synced"
    assert first.remote_path == "/research-agent/local/session_demo"
    assert first.uploaded_files == 1
    assert first.preview_url == "https://cloud.example/d/shared-session"
    assert second.uploaded_files == 0
    assert len(uploads) == 1
    state = json.loads((workspace / "Content" / "CLOUD_SYNC.json").read_text(encoding="utf-8"))
    assert state["file_signatures"]["paper/draft.md"]


def test_plan_does_not_trigger_literature_search(service: ResearchAgentService, monkeypatch):
    calls = 0

    async def unexpected_search(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("/plan must reuse evidence instead of launching literature search")

    monkeypatch.setattr(service.scholar, "search_bundle", unexpected_search)
    result = asyncio.run(service.chat(None, "/plan 制定实验方案"))

    assert result["status"] == "completed"
    assert calls == 0


def test_idea_reuses_existing_review_evidence(service: ResearchAgentService, monkeypatch):
    session = service.store.create_session()
    workspace = Path(session.workspace_root)
    evidence = workspace / "bib" / "EVIDENCE_MAP.md"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text("# Evidence Map\n\nGrounded evidence.", encoding="utf-8")
    calls = 0

    async def unexpected_search(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("/idea must reuse existing review evidence")

    monkeypatch.setattr(service.scholar, "search_bundle", unexpected_search)
    result = asyncio.run(service.chat(session.session_id, "/idea 提出一个创新方向"))

    assert result["status"] == "completed"
    assert calls == 0
