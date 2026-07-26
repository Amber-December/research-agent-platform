from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


TaskStatus = Literal["running", "waiting_human", "completed", "failed"]
CheckpointStatus = Literal["pending", "approved", "rejected"]
RouteSource = Literal["explicit", "implicit_heuristic", "implicit_llm", "approval"]
PresentationType = Literal["paper", "stage"]
PresentationSourceScope = Literal["auto", "attachments", "selected", "session", "workspace"]
CloudSyncStatus = Literal["disabled", "pending", "synced", "error"]
ArtifactKind = Literal[
    "report",
    "plan",
    "review",
    "slides",
    "wiki",
    "contract",
    "manifest",
    "checkpoint",
    "note",
    "document",
    "image",
    "presentation",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class MessageRecord(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    timestamp: str = Field(default_factory=utc_now)


class ArtifactRecord(BaseModel):
    artifact_id: str = Field(default_factory=lambda: new_id("artifact"))
    name: str
    kind: ArtifactKind
    relative_path: str
    absolute_path: str
    url_path: str
    description: str
    created_at: str = Field(default_factory=utc_now)


class UploadBatchRecord(BaseModel):
    upload_batch_id: str = Field(default_factory=lambda: new_id("upload"))
    relative_paths: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now)


class PresentationSourceConfig(BaseModel):
    presentation_type: PresentationType
    requested_scope: PresentationSourceScope = "auto"
    resolved_scope: PresentationSourceScope
    source_refs: list[str] = Field(default_factory=list)
    upload_batch_id: str = ""
    selection_reason: str = ""


class RebuttalSourceConfig(BaseModel):
    paper_refs: list[str] = Field(default_factory=list)
    review_refs: list[str] = Field(default_factory=list)
    paper_selection_reason: str = ""
    review_selection_reason: str = ""
    upload_batch_ids: list[str] = Field(default_factory=list)


class CloudWorkspaceState(BaseModel):
    provider: str = "seafile"
    status: CloudSyncStatus = "disabled"
    remote_path: str = ""
    share_url: str = ""
    preview_url: str = ""
    download_url: str = ""
    repo_id: str = ""
    synced_files: int = 0
    uploaded_files: int = 0
    last_synced_at: str = ""
    error: str = ""


class ApprovalCheckpoint(BaseModel):
    checkpoint_id: str = Field(default_factory=lambda: new_id("checkpoint"))
    stage_name: str
    stage_index: int
    title: str
    prompt: str
    status: CheckpointStatus = "pending"
    feedback: str = ""
    created_at: str = Field(default_factory=utc_now)
    resolved_at: str | None = None


class TaskRun(BaseModel):
    task_id: str = Field(default_factory=lambda: new_id("task"))
    session_id: str
    user_id: str = "local"
    command: str
    objective: str
    route_source: RouteSource
    workflow_title: str
    status: TaskStatus = "running"
    current_stage_index: int = 0
    current_stage_name: str = ""
    artifact_root: str = ""
    summary: str = ""
    error: str = ""
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)
    approvals: list[ApprovalCheckpoint] = Field(default_factory=list)
    artifacts: list[ArtifactRecord] = Field(default_factory=list)
    progress_log: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    presentation_source: PresentationSourceConfig | None = None
    rebuttal_source: RebuttalSourceConfig | None = None


class ChatSession(BaseModel):
    session_id: str = Field(default_factory=lambda: new_id("session"))
    user_id: str = "local"
    workspace_root: str = ""
    active_task_id: str | None = None
    history: list[MessageRecord] = Field(default_factory=list)
    upload_batches: list[UploadBatchRecord] = Field(default_factory=list)
    cloud_workspace: CloudWorkspaceState = Field(default_factory=CloudWorkspaceState)
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)
