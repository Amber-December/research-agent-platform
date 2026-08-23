import json
from pathlib import Path
from types import SimpleNamespace

from research_agent_platform.agent import _sanitize_review_deliverable


def test_synthetic_review_package_does_not_emit_fake_bibliography(tmp_path: Path):
    search = tmp_path / "bib" / "LITERATURE_SEARCH.json"
    search.parent.mkdir(parents=True)
    search.write_text(
        json.dumps({"papers": [{"sources": ["golden_fixture"], "url": "golden://P001"}]}),
        encoding="utf-8",
    )
    task = SimpleNamespace(artifact_root=str(tmp_path))
    content = "# Review\n\n## References\n\n- [P001] Invented title, `golden://P001`."

    sanitized = _sanitize_review_deliverable(task, content)

    assert "Invented title" not in sanitized
    assert "golden://" not in sanitized
    assert "Stable record identifiers" in sanitized
