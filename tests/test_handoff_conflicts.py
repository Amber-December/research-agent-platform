from research_agent_platform.context.handoff import build_handoff_conflict_review


def test_handoff_conflict_review_preserves_provenance_and_requires_human_confirmation():
    review, candidates = build_handoff_conflict_review(
        [
            {
                "relative_path": "wiki/ideas/idea-1.md",
                "command": "/idea",
                "excerpt": "## Limitations\n- The evidence is uncertain for rural sites.",
            },
            {
                "relative_path": "bib/EVIDENCE_MAP.md",
                "command": "/review",
                "excerpt": "## Boundary\n- The included studies use inconsistent populations.",
            },
        ]
    )

    assert candidates == ["wiki/ideas/idea-1.md", "bib/EVIDENCE_MAP.md"]
    assert "Source Precedence" in review
    assert "wiki/ideas/idea-1.md" in review
    assert "Human decision" in review
    assert "Do not silently reconcile" in review
