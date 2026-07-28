from __future__ import annotations

from ..models import TaskRun


class WikiService:
    def render_task_note(
        self,
        task: TaskRun,
        *,
        status: str | None = None,
        summary: str | None = None,
    ) -> str:
        artifact_lines = "\n".join(
            f"- `{artifact.relative_path}`" for artifact in task.artifacts
        )
        return (
            "\n".join(
                [
                    f"# Task Note: {task.workflow_title}",
                    "",
                    f"- Task ID: {task.task_id}",
                    f"- Session ID: {task.session_id}",
                    f"- Command: {task.command}",
                    f"- Objective: {task.objective}",
                    f"- Status: {status or task.status}",
                    "",
                    "## Summary",
                    summary or task.summary or "No summary available.",
                    "",
                    "## Session Artifacts",
                    "All paths below are relative to this session workspace.",
                    "",
                    artifact_lines or "- None",
                ]
            )
            + "\n"
        )
