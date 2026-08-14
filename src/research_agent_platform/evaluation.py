from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RubricDimension:
    name: str
    weight: int
    description: str


RUBRIC = (
    RubricDimension("evidence_faithfulness", 25, "数字、结论和证据边界是否保真"),
    RubricDimension("structure", 20, "核心章节和论证结构是否完整"),
    RubricDimension("citation_closure", 20, "引用键是否可解析且能闭合"),
    RubricDimension("actionability", 20, "问题和修改建议是否具体、可执行、可定位"),
    RubricDimension("risk_disclosure", 15, "限制、未决项和审阅边界是否明确"),
)


def _violated_checks(payload: dict, severity: str) -> list[dict]:
    return [
        check
        for check in payload.get("checks") or []
        if check.get("severity") == severity and check.get("status") == "violated"
    ]


def evaluate_review_package(payload: dict, manuscript: str = "", final_payload: dict | None = None) -> dict:
    findings = payload.get("findings") or []
    final_payload = final_payload or {}
    hard_violations = _violated_checks(final_payload, "hard")
    soft_violations = _violated_checks(final_payload, "soft")
    major_findings = [item for item in findings if item.get("severity") == "major"]
    scores = {dimension.name: 0 for dimension in RUBRIC}
    scores["structure"] = 20 if not any(item.get("category") == "structure" and item.get("severity") == "major" for item in findings) and not any(check.get("check") == "required_sections_present" for check in hard_violations) else 8
    scores["citation_closure"] = 20 if not any(item.get("category") == "citations" and item.get("severity") == "major" for item in findings) and not any(check.get("check") == "citation_keys_resolve" for check in hard_violations) else 8
    complete = [item for item in findings if item.get("location") and item.get("severity") and item.get("recommended_action")]
    scores["actionability"] = min(20, round(20 * len(complete) / max(1, len(findings)))) if findings else 0
    scores["risk_disclosure"] = 15 if re.search(r"(?im)^#+\s+(limitations?|讨论)", manuscript) else 4
    unsupported_claim = bool(re.search(r"\b(?:universal|always|never|outperform(?:s|ed)?|significant(?:ly)?|prove(?:s|d)?)\b", manuscript, re.I))
    evidence_major = any(item.get("category") in {"claims", "evidence"} for item in major_findings)
    scores["evidence_faithfulness"] = 8 if "AUTHOR INPUT NEEDED" in manuscript.upper() or unsupported_claim or evidence_major else 25
    raw_total = sum(scores.values())
    ceiling = 100
    ceiling_reason = None
    if hard_violations:
        ceiling, ceiling_reason = 49, "unresolved hard final-gate violation"
    elif major_findings:
        ceiling, ceiling_reason = 65, "unresolved major review finding"
    elif soft_violations:
        ceiling, ceiling_reason = 80, "unresolved soft final-gate violation"
    total = min(raw_total, ceiling)
    return {
        "rubric_version": "writing-quality/v1",
        "dimensions": [{"name": dimension.name, "weight": dimension.weight, "score": scores[dimension.name], "description": dimension.description} for dimension in RUBRIC],
        "total_score": total,
        "raw_total_score": raw_total,
        "max_score": 100,
        "band": "strong" if total >= 85 else "usable" if total >= 70 else "needs_iteration",
        "review_finding_count": len(findings),
        "quality_ceiling": ceiling,
        "quality_ceiling_reason": ceiling_reason,
    }


def evaluate_final_gate(payload: dict) -> dict:
    checks = payload.get("checks") or []
    violated_hard = sum(1 for check in checks if check.get("severity") == "hard" and check.get("status") == "violated")
    violated_soft = sum(1 for check in checks if check.get("severity") == "soft" and check.get("status") == "violated")
    return {"rubric_version": "final-gate-quality/v1", "hard_violations": violated_hard, "soft_violations": violated_soft, "gate_decision": payload.get("decision", "UNKNOWN"), "consistent": (payload.get("decision") == "BLOCK") == (violated_hard > 0)}


def write_evaluation_report(root: Path, review_payload: dict, final_payload: dict, manuscript: str) -> Path:
    report = {"rubric": evaluate_review_package(review_payload, manuscript, final_payload), "final_gate": evaluate_final_gate(final_payload)}
    target = root / "Content" / "WRITING_EVALUATION_REPORT.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return target
