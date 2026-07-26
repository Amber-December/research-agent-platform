from __future__ import annotations

import json
import os
import time
from pathlib import Path
from uuid import uuid4

from ..models import ChatSession, TaskRun, utc_now


class StateStore:
    def __init__(self, root: str, artifact_root: str | None = None) -> None:
        self.root = Path(root)
        self.artifact_root = Path(artifact_root) if artifact_root else self.root.parent / "agent-workspace"
        self.sessions_dir = self.root / "sessions"
        self.tasks_dir = self.root / "tasks"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.tasks_dir.mkdir(parents=True, exist_ok=True)

    def _session_path(self, session_id: str) -> Path:
        return self.sessions_dir / f"{session_id}.json"

    def _task_path(self, task_id: str) -> Path:
        return self.tasks_dir / f"{task_id}.json"

    def create_session(self, user_id: str = "local") -> ChatSession:
        session = ChatSession(user_id=user_id or "local")
        session.workspace_root = str(
            self.artifact_root / self._slug(session.user_id) / session.session_id
        )
        self.save_session(session)
        return session

    def get_or_create_session(self, session_id: str | None, user_id: str = "local") -> ChatSession:
        if not session_id:
            return self.create_session(user_id)
        session = self.load_session(session_id)
        if session:
            if user_id and session.user_id in {"default", "local"} and user_id != session.user_id:
                session.user_id = user_id
            session.workspace_root = str(
                self.artifact_root / self._slug(session.user_id) / session.session_id
            )
            self.save_session(session)
            return session
        return self.create_session(user_id)

    def load_session(self, session_id: str) -> ChatSession | None:
        path = self._session_path(session_id)
        if not path.exists():
            return None
        return ChatSession.model_validate_json(path.read_text(encoding="utf-8"))

    def save_session(self, session: ChatSession) -> None:
        session.updated_at = utc_now()
        self._write_json(self._session_path(session.session_id), session.model_dump_json(indent=2))

    def load_task(self, task_id: str) -> TaskRun | None:
        path = self._task_path(task_id)
        if not path.exists():
            return None
        return TaskRun.model_validate_json(path.read_text(encoding="utf-8"))

    def save_task(self, task: TaskRun) -> None:
        task.updated_at = utc_now()
        self._write_json(self._task_path(task.task_id), task.model_dump_json(indent=2))

    def list_tasks(self, session_id: str | None = None) -> list[TaskRun]:
        tasks: list[TaskRun] = []
        for path in sorted(self.tasks_dir.glob("*.json")):
            task = TaskRun.model_validate_json(path.read_text(encoding="utf-8"))
            if session_id and task.session_id != session_id:
                continue
            tasks.append(task)
        tasks.sort(key=lambda item: item.updated_at, reverse=True)
        return tasks

    def export_summary(self) -> dict[str, int]:
        return {
            "sessions": len(list(self.sessions_dir.glob("*.json"))),
            "tasks": len(list(self.tasks_dir.glob("*.json"))),
        }

    def _slug(self, value: str) -> str:
        cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in value.strip())
        return cleaned or "local"

    def _write_json(self, path: Path, content: str) -> None:
        temporary_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        temporary_path.write_text(content, encoding="utf-8")
        try:
            for attempt in range(5):
                try:
                    os.replace(temporary_path, path)
                    return
                except PermissionError:
                    if attempt == 4:
                        raise
                    time.sleep(0.02 * (attempt + 1))
        finally:
            temporary_path.unlink(missing_ok=True)
