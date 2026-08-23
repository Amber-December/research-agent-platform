from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable


_CONFLICT_TERMS = re.compile(
    r"\b(?:conflict|contradict|inconsistent|uncertain|unknown|limitation|gap|boundary)\b"
    r"|冲突|矛盾|不一致|不确定|未知|局限|缺口|边界",
    re.IGNORECASE,
)


def build_handoff_conflict_review(
    sources: Iterable[dict[str, str]],
    *,
    upstream_priority: tuple[str, ...] = ("/idea", "/review", "/plan"),
) -> tuple[str, list[str]]:
    """Create a human-reviewable handoff for upstream Idea/Wiki assets.

    This is intentionally conservative: it records candidate conflict passages
    and provenance, but never resolves disagreements or invents a preferred
    claim. The author must confirm the resolution before writing proceeds.
    """
    source_list = list(sources)
    lines = [
        "# Handoff Conflict Review",
        "",
        "This is an internal planning aid. It does not replace the upstream Idea/Wiki contract.",
        "",
        "## Source Precedence",
        "",
        "- Upstream `/idea` and `/review` artifacts remain authoritative for their stated evidence.",
        "- `/plan` may adapt those artifacts but must not silently overwrite a conflicting claim.",
        "- User-confirmed decisions take precedence over inferred resolutions.",
        "",
        "## Candidate Conflicts",
        "",
    ]
    candidates: list[str] = []
    for source in source_list:
        relative_path = source.get("relative_path", "unknown")
        command = source.get("command", "unknown")
        excerpt = source.get("excerpt", "").strip()
        if not excerpt:
            continue
        matched_lines = [
            line.strip()
            for line in excerpt.splitlines()
            if _CONFLICT_TERMS.search(line)
        ][:8]
        if matched_lines:
            candidates.append(relative_path)
            lines.extend(
                [
                    f"### `{relative_path}` ({command})",
                    "",
                    *[f"- {line}" for line in matched_lines],
                    "",
                    "- **Human decision:** confirm, narrow, or reject this boundary before drafting.",
                    "",
                ]
            )
    if not candidates:
        lines.append("- No explicit conflict marker was found; still verify claims across source artifacts.")
        lines.append("")
    lines.extend(
        [
            "## Required Confirmation",
            "",
            "- Confirm which claim, scope, population, or evidence boundary is admitted to the plan.",
            "- Do not silently reconcile conflicting claims; record the author decision or leave the issue unresolved.",
            "- Record unresolved disagreements as limitations; do not resolve them from domain common sense.",
            "- Keep the selected source path or stable evidence ID beside every downstream claim.",
        ]
    )
    return "\n".join(lines) + "\n", candidates


def handoff_conflict_context(review: str) -> str:
    return (
        "Manual handoff conflict review (not new evidence):\n"
        "- Treat this as a checklist for author confirmation, not as a factual source.\n"
        "- Do not silently reconcile conflicting Idea/Wiki claims. Preserve the source path and mark unresolved boundaries.\n\n"
        + review[:8000]
    )
