from __future__ import annotations

from pathlib import Path

from research_agent_platform.graphs.workflows import workflow_registry


def main() -> None:
    lines = [
        "# ARIS Skill Stage Mapping",
        "",
        "Generated from `src/research_agent_platform/graphs/workflows.py`.",
        "",
    ]
    for command, workflow in workflow_registry().items():
        lines.extend([f"## {command} - {workflow.title}", "", workflow.description, ""])
        for stage in workflow.stage_definitions:
            lines.extend(
                [
                    f"### {stage.title} (`{stage.name}`)",
                    "",
                    f"- Artifact: `{stage.artifact_path}`",
                    f"- Kind: `{stage.artifact_kind}`",
                    f"- HITL: `{stage.hitl}`",
                    "- ARIS skills:",
                ]
            )
            if stage.skill_paths:
                lines.extend(f"  - `{path}`" for path in stage.skill_paths)
            else:
                lines.append("  - None")
            lines.append("")
        lines.append("")
    output = Path(__file__).resolve().parents[1] / "docs" / "aris-skill-stage-mapping.md"
    output.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
