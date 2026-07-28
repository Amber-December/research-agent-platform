from __future__ import annotations

import json
import re
from pathlib import Path

from .connectors.scholar import LiteratureBundle
from .config import config


class ReviewEvidenceError(RuntimeError):
    pass


def clean_review_topic(objective: str) -> str:
    topic = re.sub(r"^\s*/review\b", "", objective, flags=re.I).strip()
    topic = re.sub(r"--[\w-]+(?:=|\s+)\S+", "", topic).strip()
    topic = re.sub(
        r"^(?:请|请帮我|帮我)?(?:写|做|整理|生成|调研|查找|检索)(?:一个|一份|一下)?(?:当前|最新)?",
        "",
        topic,
    ).strip()
    topic = re.sub(
        r"(?:相关的?|领域的?|方向的?)?(?:文献)?(?:综述|研究综述|研究进展|进展与展望|survey|review)\s*$",
        "",
        topic,
        flags=re.I,
    ).strip(" ，,。.;；")
    return topic or objective.strip()


def parse_review_queries(objective: str, research_brief: str) -> list[str]:
    topic = clean_review_topic(objective)
    candidates = [topic]
    candidates.extend(
        match.strip()
        for match in re.findall(
            r"(?mi)^\s*(?:[-*+]\s*)?Q\d+\s*[:：]\s*[`\"']?(.+?)[`\"']?\s*$",
            research_brief,
        )
    )
    if re.search(r"[A-Za-z]", topic):
        candidates.extend([f"{topic} review", f"{topic} systematic review"])
    return _deduplicate(candidates)[:6]


def review_quality_markdown(
    bundle: LiteratureBundle,
    *,
    local_sources: list[str],
    local_candidates: list[str] | None = None,
) -> str:
    quality = bundle.quality
    minimum_sources = max(1, config.review_minimum_sources)
    total_sources = int(bundle.quality.get("relevant_count", len(bundle.papers))) + len(local_sources)
    traceable_sources = int(bundle.quality.get("traceable_count", 0)) + len(local_sources)
    enough = review_evidence_is_sufficient(bundle, local_source_count=len(local_sources))
    lines = [
        "# Literature Retrieval Quality Report",
        "",
        f"- Topic: {bundle.query}",
        f"- Gate: {'PASS' if enough else 'FAIL'}",
        f"- Required minimum sources: {minimum_sources}",
        f"- Admitted sources: {total_sources}",
        f"- Traceable sources: {traceable_sources}",
        f"- Retrieval status: {quality.get('status', 'unknown')}",
        f"- Candidate records: {quality.get('candidate_count', 0)}",
        f"- Relevant records before cap: {quality.get('eligible_count', quality.get('relevant_count', 0))}",
        f"- Relevant records retained: {quality.get('relevant_count', 0)}",
        f"- Relevant records omitted by cap: {quality.get('truncated_count', 0)}",
        f"- Irrelevant records excluded: {bundle.excluded_count}",
        f"- Traceable records: {quality.get('traceable_count', 0)}",
        f"- Local candidates discovered: {len(local_candidates or local_sources)}",
        f"- Local sources with extracted evidence: {len(local_sources)}",
        "",
        "## Query Plan",
    ]
    lines.extend(f"- {query}" for query in bundle.queries)
    lines.extend(["", "## Provider Coverage"])
    lines.extend(f"- {provider}: {status}" for provider, status in bundle.provider_status.items())
    lines.extend(["", "## Local Sources"])
    lines.extend(f"- `{source}`" for source in local_sources)
    if not local_sources:
        lines.append("- None")
    lines.extend(["", "## Gate Decision"])
    if enough:
        lines.append("- Evidence is sufficient for a traceable synthesis. Coverage limitations must still be disclosed.")
    else:
        lines.append(
            "- Evidence is insufficient for a formal review. Do not generate a literature synthesis, evidence map, or research-gap claim from this retrieval."
        )
        lines.append("- Add local papers or restore another scholarly provider, then rerun `/review`.")
    return "\n".join(lines) + "\n"


def review_evidence_is_sufficient(
    bundle: LiteratureBundle,
    *,
    local_source_count: int = 0,
    minimum_sources: int | None = None,
) -> bool:
    relevant_count = int(bundle.quality.get("relevant_count", len(bundle.papers)))
    traceable_count = int(bundle.quality.get("traceable_count", 0))
    required = max(1, minimum_sources if minimum_sources is not None else config.review_minimum_sources)
    return relevant_count + local_source_count >= required and traceable_count + local_source_count >= required


def build_review_quality_reports(workspace_root: Path) -> tuple[dict, dict]:
    bundle_path = workspace_root / "bib" / "LITERATURE_SEARCH.json"
    payload = json.loads(bundle_path.read_text(encoding="utf-8")) if bundle_path.exists() else {}
    papers = payload.get("papers") if isinstance(payload.get("papers"), list) else []
    known_ids = {str(paper.get("paper_id", "")) for paper in papers if paper.get("paper_id")}
    traceable_ids = {
        str(paper.get("paper_id", ""))
        for paper in papers
        if paper.get("paper_id") and paper.get("verification_status") == "traceable_identifier"
    }
    quality = payload.get("quality") if isinstance(payload.get("quality"), dict) else {}
    local_sources = {
        str(source)
        for source in quality.get("local_evidence_sources", [])
        if isinstance(source, str) and source
    }
    file_citations: dict[str, list[str]] = {}
    file_local_citations: dict[str, list[str]] = {}
    for relative in (
        "bib/LITERATURE_REVIEW.md",
        "bib/EVIDENCE_MAP.md",
        "bib/RESEARCH_GAPS.md",
    ):
        path = workspace_root / relative
        text = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
        file_citations[relative] = sorted(set(re.findall(r"\bP\d{3}\b", text)))
        file_local_citations[relative] = sorted(source for source in local_sources if source in text)
    used_ids = set(identifier for citations in file_citations.values() for identifier in citations)
    used_local_sources = set(source for citations in file_local_citations.values() for source in citations)
    unknown_ids = sorted(used_ids - known_ids)
    uncited_ids = sorted(known_ids - used_ids)
    citation_audit = {
        "known_paper_ids": sorted(known_ids),
        "file_citations": file_citations,
        "known_local_sources": sorted(local_sources),
        "file_local_citations": file_local_citations,
        "unknown_paper_ids": unknown_ids,
        "uncited_paper_ids": uncited_ids,
        "status": "pass" if (known_ids or local_sources) and not unknown_ids else "needs_attention",
        "note": "ID resolution is deterministic; semantic claim support still requires author verification.",
    }
    source_count = len(known_ids) + len(local_sources)
    cited_source_count = len(used_ids & known_ids) + len(used_local_sources)
    traceable_source_count = len(traceable_ids) + len(local_sources)
    coverage_ratio = round(cited_source_count / source_count, 3) if source_count else 0.0
    traceable_ratio = round(traceable_source_count / source_count, 3) if source_count else 0.0
    coverage_report = {
        "retrieval_quality": quality,
        "paper_count": source_count,
        "external_paper_count": len(known_ids),
        "local_source_count": len(local_sources),
        "cited_paper_count": cited_source_count,
        "reference_coverage": coverage_ratio,
        "traceable_paper_ratio": traceable_ratio,
        "provider_status": payload.get("provider_status", {}),
        "status": (
            "pass"
            if source_count >= max(1, config.review_minimum_sources)
            and not unknown_ids
            and coverage_ratio >= 0.4
            and traceable_ratio >= 0.8
            else "needs_attention"
        ),
        "limitations": [
            "Metadata and abstracts do not replace full-text verification.",
            "Coverage reflects configured providers and local uploads only.",
        ],
    }
    return citation_audit, coverage_report


def _deduplicate(values: list[str]) -> list[str]:
    results: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = " ".join(value.split()).strip(" `\"'，,。.;；")
        key = cleaned.casefold()
        if cleaned and key not in seen:
            results.append(cleaned)
            seen.add(key)
    return results
