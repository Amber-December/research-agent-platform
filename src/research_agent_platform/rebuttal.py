from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from .models import RebuttalSourceConfig, UploadBatchRecord


REBUTTAL_DOCUMENT_EXTENSIONS = {
    ".docx",
    ".html",
    ".md",
    ".pdf",
    ".rst",
    ".tex",
    ".txt",
}
REVIEW_TERMS = (
    "review",
    "reviewer",
    "referee",
    "decision_letter",
    "审稿",
    "评审",
    "审阅意见",
    "修改意见",
)
GENERATED_REBUTTAL_FILES = {
    "REBUTTAL_INPUTS.md",
    "REVIEW_TO_PAPER_MAP.md",
    "RESPONSE_STRATEGY.md",
    "REBUTTAL_DRAFT.md",
    "REVISION_PLAN.md",
    "REVISION_LEDGER.md",
    "REBUTTAL_CLOSURE_REPORT.json",
}


class RebuttalInputError(ValueError):
    pass


def resolve_rebuttal_source_config(
    objective: str,
    workspace_root: Path,
    upload_batches: Iterable[UploadBatchRecord] = (),
) -> RebuttalSourceConfig:
    explicit_papers = _extract_flag_refs(objective, workspace_root, "paper")
    explicit_reviews = _extract_flag_refs(objective, workspace_root, "review(?:s)?")
    explicit_refs = _extract_general_refs(objective, workspace_root)
    explicit_papers.extend(
        ref for ref in explicit_refs if _source_role(ref) == "paper" and ref not in explicit_papers
    )
    explicit_reviews.extend(
        ref for ref in explicit_refs if _source_role(ref) == "review" and ref not in explicit_reviews
    )

    batches = list(upload_batches)
    paper_batch_id = ""
    review_batch_id = ""
    if explicit_papers:
        paper_refs = explicit_papers
        paper_reason = "用户在 /rebuttal 指令中明确指定了完成稿。"
    else:
        paper_refs, paper_batch_id = _latest_batch_sources(batches, workspace_root, "paper")
        if paper_refs:
            paper_reason = "采用当前会话最近上传的论文完成稿。"
        else:
            paper_refs = _workspace_paper_sources(workspace_root)
            paper_reason = "未显式指定完成稿，采用 paper/ 中名称明确标记为 final/accepted/终稿/定稿的最新材料。"

    if explicit_reviews:
        review_refs = explicit_reviews
        review_reason = "用户在 /rebuttal 指令中明确指定了审稿意见。"
    else:
        review_refs, review_batch_id = _latest_batch_sources(batches, workspace_root, "review")
        if review_refs:
            review_reason = "采用当前会话最近上传的审稿意见。"
        else:
            review_refs = _workspace_review_sources(workspace_root)
            review_reason = "未显式指定审稿意见，采用 rebuttal/uploads/ 中最新的审稿材料。"

    if not paper_refs or not review_refs:
        missing = []
        if not paper_refs:
            missing.append("完成后的论文（PDF、DOCX、Markdown 或 TeX）")
        if not review_refs:
            missing.append("审稿人意见（建议文件名包含 review/reviewer/审稿/评审，或上传到 rebuttal）")
        raise RebuttalInputError(
            "/rebuttal 必须同时提供论文完成稿和审稿意见。当前缺少：" + "；".join(missing) + "。"
        )

    batch_ids = _deduplicate(value for value in (paper_batch_id, review_batch_id) if value)
    return RebuttalSourceConfig(
        paper_refs=paper_refs,
        review_refs=review_refs,
        paper_selection_reason=paper_reason,
        review_selection_reason=review_reason,
        upload_batch_ids=batch_ids,
    )


def rebuttal_inputs_markdown(config: RebuttalSourceConfig) -> str:
    return (
        "# Rebuttal Inputs\n\n"
        "## Validation\n\n"
        "- Status: ready\n"
        "- Input contract: completed paper plus reviewer comments\n"
        "- Source boundary: frozen when the task starts\n\n"
        "## Completed Paper\n\n"
        f"- Selection: {config.paper_selection_reason}\n"
        + "\n".join(f"- `{path}`" for path in config.paper_refs)
        + "\n\n## Reviewer Comments\n\n"
        f"- Selection: {config.review_selection_reason}\n"
        + "\n".join(f"- `{path}`" for path in config.review_refs)
        + "\n\n## Required Analysis\n\n"
        "- Map every reviewer comment to the relevant paper section, claim, figure, table, or evidence.\n"
        "- Keep reviewer wording, paper wording, proposed response, and promised revision distinguishable.\n"
        "- Do not infer missing paper content or reviewer comments from the task objective.\n"
    )


def build_rebuttal_closure_report(workspace_root: Path) -> dict:
    artifact_paths = {
        "map": "rebuttal/REVIEW_TO_PAPER_MAP.md",
        "strategy": "rebuttal/RESPONSE_STRATEGY.md",
        "response": "rebuttal/REBUTTAL_DRAFT.md",
        "plan": "rebuttal/REVISION_PLAN.md",
        "ledger": "rebuttal/REVISION_LEDGER.md",
        "revised_manuscript": "paper/PAPER_REVISED_AFTER_REVIEW.md",
    }
    contents = {
        name: _read(workspace_root / relative)
        for name, relative in artifact_paths.items()
    }
    comment_ids = extract_comment_ids(contents["map"]) or extract_comment_ids(contents["response"])
    coverage: list[dict] = []
    for comment_id in comment_ids:
        ledger_line = _line_for_comment(contents["ledger"], comment_id)
        coverage.append(
            {
                "comment_id": comment_id,
                "mapped": _contains_id(contents["map"], comment_id),
                "strategy_present": _contains_id(contents["strategy"], comment_id),
                "response_present": _contains_id(contents["response"], comment_id),
                "revision_plan_present": _contains_id(contents["plan"], comment_id),
                "ledger_present": bool(ledger_line),
                "declared_revision_status": _declared_revision_status(ledger_line),
            }
        )
    required_keys = (
        "mapped",
        "strategy_present",
        "response_present",
        "revision_plan_present",
        "ledger_present",
    )
    incomplete = [
        row["comment_id"] for row in coverage if not all(row[key] for key in required_keys)
    ]
    unresolved = [
        row["comment_id"]
        for row in coverage
        if row["declared_revision_status"] in {"planned", "unresolved", "unknown"}
    ]
    findings = [
        _closure_finding(
            "comment_ids_detected",
            bool(comment_ids),
            "hard",
            f"{len(comment_ids)} stable comment IDs detected.",
        ),
        _closure_finding(
            "point_by_point_coverage",
            not incomplete,
            "hard",
            "Incomplete IDs: " + ", ".join(incomplete)
            if incomplete
            else "Every ID crosses all response artifacts.",
        ),
        _closure_finding(
            "revised_manuscript_exists",
            bool(contents["revised_manuscript"].strip()),
            "hard",
            artifact_paths["revised_manuscript"],
        ),
        {
            "check": "unresolved_or_planned_changes",
            "status": "warning" if unresolved else "pass",
            "severity": "soft",
            "detail": "Author verification required for: " + ", ".join(unresolved)
            if unresolved
            else "No unresolved ledger status detected.",
        },
    ]
    hard_violations = [
        item for item in findings if item["severity"] == "hard" and item["status"] == "violated"
    ]
    return {
        "status": "pass" if not hard_violations else "needs_attention",
        "comment_count": len(comment_ids),
        "hard_violations": len(hard_violations),
        "coverage": coverage,
        "findings": findings,
        "artifact_paths": artifact_paths,
        "verification_boundary": (
            "This gate verifies identifier coverage and declared status. Semantic correctness, new experimental "
            "results, exact manuscript edits, and reviewer satisfaction require author verification."
        ),
    }


def extract_comment_ids(content: str) -> list[str]:
    results: list[str] = []
    patterns = (
        r"\bR(?:eviewer)?\s*(\d+)\s*[.\-_:]?\s*C(?:omment)?\s*(\d+)\b",
        r"\bR(\d+)\s*[.\-_:]\s*(\d+)\b",
    )
    for pattern in patterns:
        for reviewer, comment in re.findall(pattern, content, re.I):
            normalized = f"R{int(reviewer)}.C{int(comment)}"
            if normalized not in results:
                results.append(normalized)
    return results


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def _contains_id(content: str, comment_id: str) -> bool:
    return comment_id.lower() in content.lower()


def _line_for_comment(content: str, comment_id: str) -> str:
    normalized = comment_id.lower()
    matches = [line.strip() for line in content.splitlines() if normalized in line.lower()]
    return next(
        (
            line
            for line in matches
            if re.search(
                r"\bstatus\b|implemented|planned|unresolved|已完成|已修改|已落实|待执行|计划|承诺|未解决|待确认",
                line,
                re.I,
            )
        ),
        matches[0] if matches else "",
    )


def _declared_revision_status(line: str) -> str:
    lowered = line.lower()
    if any(term in lowered for term in ("implemented", "completed", "applied", "已完成", "已修改", "已落实")):
        return "implemented"
    if any(term in lowered for term in ("planned", "committed", "待执行", "计划", "承诺")):
        return "planned"
    if any(term in lowered for term in ("unresolved", "blocked", "无法", "未解决", "待确认")):
        return "unresolved"
    return "unknown"


def _closure_finding(check: str, passed: bool, severity: str, detail: str) -> dict:
    return {
        "check": check,
        "status": "pass" if passed else "violated",
        "severity": severity,
        "detail": detail,
    }


def _latest_batch_sources(
    batches: list[UploadBatchRecord], workspace_root: Path, role: str
) -> tuple[list[str], str]:
    for batch in reversed(batches):
        refs = [
            ref
            for ref in batch.relative_paths
            if _valid_source(workspace_root, ref) and _source_role(ref) == role
        ]
        if refs:
            return refs, batch.upload_batch_id
    return [], ""


def _workspace_paper_sources(workspace_root: Path) -> list[str]:
    directory = workspace_root / "paper"
    candidates = [
        path
        for path in directory.rglob("*")
        if path.is_file()
        and path.suffix.lower() in REBUTTAL_DOCUMENT_EXTENSIONS
        and not _looks_like_review(path.name)
        and _looks_like_final_paper(path.name)
    ] if directory.exists() else []
    candidates.sort(key=lambda path: (_paper_rank(path), -path.stat().st_mtime_ns))
    return [candidates[0].relative_to(workspace_root).as_posix()] if candidates else []


def _workspace_review_sources(workspace_root: Path) -> list[str]:
    upload_directory = workspace_root / "rebuttal" / "uploads"
    candidates = [
        path
        for path in upload_directory.rglob("*")
        if path.is_file() and path.suffix.lower() in REBUTTAL_DOCUMENT_EXTENSIONS
    ] if upload_directory.exists() else []
    for path in workspace_root.glob("*/uploads/*"):
        if (
            path.is_file()
            and path.suffix.lower() in REBUTTAL_DOCUMENT_EXTENSIONS
            and _looks_like_review(path.name)
            and path not in candidates
        ):
            candidates.append(path)
    candidates.sort(key=lambda path: path.stat().st_mtime_ns, reverse=True)
    return [path.relative_to(workspace_root).as_posix() for path in candidates]


def _paper_rank(path: Path) -> int:
    lowered = path.stem.lower()
    if any(term in lowered for term in ("final", "accepted", "camera", "终稿", "定稿", "完成稿")):
        return 0
    if path.parent.name == "uploads":
        return 1
    return 2


def _looks_like_final_paper(filename: str) -> bool:
    lowered = Path(filename).stem.lower()
    return any(
        term in lowered
        for term in (
            "final",
            "accepted",
            "camera_ready",
            "camera-ready",
            "终稿",
            "定稿",
            "完成稿",
            "最终稿",
        )
    )


def _source_role(relative: str) -> str:
    normalized = relative.replace("\\", "/")
    if normalized.startswith("rebuttal/uploads/") or _looks_like_review(Path(normalized).name):
        return "review"
    if normalized.startswith("paper/"):
        return "paper"
    return ""


def _looks_like_review(filename: str) -> bool:
    lowered = Path(filename).stem.lower()
    return any(term in lowered for term in REVIEW_TERMS)


def _extract_flag_refs(objective: str, workspace_root: Path, flag: str) -> list[str]:
    pattern = rf"--{flag}(?:=|\s+)(`[^`]+`|\"[^\"]+\"|'[^']+'|\S+)"
    values = [match.strip("`\"'").rstrip(".,，。;；") for match in re.findall(pattern, objective, re.I)]
    return _resolve_refs(values, workspace_root)


def _extract_general_refs(objective: str, workspace_root: Path) -> list[str]:
    candidates = re.findall(
        r"(?:`([^`]+)`|[\"']([^\"']+)[\"']|(?<![\w.-])((?:paper|rebuttal)[/\\][^\s,，;；]+))",
        objective,
        re.I,
    )
    return _resolve_refs(
        [next((group for group in groups if group), "").rstrip(".,，。;；)") for groups in candidates],
        workspace_root,
    )


def _resolve_refs(values: Iterable[str], workspace_root: Path) -> list[str]:
    refs: list[str] = []
    root = workspace_root.resolve()
    for value in values:
        if not value:
            continue
        normalized = value.replace("\\", "/").lstrip("./")
        target = (workspace_root / normalized).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            continue
        if target.is_file() and target.suffix.lower() in REBUTTAL_DOCUMENT_EXTENSIONS:
            relative = target.relative_to(root).as_posix()
            if relative not in refs:
                refs.append(relative)
    return refs


def _valid_source(workspace_root: Path, relative: str) -> bool:
    path = workspace_root / relative
    return (
        path.is_file()
        and path.suffix.lower() in REBUTTAL_DOCUMENT_EXTENSIONS
        and path.name not in GENERATED_REBUTTAL_FILES
    )


def _deduplicate(values: Iterable[str]) -> list[str]:
    results: list[str] = []
    for value in values:
        if value not in results:
            results.append(value)
    return results
