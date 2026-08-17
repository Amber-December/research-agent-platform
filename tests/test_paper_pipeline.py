from __future__ import annotations

import json
from pathlib import Path

from research_agent_platform import agent as agent_module, paper_pipeline
from research_agent_platform.agent import ResearchAgentService
from research_agent_platform.connectors.scholar import LiteratureBundle, PaperRecord
from research_agent_platform.models import TaskRun, UploadBatchRecord
from research_agent_platform.paper_pipeline import (
    build_fulltext_venue_style_card,
    build_writing_style_context,
    assess_writing_length,
    build_paper_quality_reports,
    collect_paper_evidence,
    extract_venue_guidance_urls,
    extract_writing_length_contract,
    infer_source_section,
    resolve_write_source_config,
    select_discipline_profile,
    select_venue_profile,
)
from research_agent_platform.publication_contracts import VenueRuleSource, VenueStyleCard, VenueStyleRule

from .conftest import run


def _prepare_write_workspace(session) -> None:
    workspace = Path(session.workspace_root)
    result = workspace / "figures" / "results.csv"
    plan = workspace / "plan" / "EXPERIMENT_PLAN.md"
    bib = workspace / "bib" / "references.bib"
    result.parent.mkdir(parents=True, exist_ok=True)
    plan.parent.mkdir(parents=True, exist_ok=True)
    bib.parent.mkdir(parents=True, exist_ok=True)
    result.write_text("model,accuracy\nours,0.91\nbaseline,0.84\n", encoding="utf-8")
    plan.write_text("# Experiment Plan\n\nEvaluate accuracy against the baseline.", encoding="utf-8")
    bib.write_text("@article{smith2025, title={Grounded Research}}", encoding="utf-8")
    session.upload_batches.append(
        UploadBatchRecord(relative_paths=["figures/results.csv", "bib/references.bib"])
    )


def test_write_source_set_combines_latest_uploads_and_workspace(service: ResearchAgentService):
    session = service.store.create_session()
    _prepare_write_workspace(session)
    service.store.save_session(session)

    config = resolve_write_source_config(
        "/write 写论文",
        Path(session.workspace_root),
        session.upload_batches,
    )

    assert config.resolved_scope == "session"
    assert "figures/results.csv" in config.source_refs
    assert "plan/EXPERIMENT_PLAN.md" in config.source_refs
    assert config.upload_batch_id == session.upload_batches[-1].upload_batch_id


def test_write_source_set_includes_dedicated_results_directory(service: ResearchAgentService):
    session = service.store.create_session()
    workspace = Path(session.workspace_root)
    result = workspace / "results" / "summary.md"
    result.parent.mkdir(parents=True, exist_ok=True)
    result.write_text("Paired nitrate reduction was 1.6 mg N/L.", encoding="utf-8")

    config = resolve_write_source_config(
        "/write --source workspace 写论文",
        workspace,
        session.upload_batches,
    )

    assert config.resolved_scope == "workspace"
    assert "results/summary.md" in config.source_refs


def test_collect_paper_evidence_assigns_stable_ids(tmp_path: Path):
    source = tmp_path / "plan" / "notes.md"
    source.parent.mkdir(parents=True)
    source.write_text("# Result\n\nAccuracy is 0.91.", encoding="utf-8")

    first = collect_paper_evidence(tmp_path, ["plan/notes.md"])
    second = collect_paper_evidence(tmp_path, ["plan/notes.md"])

    assert first == second
    assert first[0]["evidence_id"].startswith("PE-")
    assert first[0]["source_path"] == "plan/notes.md"


def test_infer_source_section_uses_heading_without_imposing_a_template(tmp_path: Path):
    source = tmp_path / "paper" / "excerpt.md"
    source.parent.mkdir(parents=True)
    source.write_text("## 方法\n\n采用分层抽样与回归模型分析。", encoding="utf-8")

    inferred = infer_source_section(tmp_path, ["paper/excerpt.md"])

    assert inferred["section"] == "方法"
    assert inferred["confidence"] == "high"


def test_writing_style_context_combines_discipline_language_and_verified_venue_rule():
    source = VenueRuleSource(
        url="https://example.org/authors",
        source_type="official_guideline",
    )
    card = VenueStyleCard(
        card_id="nature-ai",
        venue="Nature",
        language="en",
        sources=[source],
        rules=[
            VenueStyleRule(
                category="reporting",
                instruction="Include a data-availability statement when required.",
                source_urls=[source.url],
            )
        ],
    )

    profile = select_discipline_profile("Write an English AI benchmark article for Nature")
    context = build_writing_style_context("Write an English AI benchmark article for Nature", card)

    assert profile["id"] == "ai_computer_science"
    assert "dataset, split, metric and baseline" in context
    assert "Avoid these failure modes" in context
    assert "specific subjects and measured conditions" in context
    assert "Include a data-availability statement when required." in context


def test_fulltext_venue_style_card_requires_three_allowed_lawful_fulltexts(tmp_path: Path):
    from reportlab.pdfgen.canvas import Canvas

    papers = tmp_path / "bib" / "papers"
    papers.mkdir(parents=True)
    allowed = []
    for index in range(3):
        path = papers / f"P{index + 1:03d}_sample.pdf"
        canvas = Canvas(str(path))
        canvas.drawString(72, 760, "Abstract")
        canvas.drawString(72, 740, "Introduction")
        canvas.drawString(72, 720, "Methods")
        canvas.drawString(72, 700, "Results")
        canvas.drawString(72, 680, "Discussion")
        canvas.drawString(72, 660, "References")
        for line in range(280):
            canvas.drawString(72, 640 - (line % 45) * 12, "Evidence-oriented academic prose for structural analysis only.")
            if line and line % 45 == 0:
                canvas.showPage()
        canvas.save()
        allowed.append(path.relative_to(tmp_path).as_posix())

    card = build_fulltext_venue_style_card(
        tmp_path, venue="Nature", article_type="research-article", language="en",
        allowed_relative_paths=allowed,
    )

    assert card is not None
    assert len(card.sources) == 3
    assert any(rule.category == "fulltext-structure" for rule in card.rules)
    assert build_fulltext_venue_style_card(
        tmp_path, venue="Nature", article_type="research-article", language="en",
        allowed_relative_paths=allowed[:2],
    ) is None


def test_writing_style_context_adds_curated_exemplar_patterns_for_review_writing():
    context = build_writing_style_context(
        "Write a 1200-1600 words English AI literature review for a journal."
    )

    assert "Curated exemplar patterns" in context
    assert "Synthesize by task, setting, evidence and disagreement" in context
    assert "Never copy exemplar wording" in context


def test_writing_style_context_includes_verified_style_corpus_rules():
    context = build_writing_style_context(
        "Write an English systematic review of AI applications in higher education."
    )

    assert "Verified style-corpus rules" in context
    assert "search, screening, coding and synthesis" in context
    assert "not copied prose" in context


def test_writing_style_context_loads_local_library_controls_for_chinese_social_science():
    context = build_writing_style_context(
        "根据省级面板数据写一篇中文社会科学期刊论文，讨论城乡收入差距。"
    )

    assert "real-world puzzle" in context
    assert "identification or model assumption" in context


def test_writing_style_context_loads_targeted_clinical_reporting_controls():
    context = build_writing_style_context(
        "Write an English randomized clinical trial article with participant flow and harms."
    )

    assert "trial design and allocation" in context
    assert "randomisation and blinding" in context


def test_writing_style_context_injects_theorem_proof_boundaries_for_math_cases():
    context = build_writing_style_context("Draft an English mathematics theorem proof section")

    assert "theorem" in context.lower()
    assert "hypothesis" in context.lower()
    assert "unproved lemma" in context.lower()


def test_writing_style_context_injects_operando_boundary_for_materials_cases():
    context = build_writing_style_context(
        "Draft an English electrocatalyst manuscript from ex situ XPS characterization."
    )

    assert "operando" in context.lower()
    assert "ex situ" in context.lower()
    assert "active state" in context.lower()


def test_writing_style_context_uses_thesis_specific_exemplar_patterns():
    context = build_writing_style_context(
        "润色中文博士学位论文，保留现有章节结构、事实与引文。"
    )

    assert "Document profile: degree_thesis" in context
    assert "Do not force a journal IMRAD structure" in context


def test_writing_style_context_detects_chinese_thesis_without_an_explicit_language_label():
    context = build_writing_style_context("润色硕士学位论文，保留原有章节、术语、事实与引文。")

    assert "Draft language: Chinese." in context
    assert "Keep Chinese terminology" in context


def test_venue_guidance_url_extraction_accepts_public_https_urls_only():
    objective = (
        "Write for Nature and learn style from https://www.nature.com/nature/for-authors "
        "but ignore http://localhost:8000/private."
    )

    assert extract_venue_guidance_urls(objective) == ["https://www.nature.com/nature/for-authors"]


def test_writing_length_contract_parses_english_words_and_chinese_characters():
    english = extract_writing_length_contract("Write an English review of 1200-1600 words.")
    chinese = extract_writing_length_contract("润色该章节，不超过 6000 字。")

    assert english == {"minimum": 1200, "maximum": 1600, "unit": "words"}
    assert chinese == {"minimum": 0, "maximum": 6000, "unit": "characters"}


def test_review_length_guidance_scales_sections_to_explicit_smoke_contract():
    guidance = paper_pipeline.build_writing_length_guidance(
        "Write a 1500-2500 words English literature review."
    )

    assert "User-specified contract overrides profile defaults: 1500–2500 words." in guidance
    assert "Abstract: 8–10%" in guidance
    assert "Thematic synthesis: 50–60%" in guidance
    assert "formal review-article structure" in guidance


def test_review_length_guidance_translates_explicit_total_into_section_word_budgets():
    guidance = paper_pipeline.build_writing_length_guidance(
        "Write a 1500-2500 words English literature review."
    )

    assert "Scaled section budget for this delivery (before references):" in guidance
    assert "Abstract: 160–200 words" in guidance
    assert "Thematic synthesis: 1000–1200 words" in guidance


def test_research_article_length_guidance_defines_section_responsibilities():
    guidance = paper_pipeline.build_writing_length_guidance(
        "Write an English research article from these results."
    )

    assert "Research article fallback: 4000–8000 words" in guidance
    assert "Abstract: 150–300 words" in guidance
    assert "Introduction: 10–15%" in guidance
    assert "Results: 25–35%" in guidance
    assert "venue instructions override" in guidance.lower()


def test_degree_thesis_length_guidance_does_not_force_imrad():
    guidance = paper_pipeline.build_writing_length_guidance(
        "润色中文博士学位论文章节"
    )

    assert "Degree thesis fallback" in guidance
    assert "Thesis abstract: 800–1500 characters" in guidance
    assert "Do not force IMRAD" in guidance


def test_writing_length_assessment_uses_contract_unit_and_validity():
    english = assess_writing_length(
        "one two three four",
        {"minimum": 3, "maximum": 4, "unit": "words"},
    )
    chinese = assess_writing_length(
        "中文学术写作",
        {"minimum": 0, "maximum": 6, "unit": "characters"},
    )

    assert english == {"unit": "words", "count": 4, "valid": True}
    assert chinese == {"unit": "characters", "count": 6, "valid": True}


def test_venue_style_discovery_persists_candidate_metadata_without_claiming_official_rules(
    service: ResearchAgentService,
):
    session = service.store.create_session()
    task = TaskRun(
        session_id=session.session_id,
        command="/write",
        objective="Write an English AI paper for Nature",
        route_source="explicit",
        workflow_title="Paper Writing Workflow",
        artifact_root=session.workspace_root,
    )

    class StubScholar:
        async def search_bundle(self, query, *, per_source_limit, max_papers):
            return LiteratureBundle(
                query=query,
                papers=[
                    PaperRecord(
                        title="Comparable open article",
                        year=2025,
                        abstract="An abstract-level rhetorical pattern.",
                        authors=["Author"],
                        url="https://example.org/article",
                        venue="Nature",
                        citation_count=10,
                        sources=["OpenAlex"],
                    )
                ],
                provider_status={"openalex": "ok"},
            )

    service.scholar = StubScholar()
    artifacts, context = run(service._prepare_venue_style_discovery(task, select_venue_profile(task.objective)))

    payload = json.loads(Path(task.artifact_root, "Content", "VENUE_STYLE_DISCOVERY.json").read_text(encoding="utf-8"))
    assert len(artifacts) == 2
    assert payload["status"] == "candidate_metadata_only"
    assert payload["rule_status"] == "not_official_guidance"
    assert "Comparable open article" in context


def test_write_evidence_cache_is_bound_to_task_source_set(service: ResearchAgentService):
    session = service.store.create_session()
    workspace = Path(session.workspace_root)
    first_source = workspace / "plan" / "first.md"
    second_source = workspace / "plan" / "second.md"
    first_source.parent.mkdir(parents=True, exist_ok=True)
    first_source.write_text("first evidence", encoding="utf-8")
    second_source.write_text("second evidence", encoding="utf-8")
    first_task = service.store.list_tasks(session.session_id)
    assert first_task == []

    from research_agent_platform.models import TaskRun, WriteSourceConfig

    task = TaskRun(
        session_id=session.session_id,
        command="/write",
        objective="write",
        route_source="explicit",
        workflow_title="Paper Writing Workflow",
        artifact_root=session.workspace_root,
        write_source=WriteSourceConfig(
            resolved_scope="selected",
            source_refs=["plan/second.md"],
        ),
    )
    Path(workspace, "paper").mkdir(parents=True, exist_ok=True)
    Path(workspace, "Content").mkdir(parents=True, exist_ok=True)
    Path(workspace, "paper", "PAPER_EVIDENCE_MAP.json").write_text(
        json.dumps([{"evidence_id": "PE-OLD", "source_path": "plan/first.md"}]),
        encoding="utf-8",
    )
    Path(workspace, "Content", "PAPER_EVIDENCE_METADATA.json").write_text(
        json.dumps({"task_id": "old-task", "source_refs": ["plan/first.md"]}),
        encoding="utf-8",
    )

    records = service._paper_evidence_records(task)

    assert records[0]["source_path"] == "plan/second.md"


def test_write_runs_evidence_review_revision_and_delivery_gates(
    service: ResearchAgentService, monkeypatch
):
    session = service.store.create_session()
    _prepare_write_workspace(session)
    service.store.save_session(session)

    async def generate_paper(*, system_prompt, user_prompt, model=None, temperature=0.3):
        if "Current stage: Paper Plan" in user_prompt:
            return (
                "# Paper Plan\n\n## Target Story\nEvidence-grounded result.\n\n## Submission Target\nUnspecified.\n\n"
                "## Section Outline\nStandard paper.\n\n## Section Responsibilities and Paragraph Jobs\nOne claim per paragraph.\n\n"
                "## Claim to Evidence Map\n- Accuracy -> frozen PE evidence.\n\n## Terminology and Claim Boundaries\nBounded.\n\n"
                "## Writing Risks\nMissing robustness.\n\n## Questions for Human Review\nNone.\n\n## Decision Required\nNone."
            )
        if "Current stage: Narrative Report" in user_prompt:
            return (
                "# Narrative\n\n## Problem Statement\nProblem.\n\n## Core Claim\nAccuracy improved.\n\n"
                "## Method Summary\nMethod.\n\n## Key Results\n0.91 vs 0.84.\n\n"
                "## Evidence and Citation Boundaries\nUse frozen evidence.\n\n## Limitations\nRobustness.\n\n## Open Gaps\nMore seeds."
            )
        if "Current stage: Draft Sections" in user_prompt:
            return _paper_markdown("Draft title", "Draft evidence wording")
        if "Current stage: Paper Self Review" in user_prompt:
            return (
                "# Self Review\n\n## Quality Scores\n- Evidence: 4\n\n## Major Issues\n- M1: Clarify evidence wording.\n\n"
                "## Minor Issues\n- None.\n\n## Claim and Evidence Findings\n- Grounded.\n\n"
                "## Citation Findings\n- smith2025 resolves.\n\n## Structure and Venue Findings\n- Complete.\n\n"
                "## Revision Actions\n- M1 revise wording."
            )
        if "Current stage: Paper Revision" in user_prompt:
            return _paper_markdown("Revised title", "Revised evidence wording")
        return "# Artifact\n\nGenerated."

    monkeypatch.setattr(agent_module, "generate_text", generate_paper)
    result = run(service.chat(session.session_id, "/write --source workspace 写论文 word pdf"))
    task = service.get_task(result["task_id"])

    assert result["status"] == "completed"
    assert result["checkpoint"] is None
    assert task is not None and task.write_source is not None
    assert Path(task.artifact_root, "paper", "PAPER_EVIDENCE_MAP.json").exists()
    assert Path(task.artifact_root, "paper", "PAPER_SELF_REVIEW.md").exists()
    assert Path(task.artifact_root, "paper", "PAPER_REVISED.md").exists()
    assert Path(task.artifact_root, "paper", "FINAL_REVIEW_PACKAGE.json").exists()
    assert Path(task.artifact_root, "Content", "WRITING_EVALUATION_REPORT.json").exists()
    assert Path(task.artifact_root, "paper", "PAPER_REVISED.docx").exists()
    assert Path(task.artifact_root, "paper", "PAPER_REVISED.pdf").exists()
    selection = json.loads(
        Path(task.artifact_root, "Content", "PAPER_SOURCE_SELECTION.json").read_text(encoding="utf-8")
    )
    assert selection["source_boundary"] == "frozen_at_task_start"
    delivery = json.loads(
        Path(task.artifact_root, "paper", "PAPER_DELIVERY_REPORT.json").read_text(encoding="utf-8")
    )
    citation = json.loads(
        Path(task.artifact_root, "paper", "CITATION_AUDIT.json").read_text(encoding="utf-8")
    )
    assert delivery["status"] == "pass"
    assert citation["unknown_keys"] == []


def test_quality_gate_reports_unknown_citation(tmp_path: Path):
    manuscript = tmp_path / "paper" / "PAPER_REVISED.md"
    manuscript.parent.mkdir(parents=True)
    manuscript.write_text(_paper_markdown("Title", "Text").replace("smith2025", "unknown2026"), encoding="utf-8")
    (tmp_path / "bib").mkdir()
    (tmp_path / "bib" / "references.bib").write_text(
        "@article{smith2025, title={Known}}", encoding="utf-8"
    )

    citation, delivery = build_paper_quality_reports(
        tmp_path,
        "paper/PAPER_REVISED.md",
        [],
        select_venue_profile("research paper"),
    )

    assert citation["unknown_keys"] == ["unknown2026"]
    assert delivery["status"] == "needs_attention"


def test_paper_citation_audit_flags_admitted_bibliography_not_used_in_body(tmp_path: Path):
    manuscript = tmp_path / "paper" / "PAPER_REVISED.md"
    manuscript.parent.mkdir(parents=True)
    manuscript.write_text(_paper_markdown("Title", "Text"), encoding="utf-8")
    (tmp_path / "bib").mkdir()
    (tmp_path / "bib" / "references.bib").write_text(
        "@article{smith2025, title={Known}}\n@article{jones2024, title={Uncited}}",
        encoding="utf-8",
    )

    citation, _ = build_paper_quality_reports(
        tmp_path,
        "paper/PAPER_REVISED.md",
        [],
        select_venue_profile("research paper"),
    )

    assert citation["body_citation_coverage"] == 0.5
    assert citation["corpus_coverage_status"] == "needs_attention"
    assert citation["status"] == "needs_attention"


def _paper_markdown(title: str, wording: str) -> str:
    return (
        f"# {title}\n\n## Abstract\n{wording}.\n\n## Introduction\nProblem context [@smith2025].\n\n"
        "## Related Work\nPrior work [@smith2025].\n\n## Method\nMethod description.\n\n"
        "## Experiments or Results\nAccuracy is 0.91 versus 0.84.\n\n## Limitations\nRobustness remains limited.\n\n"
        "## Conclusion\nBounded conclusion.\n\n## References\n- [@smith2025]\n\n## Unresolved Author Inputs\nNone."
    )
