from __future__ import annotations

import json
import re
from pathlib import Path
from collections import Counter


def extract_citations(manuscript: str) -> set[str]:
    keys = set(re.findall(r"(?<![A-Za-z0-9_@])@([A-Za-z0-9_:-]+)(?![A-Za-z0-9_:-]*\s*\{)", manuscript))
    for group in re.findall(r"\\cite\w*\{([^}]+)\}", manuscript):
        keys.update(key.strip() for key in group.split(",") if key.strip())
    return keys


def find_author_year_citations(manuscript: str) -> list[str]:
    citations: set[str] = set()
    for group in re.findall(r"\(([^()\n]+)\)", manuscript):
        for candidate in group.split(";"):
            match = re.fullmatch(
                r"\s*([A-Z][A-Za-z'’-]+)(?:\s+et al\.)?,?\s+(\d{4}[a-z]?)\s*",
                candidate,
            )
            if match:
                citations.add(f"{match.group(1)}, {match.group(2)}")
    return sorted(citations)


def extract_bibliography_author_years(bibliography: str) -> set[tuple[str, str]]:
    signatures: set[tuple[str, str]] = set()
    entries = re.split(r"(?=@[A-Za-z]+\s*\{)", bibliography)
    for entry in entries:
        author_match = re.search(r"\bauthor\s*=\s*[\{\"]([^}\"]+)", entry, re.I)
        year_match = re.search(r"\byear\s*=\s*[\{\"]?(\d{4}[a-z]?)", entry, re.I)
        if not author_match or not year_match:
            continue
        first_author = re.split(r"\s+and\s+", author_match.group(1), maxsplit=1, flags=re.I)[0]
        surname = first_author.split(",", 1)[0] if "," in first_author else first_author.split()[-1]
        normalized_surname = re.sub(r"[^A-Za-z]", "", surname).lower()
        if normalized_surname:
            signatures.add((normalized_surname, year_match.group(1).lower()))
    return signatures


def _author_year_signature(citation: str) -> tuple[str, str]:
    author, year = citation.split(", ", 1)
    return re.sub(r"[^A-Za-z]", "", author).lower(), year.lower()


def _has_nearby_evidence(
    lines: list[str],
    line_index: int,
    citation_keys: set[str] | None = None,
    evidence_ids: set[str] | None = None,
) -> bool:
    support_pattern = re.compile(
        r"@[A-Za-z0-9_:-]+|\[PE-[A-Z0-9]+\]|\\cite\w*\{|\([A-Z][A-Za-z'’-]+(?:\s+et al\.)?,?\s+\d{4}[a-z]?\)|\b(?:Figure|Fig\.|Table)\s+\d+\b",
        re.I,
    )
    start = max(0, line_index - 1)
    end = min(len(lines), line_index + 2)
    for line in lines[start:end]:
        if citation_keys is None and re.search(r"@[A-Za-z0-9_:-]+", line):
            return True
        if citation_keys is not None and any(key in citation_keys for key in re.findall(r"@([A-Za-z0-9_:-]+)", line)):
            return True
        if evidence_ids is None and re.search(r"\bPE-[A-Z0-9-]+\b", line, re.I):
            return True
        if evidence_ids is not None and any(
            evidence_id.upper() in evidence_ids
            for evidence_id in re.findall(r"\bPE-[A-Z0-9-]+\b", line, re.I)
        ):
            return True
        if support_pattern.search(line) and not re.search(r"@[A-Za-z0-9_:-]+|\bPE-[A-Z0-9-]+\b", line, re.I):
            return True
    return False


def _section_present(manuscript: str, section: str) -> bool:
    escaped = re.escape(section)
    return bool(
        re.search(rf"^#+\s+.*{escaped}", manuscript, re.I | re.M)
        or re.search(rf"\\(?:sub)*section\*?\{{[^}}]*{escaped}[^}}]*\}}", manuscript, re.I)
    )


def find_manuscript(workspace_root: Path) -> tuple[str, str]:
    allowed_directories = ("paper", "Content")
    candidates = sorted(
        (
            path
            for directory in allowed_directories
            for path in (workspace_root / directory).rglob("*")
            if path.is_file()
            and path.suffix.lower() in {".md", ".txt", ".tex"}
            and path.name not in {"MANIFEST.md"}
        ),
        key=lambda path: (
            path.parts[-3] != "paper",
            "revised" not in path.name.lower(),
            path.name.lower(),
        ),
    )
    if not candidates:
        raise ValueError("缺少可审阅的稿件；请上传 Markdown、TXT 或 LaTeX 稿件，或先完成 /write。")
    path = candidates[0]
    return path.relative_to(workspace_root).as_posix(), path.read_text(encoding="utf-8", errors="ignore")


def build_review_package(manuscript_path: str, manuscript: str, workspace_root: Path | None = None) -> dict:
    findings: list[dict] = []
    required_sections = ("abstract", "introduction", "method", "conclusion")
    for section in required_sections:
        if not _section_present(manuscript, section):
            findings.append(_finding("structure", "major", "whole manuscript", f"Missing required section: {section.title()}.", "Add a bounded section supported by the frozen evidence."))
    manuscript_lines = manuscript.splitlines()
    for line_no, line in enumerate(manuscript_lines, start=1):
        if re.search(r"AUTHOR INPUT NEEDED|TODO|PLACEHOLDER|CITATION NEEDED", line, re.I):
            findings.append(_finding("evidence", "major", f"line {line_no}", "Unresolved author input or placeholder remains.", "Resolve it with traceable evidence or retain it as an explicit limitation before submission."))
    if not extract_citations(manuscript) and not find_author_year_citations(manuscript):
        findings.append(_finding("citations", "minor", "whole manuscript", "No machine-readable citation keys were found.", "Verify that references are complete and use the target venue citation convention."))
    citation_keys: set[str] | None = None
    evidence_ids: set[str] | None = None
    if workspace_root is not None:
        citation_keys = set()
        evidence_ids = set()
        for path in (workspace_root / "bib").rglob("*.bib"):
            citation_keys.update(
                re.findall(r"@\w+\s*\{\s*([^,\s]+)", path.read_text(encoding="utf-8", errors="ignore"))
            )
        evidence_map_path = workspace_root / "paper" / "PAPER_EVIDENCE_MAP.json"
        if evidence_map_path.exists():
            try:
                records = json.loads(evidence_map_path.read_text(encoding="utf-8"))
                if isinstance(records, list):
                    evidence_ids.update(
                        str(record.get("evidence_id", "")).upper()
                        for record in records
                        if isinstance(record, dict) and record.get("evidence_id")
                    )
            except json.JSONDecodeError:
                pass
    for line_no, line in enumerate(manuscript_lines, start=1):
        if re.search(r"\b(?:improve(?:s|d)?|outperform(?:s|ed)?|state-of-the-art|significant(?:ly)?|universal|always|never|prove(?:s|d)?)\b", line, re.I) and not _has_nearby_evidence(manuscript_lines, line_no - 1, citation_keys, evidence_ids):
            findings.append(_finding("claims", "major", f"line {line_no}", "Comparative or strong claim lacks a local citation or evidence identifier.", "Attach a source citation or frozen evidence ID, or narrow the claim."))
        if re.search(r"(?:\b\d+(?:\.\d+)?\s*%|\bp\s*[<=>]\s*0?\.\d+|\b(?:confidence interval|CI)\b)", line, re.I) and not _has_nearby_evidence(manuscript_lines, line_no - 1, citation_keys, evidence_ids):
            findings.append(_finding("claims", "major", f"line {line_no}", "Quantitative claim lacks a nearby citation, evidence identifier, or figure/table reference.", "Attach traceable evidence near the value or mark it as unresolved author input."))
        if len(line) > 280:
            findings.append(_finding("language-format", "minor", f"line {line_no}", "Sentence or paragraph line is unusually long.", "Split it into shorter claim-evidence-reasoning units."))
    if not _section_present(manuscript, "limitations") and not re.search(r"(?im)^#+\s+讨论", manuscript):
        findings.append(_finding("claims", "minor", "whole manuscript", "No explicit limitations section was found.", "State scope, uncertainty, and unsupported future work explicitly."))
    reviewers = ("editor", "domain", "methods", "evidence", "adversarial", "language-format")
    for index, finding in enumerate(findings, start=1):
        finding["finding_id"] = f"F{index:03d}"
        finding["reviewers"] = [reviewers[(index - 1) % len(reviewers)]]
    decision = "REVISE" if any(item["severity"] == "major" for item in findings) else "PASS"
    return {"review_mode": "simulated-peer-review", "manuscript_path": manuscript_path, "decision": decision, "findings": findings, "limitations": ["This is an automated simulated review, not a journal decision."]}


def build_final_gate_report(manuscript_path: str, manuscript: str, workspace_root: Path) -> dict:
    bibliography_keys: set[str] = set()
    bibliography_author_years: set[tuple[str, str]] = set()
    for path in (workspace_root / "bib").rglob("*.bib"):
        bibliography = path.read_text(encoding="utf-8", errors="ignore")
        bibliography_keys.update(re.findall(r"@\w+\s*\{\s*([^,\s]+)", bibliography))
        bibliography_author_years.update(extract_bibliography_author_years(bibliography))
    cited = extract_citations(manuscript)
    unknown = sorted(cited - bibliography_keys)
    author_year_citations = find_author_year_citations(manuscript)
    unknown_author_years = sorted(
        citation
        for citation in author_year_citations
        if _author_year_signature(citation) not in bibliography_author_years
    )
    known_evidence_ids: set[str] = set()
    evidence_map_path = workspace_root / "paper" / "PAPER_EVIDENCE_MAP.json"
    if evidence_map_path.exists():
        try:
            evidence_records = json.loads(evidence_map_path.read_text(encoding="utf-8"))
            if isinstance(evidence_records, list):
                known_evidence_ids.update(
                    str(record.get("evidence_id", "")).upper()
                    for record in evidence_records
                    if isinstance(record, dict) and record.get("evidence_id")
                )
        except json.JSONDecodeError:
            pass
    referenced_evidence_ids = {value.upper() for value in re.findall(r"\bPE-[A-Z0-9-]+\b", manuscript, re.I)}
    unknown_evidence_ids = sorted(referenced_evidence_ids - known_evidence_ids)
    placeholders = sorted({match.group(0) for match in re.finditer(r"AUTHOR INPUT NEEDED|TODO|PLACEHOLDER|CITATION NEEDED", manuscript, re.I)})
    labels = set(re.findall(r"\\label\{([^}]+)\}", manuscript))
    references = set(re.findall(r"\\(?:ref|autoref|cref|Cref)\{([^}]+)\}", manuscript))
    figure_mentions = [int(value) for value in re.findall(r"(?i)\b(?:figure|fig\.)\s+(\d+)\b", manuscript)]
    table_mentions = [int(value) for value in re.findall(r"(?i)\btable\s+(\d+)\b", manuscript)]
    figure_definitions = [int(value) for value in re.findall(r"(?im)^\s*(?:figure|fig\.)\s+(\d+)\s*[:.]", manuscript)]
    table_definitions = [int(value) for value in re.findall(r"(?im)^\s*table\s+(\d+)\s*[:.]", manuscript)]
    def numbering_issues(values: list[int], definitions: list[int]) -> dict:
        counts = Counter(values)
        expected = set(range(1, max(values) + 1)) if values else set()
        definition_counts = Counter(definitions)
        return {
            "missing": sorted(expected - set(values)),
            "duplicate": sorted(value for value, count in definition_counts.items() if count > 1),
        }
    figure_issues = numbering_issues(figure_mentions, figure_definitions)
    table_issues = numbering_issues(table_mentions, table_definitions)
    required_sections = ("abstract", "introduction", "method", "conclusion")
    missing_sections = [
        section
        for section in required_sections
        if not _section_present(manuscript, section)
    ]
    checks = [
        {"check": "manuscript_present", "status": "pass" if manuscript.strip() else "violated", "severity": "hard"},
        {"check": "citation_keys_resolve", "status": "violated" if unknown else "pass", "severity": "hard", "detail": unknown},
        {"check": "author_year_citations_resolve", "status": "violated" if unknown_author_years else "pass", "severity": "hard", "detail": unknown_author_years},
        {"check": "evidence_ids_resolve", "status": "violated" if unknown_evidence_ids else "pass", "severity": "hard", "detail": unknown_evidence_ids},
        {"check": "placeholders_resolved", "status": "violated" if placeholders else "pass", "severity": "soft", "detail": placeholders},
        {"check": "latex_cross_references_resolve", "status": "violated" if references - labels else "pass", "severity": "hard", "detail": sorted(references - labels)},
        {"check": "required_sections_present", "status": "violated" if missing_sections else "pass", "severity": "hard", "detail": missing_sections},
        {"check": "markdown_figure_numbering", "status": "violated" if figure_issues["missing"] or figure_issues["duplicate"] else "pass", "severity": "soft", "detail": figure_issues},
        {"check": "markdown_table_numbering", "status": "violated" if table_issues["missing"] or table_issues["duplicate"] else "pass", "severity": "soft", "detail": table_issues},
    ]
    hard = any(check["status"] == "violated" and check["severity"] == "hard" for check in checks)
    soft = any(check["status"] == "violated" and check["severity"] == "soft" for check in checks)
    return {"manuscript_path": manuscript_path, "decision": "BLOCK" if hard else "REVISE" if soft else "PASS", "checks": checks}


def to_markdown(title: str, payload: dict) -> str:
    return f"# {title}\n\n```json\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n```\n"


def build_writing_context(task_objective: str, source_refs: list[str], venue_profile: dict) -> dict:
    lowered = task_objective.lower()
    language = "zh" if re.search(r"中文|汉语|chinese", lowered) else "en"
    article_type = "review" if re.search(r"综述|survey|review article", lowered) else "research"
    disciplines = {
        "ai": ("ai", "computer science", "机器学习", "人工智能"),
        "medicine": ("medicine", "clinical", "医学", "临床"),
        "life": ("life science", "biology", "生命科学", "生物"),
    }
    discipline = "general"
    for name, terms in disciplines.items():
        if any(term in lowered for term in terms):
            discipline = name
            break
    return {
        "schema_version": "writing-context/v1",
        "language": language,
        "article_type": article_type,
        "discipline": discipline,
        "venue_profile": venue_profile,
        "source_boundary": "frozen_at_task_start",
        "source_refs": source_refs,
        "rules": [
            "Evidence precedes prose; unsupported claims remain AUTHOR INPUT NEEDED.",
            "Preserve supplied numbers, equations, citation keys, figures, and tables.",
            "Keep demonstrated results separate from intended contributions and future work.",
        ],
    }


def build_revision_audit(original: str, revised: str) -> dict:
    original_lines = original.splitlines()
    revised_lines = revised.splitlines()
    changed = sum(1 for before, after in zip(original_lines, revised_lines) if before != after)
    changed += abs(len(original_lines) - len(revised_lines))
    original_numbers = re.findall(r"\b\d+(?:\.\d+)?%?\b", original)
    revised_numbers = re.findall(r"\b\d+(?:\.\d+)?%?\b", revised)
    return {
        "schema_version": "revision-audit/v1",
        "changed_line_count": changed,
        "original_line_count": len(original_lines),
        "revised_line_count": len(revised_lines),
        "numbers_preserved": sorted(original_numbers) == sorted(revised_numbers),
        "citation_keys_preserved": sorted(re.findall(r"@([A-Za-z0-9_:-]+)", original)) == sorted(re.findall(r"@([A-Za-z0-9_:-]+)", revised)),
        "unresolved_author_inputs": sorted(set(re.findall(r"AUTHOR INPUT NEEDED[^\n]*", revised, re.I))),
    }


def _finding(category: str, severity: str, location: str, problem: str, action: str) -> dict:
    return {"finding_id": "", "category": category, "severity": severity, "location": location, "problem": problem, "impact": "May weaken the manuscript's traceability or submission readiness.", "recommended_action": action, "reviewers": []}
