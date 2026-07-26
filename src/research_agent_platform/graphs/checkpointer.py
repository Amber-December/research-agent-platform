from __future__ import annotations

import pickle
import os
import time
from collections import defaultdict
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

from langgraph.checkpoint.memory import InMemorySaver


class PersistentMemorySaver(InMemorySaver):
    """Persist LangGraph's in-memory saver to a local pickle file."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._flush_lock = Lock()
        super().__init__()
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        payload = pickle.loads(self.path.read_bytes())
        if "storage" in payload:
            self.storage = defaultdict(
                lambda: defaultdict(dict),
                {
                    thread_id: defaultdict(dict, namespaces)
                    for thread_id, namespaces in payload["storage"].items()
                },
            )
        if "writes" in payload:
            self.writes = defaultdict(dict, payload["writes"])
        if "blobs" in payload:
            self.blobs = dict(payload["blobs"])

    def _plain_storage(self) -> dict[str, dict[str, dict[str, Any]]]:
        return {
            thread_id: {namespace: dict(checkpoints) for namespace, checkpoints in namespaces.items()}
            for thread_id, namespaces in self.storage.items()
        }

    def _plain_writes(self) -> dict[Any, Any]:
        return {key: dict(value) for key, value in self.writes.items()}

    def _flush(self) -> None:
        with self._flush_lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload: dict[str, Any] = {
                "storage": self._plain_storage(),
                "writes": self._plain_writes(),
                "blobs": dict(self.blobs),
            }
            temp_path = self.path.with_suffix(self.path.suffix + f".{uuid4().hex}.tmp")
            try:
                temp_path.write_bytes(pickle.dumps(payload))
                for attempt in range(5):
                    try:
                        os.replace(temp_path, self.path)
                        break
                    except PermissionError:
                        if attempt == 4:
                            raise
                        time.sleep(0.02 * (attempt + 1))
            finally:
                temp_path.unlink(missing_ok=True)

    def put(self, config, checkpoint, metadata, new_versions):
        result = super().put(config, checkpoint, metadata, new_versions)
        self._flush()
        return result

    def put_writes(self, config, writes, task_id, task_path: str = "") -> None:
        super().put_writes(config, writes, task_id, task_path)
        self._flush()

    def delete_thread(self, thread_id: str) -> None:
        super().delete_thread(thread_id)
        self._flush()

    def copy_thread(self, source_thread_id: str, target_thread_id: str) -> None:
        super().copy_thread(source_thread_id, target_thread_id)
        self._flush()

    def prune(self, thread_ids, *, strategy: str = "keep_latest") -> None:
        super().prune(thread_ids, strategy=strategy)
        self._flush()
