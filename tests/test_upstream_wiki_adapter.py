import asyncio
from pathlib import Path

from research_agent_platform.agent import ResearchAgentService
from research_agent_platform.graphs.workflows import StageDefinition
from research_agent_platform.memory.store import ResearchWikiStore
from research_agent_platform.models import TaskRun
from research_agent_platform.paper_pipeline import resolve_write_source_config, select_venue_profile


def test_upstream_wiki_store_builds_query_pack_from_a_paper_summary(tmp_path: Path):
    summary = tmp_path / "wiki" / "papers" / "P-ABCDEF123456" / "summary.md"
    summary.parent.mkdir(parents=True)
    summary.write_text(
        "# Example Paper\n\n"
        "## 研究问题\n\n- [PE-1111111111] 研究问题。\n\n"
        "## 作者提出的未来工作\n\n- [PE-2222222222] 验证更广泛样本。\n\n"
        "## 作者讨论与局限\n\n- [PE-3333333333] 外部效度有限。\n",
        encoding="utf-8",
    )

    query_pack = ResearchWikiStore(tmp_path).query_pack("future work", character_limit=1800)

    assert "作者提出的未来工作" in query_pack
    assert "PE-2222222222" in query_pack
    assert "作者讨论与局限" in query_pack


def test_wiki_stage_uses_upstream_paper_store_for_uploaded_pdfs(service: ResearchAgentService, isolated_env: dict):
    workspace = Path(isolated_env["artifact_root"]) / "local" / "wiki-adapter"
    source = workspace / "paper" / "uploads" / "source.pdf"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"%PDF-1.4\nminimal test source")
    task = TaskRun(
        session_id="wiki-adapter",
        command="/wiki",
        objective="收录洪涝避险研究论文",
        route_source="explicit",
        workflow_title="Research Wiki Workflow",
        artifact_root=str(workspace),
    )
    stage = StageDefinition("knowledge_digest", "Knowledge Digest", "", "wiki/KNOWLEDGE_DIGEST.md", "wiki", [])

    artifacts, context, has_papers = asyncio.run(service._prepare_research_wiki_support(task, stage))

    assert has_papers is True
    assert any(artifact.relative_path == "wiki/index.md" for artifact in artifacts)
    assert (workspace / "wiki" / "papers").is_dir()
    assert "Research Wiki retrieval context" in context


def test_final_idea_is_written_back_to_the_upstream_wiki(service: ResearchAgentService, isolated_env: dict):
    workspace = Path(isolated_env["artifact_root"]) / "local" / "idea-adapter"
    task = TaskRun(
        task_id="idea-adapter",
        session_id="idea-adapter",
        command="/idea",
        objective="洪涝避险研究选题",
        route_source="explicit",
        workflow_title="Idea Discovery Workflow",
        artifact_root=str(workspace),
    )
    (workspace / "idea").mkdir(parents=True)
    (workspace / "wiki").mkdir(parents=True)
    (workspace / "idea" / "FINAL_IDEA.md").write_text("# Final Idea\n\nEvidence-bounded idea.", encoding="utf-8")
    (workspace / "idea" / "IDEA_VERIFICATION.md").write_text("# Verification\n\nKeep with caveats.", encoding="utf-8")
    (workspace / "wiki" / "query_pack.md").write_text("## P-ABCDEF123456: Paper", encoding="utf-8")

    artifacts = service._write_idea_to_wiki(task)

    assert {artifact.relative_path for artifact in artifacts} == {
        "wiki/ideas/idea-adapter.md",
        "wiki/relations.jsonl",
    }
    assert "idea_based_on" in (workspace / "wiki" / "relations.jsonl").read_text(encoding="utf-8")


def test_topic_and_venue_write_creates_retrieval_and_session_knowledge_assets(service: ResearchAgentService, isolated_env: dict):
    workspace = Path(isolated_env["artifact_root"]) / "local" / "topic-write"
    task = TaskRun(
        session_id="topic-write",
        command="/write",
        objective="Write an English review article about urban flood evacuation for Nature",
        route_source="explicit",
        workflow_title="Paper Writing Workflow",
        artifact_root=str(workspace),
    )
    source_config = resolve_write_source_config(task.objective, workspace)

    artifacts, context = asyncio.run(
        service._prepare_topic_driven_write_retrieval(task, source_config, select_venue_profile(task.objective))
    )

    assert source_config.source_refs == []
    assert any(artifact.relative_path == "bib/LITERATURE_SEARCH.json" for artifact in artifacts)
    assert any(artifact.relative_path == "wiki/KNOWLEDGE_DIGEST.md" for artifact in artifacts)
    assert (workspace / "bib" / "EVIDENCE_MAP.md").is_file()
    assert "Topic-driven writing retrieval package" in context
