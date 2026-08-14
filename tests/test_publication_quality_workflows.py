from __future__ import annotations

import json
from pathlib import Path

from research_agent_platform.agent import ResearchAgentService
from research_agent_platform.publication_quality import extract_citations

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


def test_peer_review_flags_unreferenced_strong_claim(service: ResearchAgentService):
    session = service.store.create_session()
    _manuscript(session)
    path = Path(session.workspace_root, "paper/uploads/paper.md")
    path.write_text(path.read_text(encoding="utf-8").replace("Method.", "Our method significantly outperforms all baselines."), encoding="utf-8")

    result = run(service.chat(session.session_id, "/peer-review"))
    task = service.get_task(result["task_id"])
    payload = json.loads(Path(task.artifact_root, "rebuttal/reviews/REVIEW_PACKAGE.json").read_text())

    assert result["status"] == "completed"
    assert any(item["category"] == "claims" and item["location"].startswith("line") for item in payload["findings"])


def test_final_check_writes_rubric_report_after_peer_review(service: ResearchAgentService):
    session = service.store.create_session()
    _manuscript(session)
    run(service.chat(session.session_id, "/peer-review"))
    result = run(service.chat(session.session_id, "/final-check"))
    task = service.get_task(result["task_id"])

    assert result["status"] == "completed"
    assert Path(task.artifact_root, "Content/WRITING_EVALUATION_REPORT.json").exists()


def test_final_check_resolves_latex_citation_and_blocks_unknown_key(service: ResearchAgentService):
    session = service.store.create_session()
    _manuscript(session)
    path = Path(session.workspace_root, "paper/uploads/paper.md")
    path.write_text(path.read_text(encoding="utf-8").replace("[@known]", "\\cite{unknown}"), encoding="utf-8")

    result = run(service.chat(session.session_id, "/final-check"))
    task = service.get_task(result["task_id"])
    payload = json.loads(Path(task.artifact_root, "paper/FINAL_GATE_REPORT.json").read_text())

    assert result["status"] == "completed"
    assert payload["decision"] == "BLOCK"


def test_final_check_flags_markdown_figure_number_gap(service: ResearchAgentService):
    session = service.store.create_session()
    _manuscript(session)
    path = Path(session.workspace_root, "paper/uploads/paper.md")
    path.write_text(path.read_text(encoding="utf-8") + "\nFigure 2 shows the result.", encoding="utf-8")

    result = run(service.chat(session.session_id, "/final-check"))
    task = service.get_task(result["task_id"])
    payload = json.loads(Path(task.artifact_root, "paper/FINAL_GATE_REPORT.json").read_text())

    assert result["status"] == "completed"
    finding = next(check for check in payload["checks"] if check["check"] == "markdown_figure_numbering")
    assert finding["status"] == "violated"


def test_final_check_blocks_unresolved_author_year_citation(service: ResearchAgentService):
    session = service.store.create_session()
    _manuscript(session)
    root = Path(session.workspace_root)
    manuscript = root / "paper/uploads/paper.md"
    manuscript.write_text(
        manuscript.read_text(encoding="utf-8").replace("Context [@known].", "Context (Jones, 2024)."),
        encoding="utf-8",
    )
    bibliography = root / "bib/uploads/references.bib"
    bibliography.write_text(
        "@article{known,author={Smith, Jane},year={2020},title={Known}}",
        encoding="utf-8",
    )

    result = run(service.chat(session.session_id, "/final-check"))
    task = service.get_task(result["task_id"])
    payload = json.loads(Path(task.artifact_root, "paper/FINAL_GATE_REPORT.json").read_text())

    check = next(item for item in payload["checks"] if item["check"] == "author_year_citations_resolve")
    assert payload["decision"] == "BLOCK"
    assert check["detail"] == ["Jones, 2024"]


def test_peer_review_accepts_claim_with_adjacent_citation(service: ResearchAgentService):
    session = service.store.create_session()
    _manuscript(session)
    path = Path(session.workspace_root, "paper/uploads/paper.md")
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "Method.",
            "Our method significantly outperforms all baselines.\nEvidence: [@known].",
        ),
        encoding="utf-8",
    )

    result = run(service.chat(session.session_id, "/peer-review"))
    task = service.get_task(result["task_id"])
    payload = json.loads(Path(task.artifact_root, "rebuttal/reviews/REVIEW_PACKAGE.json").read_text())

    assert not any(item["category"] == "claims" and item["severity"] == "major" for item in payload["findings"])


def test_peer_review_flags_quantitative_claim_without_evidence(service: ResearchAgentService):
    session = service.store.create_session()
    _manuscript(session)
    path = Path(session.workspace_root, "paper/uploads/paper.md")
    path.write_text(
        path.read_text(encoding="utf-8").replace("Method.", "Accuracy reached 97.3%."),
        encoding="utf-8",
    )

    result = run(service.chat(session.session_id, "/peer-review"))
    task = service.get_task(result["task_id"])
    payload = json.loads(Path(task.artifact_root, "rebuttal/reviews/REVIEW_PACKAGE.json").read_text())

    assert any(
        item["category"] == "claims"
        and item["severity"] == "major"
        and "Quantitative claim" in item["problem"]
        for item in payload["findings"]
    )


def test_final_check_blocks_unknown_key_without_bibliography(service: ResearchAgentService):
    session = service.store.create_session()
    _manuscript(session)
    root = Path(session.workspace_root)
    (root / "bib/uploads/references.bib").unlink()
    manuscript = root / "paper/uploads/paper.md"
    manuscript.write_text(manuscript.read_text(encoding="utf-8").replace("@known", "@unknown"), encoding="utf-8")

    result = run(service.chat(session.session_id, "/final-check"))
    task = service.get_task(result["task_id"])
    payload = json.loads(Path(task.artifact_root, "paper/FINAL_GATE_REPORT.json").read_text())

    citation_check = next(item for item in payload["checks"] if item["check"] == "citation_keys_resolve")
    assert payload["decision"] == "BLOCK"
    assert citation_check["detail"] == ["unknown"]


def test_extract_citations_ignores_email_and_bibtex_declaration():
    assert extract_citations("Contact research@example.com.\n@article{known,title={Known}}") == set()


def test_final_check_accepts_latex_section_commands(service: ResearchAgentService):
    session = service.store.create_session()
    root = Path(session.workspace_root)
    manuscript = root / "paper/uploads/paper.tex"
    manuscript.parent.mkdir(parents=True, exist_ok=True)
    manuscript.write_text(
        "\\section{Abstract}\nText.\n\\section{Introduction}\nContext.\n\\section{Method}\nMethod.\n\\section{Conclusion}\nDone.",
        encoding="utf-8",
    )

    result = run(service.chat(session.session_id, "/final-check"))
    task = service.get_task(result["task_id"])
    payload = json.loads(Path(task.artifact_root, "paper/FINAL_GATE_REPORT.json").read_text())

    section_check = next(item for item in payload["checks"] if item["check"] == "required_sections_present")
    assert section_check["status"] == "pass"


def test_final_check_flags_duplicate_figure_definitions(service: ResearchAgentService):
    session = service.store.create_session()
    _manuscript(session)
    manuscript = Path(session.workspace_root, "paper/uploads/paper.md")
    manuscript.write_text(
        manuscript.read_text(encoding="utf-8") + "\nFigure 1: First.\nFigure 1: Duplicate.",
        encoding="utf-8",
    )

    result = run(service.chat(session.session_id, "/final-check"))
    task = service.get_task(result["task_id"])
    payload = json.loads(Path(task.artifact_root, "paper/FINAL_GATE_REPORT.json").read_text())

    figure_check = next(item for item in payload["checks"] if item["check"] == "markdown_figure_numbering")
    assert figure_check["status"] == "violated"


def test_final_check_blocks_unknown_evidence_identifier(service: ResearchAgentService):
    session = service.store.create_session()
    _manuscript(session)
    manuscript = Path(session.workspace_root, "paper/uploads/paper.md")
    manuscript.write_text(
        manuscript.read_text(encoding="utf-8").replace("Method.", "Method evidence [PE-BOGUS]."),
        encoding="utf-8",
    )

    result = run(service.chat(session.session_id, "/final-check"))
    task = service.get_task(result["task_id"])
    payload = json.loads(Path(task.artifact_root, "paper/FINAL_GATE_REPORT.json").read_text())

    evidence_check = next(item for item in payload["checks"] if item["check"] == "evidence_ids_resolve")
    assert payload["decision"] == "BLOCK"
    assert evidence_check["detail"] == ["PE-BOGUS"]


def test_peer_review_does_not_accept_unknown_evidence_identifier(service: ResearchAgentService):
    session = service.store.create_session()
    _manuscript(session)
    manuscript = Path(session.workspace_root, "paper/uploads/paper.md")
    manuscript.write_text(
        manuscript.read_text(encoding="utf-8").replace("Method.", "Our method significantly outperforms baselines [PE-BOGUS]."),
        encoding="utf-8",
    )

    result = run(service.chat(session.session_id, "/peer-review"))
    task = service.get_task(result["task_id"])
    payload = json.loads(Path(task.artifact_root, "rebuttal/reviews/REVIEW_PACKAGE.json").read_text())

    assert any(item["category"] == "claims" and item["severity"] == "major" for item in payload["findings"])
