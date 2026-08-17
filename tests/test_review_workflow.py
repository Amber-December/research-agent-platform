from __future__ import annotations

import json
from pathlib import Path

from research_agent_platform import agent as agent_module, review_pipeline
from research_agent_platform.agent import ResearchAgentService
from research_agent_platform.connectors.scholar import LiteratureBundle, PaperRecord
from research_agent_platform.models import TaskRun
from research_agent_platform.graphs.workflows import workflow_registry

from .conftest import run


def _bundle(query: str, count: int) -> LiteratureBundle:
    papers = [
        PaperRecord(
            title=f"{query} study {index}",
            year=2018 + index,
            abstract=f"Evidence for {query}, method {index}, and limitations.",
            authors=[f"Author {index}"],
            url=f"https://doi.org/10.1000/{index}",
            venue="Research Journal",
            citation_count=index,
            sources=["OpenAlex"],
            identifiers={"doi": f"10.1000/{index}"},
            paper_id=f"P{index:03d}",
            relevance_score=0.9,
            matched_queries=[query],
            verification_status="traceable_identifier",
        )
        for index in range(1, count + 1)
    ]
    return LiteratureBundle(
        query=query,
        queries=[query, f"{query} review"],
        papers=papers,
        provider_status={"openalex": f"ok ({count} records)"},
        quality={
            "status": "adequate" if count >= 10 else "insufficient",
            "candidate_count": count,
            "relevant_count": count,
            "minimum_for_synthesis": 10,
            "recommended_for_review": 15,
            "traceable_count": count,
            "provider_success_count": 1,
        },
    )


def test_review_stops_before_synthesis_when_evidence_is_insufficient(
    service: ResearchAgentService,
    monkeypatch,
) -> None:
    async def insufficient(query, **_kwargs):
        return _bundle(query, 2)

    monkeypatch.setattr(service.scholar, "search_bundle", insufficient)
    result = run(service.chat(None, "/review 写一个当前海绵城市相关的综述"))
    task = service.get_task(result["task_id"])

    assert result["status"] == "failed"
    assert task is not None and task.status == "failed"
    workspace = Path(task.artifact_root)
    assert (workspace / "bib" / "RESEARCH_BRIEF.md").exists()
    assert (workspace / "bib" / "LITERATURE_SEARCH.json").exists()
    assert "Gate: FAIL" in (workspace / "bib" / "RETRIEVAL_QUALITY.md").read_text(encoding="utf-8")
    assert not (workspace / "bib" / "LITERATURE_REVIEW.md").exists()
    assert not (workspace / "bib" / "EVIDENCE_MAP.md").exists()
    assert not (workspace / "bib" / "RESEARCH_GAPS.md").exists()
    assert not (workspace / "bib" / "CITATION_AUDIT.json").exists()


def test_review_writing_emits_taxonomy_and_synthesis_matrix(
    service: ResearchAgentService,
    monkeypatch,
) -> None:
    async def sufficient(query, **_kwargs):
        return _bundle(query, 10)

    monkeypatch.setattr(service.scholar, "search_bundle", sufficient)
    result = run(service.chat(None, "/review 写一篇海绵城市文献综述"))
    task = service.get_task(result["task_id"])

    assert result["status"] == "completed"
    assert task is not None and task.workflow_mode == "literature_review_writing"
    workspace = Path(task.artifact_root)
    package = json.loads((workspace / "Content" / "LITERATURE_REVIEW_WRITING_PACKAGE.json").read_text())
    matrix = json.loads((workspace / "bib" / "SYNTHESIS_MATRIX.json").read_text())
    assert package["source_paper_ids"] == [f"P{index:03d}" for index in range(1, 11)]
    assert len(matrix) == 10


def test_review_synthesis_instruction_requires_a_traceable_scope_summary():
    workflow = workflow_registry()["/review"]
    synthesis = next(stage for stage in workflow.stage_definitions if stage.name == "literature_synthesis")

    assert "retrieval scope summary" in synthesis.instruction
    assert "material condition, assumption, or boundary" in synthesis.instruction


def test_review_synthesis_matrix_is_backfilled_from_generated_review(
    service: ResearchAgentService,
) -> None:
    session = service.store.create_session()
    workspace = Path(session.workspace_root)
    (workspace / "bib").mkdir(parents=True, exist_ok=True)
    (workspace / "bib" / "LITERATURE_SEARCH.json").write_text(
        json.dumps(
            {
                "papers": [
                    {
                        "paper_id": "P001",
                        "title": "Study one",
                        "year": 2024,
                        "venue": "Journal",
                        "verification_status": "traceable_identifier",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (workspace / "bib" / "LITERATURE_REVIEW.md").write_text(
        "# Review\n\n## Contradictory Evidence\n\nHigh-flow outcomes differed from low-flow outcomes [P001].",
        encoding="utf-8",
    )
    task = TaskRun(
        session_id=session.session_id,
        command="/review",
        objective="write review",
        route_source="explicit",
        workflow_title="Literature Review Workflow",
        workflow_mode="literature_review_writing",
        artifact_root=session.workspace_root,
    )

    service._write_review_writing_artifacts(task)

    matrix = json.loads((workspace / "bib" / "SYNTHESIS_MATRIX.json").read_text())
    taxonomy = json.loads((workspace / "bib" / "REVIEW_TAXONOMY.json").read_text())
    assert matrix[0]["citation_count"] == 1
    assert matrix[0]["synthesis_role"] == "cited_in_thematic_synthesis"
    assert "High-flow outcomes" in matrix[0]["synthesis_context"]
    assert "Contradictory Evidence" in taxonomy["review_themes"]


def test_nine_traceable_sources_do_not_satisfy_ten_source_gate(
    service: ResearchAgentService,
    monkeypatch,
) -> None:
    async def insufficient(query, **_kwargs):
        return _bundle(query, 9)

    monkeypatch.setattr(service.scholar, "search_bundle", insufficient)
    result = run(service.chat(None, "/review sponge city"))
    task = service.get_task(result["task_id"])

    assert result["status"] == "failed"
    assert task is not None and task.status == "failed"
    quality = Path(task.artifact_root, "bib", "RETRIEVAL_QUALITY.md").read_text(encoding="utf-8")
    assert "Required minimum sources: 10" in quality
    assert "Admitted sources: 9" in quality
    assert "Gate: FAIL" in quality


def test_review_completes_with_stable_id_audit(
    service: ResearchAgentService,
    monkeypatch,
) -> None:
    async def review_text(*, system_prompt, user_prompt, model=None, temperature=0.3):
        if "Current stage: Research Brief" in user_prompt:
            return "# Brief\n\n## Search Strategy\nQ1: sponge city\nQ2: green stormwater infrastructure review"
        if "Current stage: Literature Synthesis" in user_prompt:
            return "# Review\n\nEvidence agrees [P001] [P002] [P003] [P004] [P005] [P006] [P007] [P008] [P009] [P010]."
        if "Current stage: Evidence Map" in user_prompt:
            return "# Evidence Map\n\nSupported claim [P001] and unknown source [P999]."
        return "# Research Gaps\n\nSupported gap [P002] [P003]."

    monkeypatch.setattr(agent_module, "generate_text", review_text)
    result = run(service.chat(None, "/review sponge city"))
    task = service.get_task(result["task_id"])

    assert result["status"] == "completed"
    assert task is not None
    workspace = Path(task.artifact_root)
    audit = json.loads((workspace / "bib" / "CITATION_AUDIT.json").read_text(encoding="utf-8"))
    coverage = json.loads((workspace / "bib" / "REVIEW_COVERAGE.json").read_text(encoding="utf-8"))
    assert audit["unknown_paper_ids"] == ["P999"]
    assert audit["status"] == "needs_attention"
    assert coverage["paper_count"] == 10
    assert coverage["reference_coverage"] == 1.0


def test_review_citation_audit_recognizes_non_p_prefixed_stable_ids(tmp_path: Path):
    workspace = tmp_path
    (workspace / "bib").mkdir()
    (workspace / "bib" / "LITERATURE_SEARCH.json").write_text(
        json.dumps(
            {
                "papers": [
                    {"paper_id": "AI001", "verification_status": "traceable_identifier"},
                    {"paper_id": "AI002", "verification_status": "traceable_identifier"},
                ],
                "quality": {"relevant_count": 2, "traceable_count": 2},
            }
        ),
        encoding="utf-8",
    )
    (workspace / "bib" / "LITERATURE_REVIEW.md").write_text(
        "# Review\n\nThe official split yielded 84.2% accuracy [AI001].\n\n"
        "The custom split is not directly comparable [AI002].\n\n"
        "## References\n\n[AI001] Synthetic record.\n\n[AI002] Synthetic record.",
        encoding="utf-8",
    )

    audit, coverage = review_pipeline.build_review_quality_reports(workspace)

    assert audit["file_citations"]["bib/LITERATURE_REVIEW.md"] == ["AI001", "AI002"]
    assert audit["resolution_status"] == "pass"
    assert audit["claim_coverage"]["status"] == "pass"
    assert audit["semantic_support_status"] == "not_deterministically_verified"
    assert audit["status"] == "pass"
    assert coverage["reference_coverage"] == 1.0


def test_review_citation_audit_flags_citable_claim_without_adjacent_source(tmp_path: Path):
    workspace = tmp_path
    (workspace / "bib").mkdir()
    (workspace / "bib" / "LITERATURE_SEARCH.json").write_text(
        json.dumps(
            {
                "papers": [{"paper_id": "AI001", "verification_status": "traceable_identifier"}],
                "quality": {"relevant_count": 1, "traceable_count": 1},
            }
        ),
        encoding="utf-8",
    )
    (workspace / "bib" / "LITERATURE_REVIEW.md").write_text(
        "# Review\n\nThe official split yielded 84.2% accuracy.\n\n"
        "## References\n\n[AI001] Synthetic record.",
        encoding="utf-8",
    )

    audit, _ = review_pipeline.build_review_quality_reports(workspace)

    assert audit["resolution_status"] == "pass"
    assert audit["claim_coverage"]["status"] == "needs_attention"
    assert audit["claim_coverage"]["uncited_claim_count"] == 1
    assert audit["status"] == "needs_attention"


def test_review_prompt_excerpt_excludes_platform_download_state():
    bundle = _bundle("benchmark", 1)
    bundle.papers[0].download_status = "disabled"
    bundle.papers[0].pdf_url = ""

    excerpt = bundle.prompt_excerpt()

    assert "download" not in excerpt.lower()
    assert "public pdf" not in excerpt.lower()
    assert "P001" in excerpt
    assert "Evidence for benchmark" in excerpt


def test_ten_extracted_local_papers_can_satisfy_review_gate(
    service: ResearchAgentService,
    monkeypatch,
) -> None:
    session = service.store.create_session()
    uploads = Path(session.workspace_root, "paper", "uploads")
    uploads.mkdir(parents=True, exist_ok=True)
    for index in range(1, 11):
        (uploads / f"paper-{index}.txt").write_text(
            f"海绵城市 paper {index}. Method, result, and limitation.",
            encoding="utf-8",
        )
    (uploads / "unrelated.txt").write_text(
        "Contemporary film aesthetics and ritual literature.",
        encoding="utf-8",
    )

    async def no_external_evidence(query, **_kwargs):
        return _bundle(query, 0)

    monkeypatch.setattr(service.scholar, "search_bundle", no_external_evidence)
    result = run(service.chat(session.session_id, "/review 海绵城市"))
    task = service.get_task(result["task_id"])

    assert result["status"] == "completed"
    assert task is not None
    workspace = Path(task.artifact_root)
    quality = (workspace / "bib" / "RETRIEVAL_QUALITY.md").read_text(encoding="utf-8")
    search = json.loads((workspace / "bib" / "LITERATURE_SEARCH.json").read_text(encoding="utf-8"))
    assert "Gate: PASS" in quality
    assert "Required minimum sources: 10" in quality
    assert "Local candidates discovered: 11" in quality
    assert "Local sources with extracted evidence: 10" in quality
    assert len(search["quality"]["local_evidence_sources"]) == 10


def test_frozen_local_corpus_uses_structured_evidence_without_external_search(
    service: ResearchAgentService,
    monkeypatch,
) -> None:
    session = service.store.create_session()
    uploads = Path(session.workspace_root, "bib", "uploads")
    uploads.mkdir(parents=True, exist_ok=True)
    evidence_lines = [
        json.dumps(
            {
                "paper_id": f"paper-{index:03d}",
                "bib_key": f"agent_{index}",
                "page": 1,
                "text": f"LLM multi-agent study {index} compares collaboration cost and reliability.",
            }
        )
        for index in range(1, 11)
    ]
    (uploads / "evidence.jsonl").write_text("\n".join(evidence_lines), encoding="utf-8")
    (uploads / "corpus.csv").write_text(
        "title,year,doi\n"
        + "\n".join(f"Study {index},2024,10.1000/{index}" for index in range(1, 11)),
        encoding="utf-8",
    )

    async def external_search_must_not_run(*_args, **_kwargs):
        raise AssertionError("frozen local corpus must not trigger external retrieval")

    monkeypatch.setattr(service.scholar, "search_bundle", external_search_must_not_run)
    result = run(
        service.chat(
            session.session_id,
            "/review Write a narrative review using only the uploaded local corpus.",
        )
    )

    assert result["status"] == "completed"
    task = service.get_task(result["task_id"])
    assert task is not None
    workspace = Path(task.artifact_root)
    search = json.loads((workspace / "bib" / "LITERATURE_SEARCH.json").read_text())
    assert len(search["papers"]) == 10
    assert search["provider_status"] == {"local_corpus": "frozen user-provided evidence"}
    quality = (workspace / "bib" / "RETRIEVAL_QUALITY.md").read_text(encoding="utf-8")
    assert "Gate: PASS" in quality


def test_new_review_archives_previous_outputs_before_failed_retrieval(
    service: ResearchAgentService,
    monkeypatch,
) -> None:
    first = run(service.chat(None, "/review sponge city"))
    first_task = service.get_task(first["task_id"])
    assert first_task is not None
    workspace = Path(first_task.artifact_root)
    assert (workspace / "bib" / "LITERATURE_REVIEW.md").exists()

    async def insufficient(query, **_kwargs):
        return _bundle(query, 0)

    monkeypatch.setattr(service.scholar, "search_bundle", insufficient)
    second = run(service.chat(first_task.session_id, "/review quantum networking"))
    second_task = service.get_task(second["task_id"])

    assert second["status"] == "failed"
    assert second_task is not None
    archive = workspace / "bib" / "archive" / f"prior-to-{second_task.task_id}"
    assert (archive / "LITERATURE_REVIEW.md").exists()
    assert not (workspace / "bib" / "LITERATURE_REVIEW.md").exists()
    assert not (workspace / "bib" / "EVIDENCE_MAP.md").exists()
    assert not (workspace / "bib" / "RESEARCH_GAPS.md").exists()
