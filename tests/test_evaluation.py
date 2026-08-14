from __future__ import annotations

from research_agent_platform.evaluation import evaluate_final_gate, evaluate_review_package


def test_review_rubric_reports_actionable_findings_without_masking_major_risk():
    result = evaluate_review_package(
        {"findings": [{"category": "methods", "severity": "major", "location": "line 10", "recommended_action": "Add ablation."}], "limitations": ["automated"]},
        "## Method\nMethod.",
    )
    assert result["rubric_version"] == "writing-quality/v1"
    assert result["dimensions"][3]["score"] > 0
    assert result["dimensions"][0]["score"] == 25
    assert result["total_score"] == 65
    assert result["band"] == "needs_iteration"


def test_final_gate_rubric_detects_inconsistent_decision():
    result = evaluate_final_gate({"decision": "PASS", "checks": [{"severity": "hard", "status": "violated"}]})
    assert result["consistent"] is False


def test_empty_review_cannot_score_as_usable():
    result = evaluate_review_package({"findings": [], "limitations": ["automated"]}, "## Method\nMethod.")
    assert result["total_score"] < 70
    assert result["band"] == "needs_iteration"


def test_adversarial_manuscript_is_not_scored_as_strong():
    review = {
        "findings": [
            {
                "category": "claims",
                "severity": "major",
                "location": "line 10",
                "recommended_action": "Cite evidence or narrow the claim.",
            }
        ],
        "limitations": ["automated"],
    }
    final_gate = {
        "decision": "REVISE",
        "checks": [
            {"check": "markdown_figure_numbering", "severity": "soft", "status": "violated"}
        ],
    }

    result = evaluate_review_package(
        review,
        "## Method\nWe prove universal superiority.\nFigure 2 shows the result.",
        final_gate,
    )

    assert result["total_score"] < 70
    assert result["band"] == "needs_iteration"
