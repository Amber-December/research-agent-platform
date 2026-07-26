from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from ..models import TaskRun


class WikiService:
    def __init__(self, wiki_root: str, aris_repo_root: str) -> None:
        self.wiki_root = Path(wiki_root)
        self.aris_repo_root = Path(aris_repo_root)
        self.notes_dir = self.wiki_root / "agent-notes"
        self.notes_dir.mkdir(parents=True, exist_ok=True)

    def ensure_initialized(self) -> None:
        script = self.aris_repo_root / "tools" / "research_wiki.py"
        if not script.exists():
            self.wiki_root.mkdir(parents=True, exist_ok=True)
            return
        if (self.wiki_root / "papers").exists():
            return
        subprocess.run(
            [sys.executable, str(script), "init", str(self.wiki_root)],
            check=False,
            capture_output=True,
            text=True,
        )

    def record_task(self, task: TaskRun) -> str:
        self.ensure_initialized()
        note_path = self.notes_dir / f"{task.task_id}.md"
        artifact_lines = "\n".join(
            f"- {artifact.relative_path}: {artifact.absolute_path}" for artifact in task.artifacts
        )
        note_path.write_text(
            "\n".join(
                [
                    f"# Task Note: {task.workflow_title}",
                    "",
                    f"- Task ID: {task.task_id}",
                    f"- Command: {task.command}",
                    f"- Objective: {task.objective}",
                    f"- Status: {task.status}",
                    "",
                    "## Summary",
                    task.summary or "No summary available.",
                    "",
                    "## Artifacts",
                    artifact_lines or "- None",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        return str(note_path.resolve())
