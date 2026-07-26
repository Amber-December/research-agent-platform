from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _docs_root() -> Path:
    return _project_root().parent


def _default_aris_repo_root() -> str:
    candidate = _docs_root() / "Auto-claude-code-research-in-sleep"
    return str(candidate)


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class AppConfig(BaseModel):
    project_name: str = "research-agent-platform"
    enable_hitl: bool = True
    router_mode: str = "rule_first"
    graph_backend: str = "langgraph"
    memory_backend: str = "research_wiki"
    project_root: str = Field(default_factory=lambda: str(_project_root()))
    docs_root: str = Field(default_factory=lambda: str(_docs_root()))
    artifact_root: str = Field(default_factory=lambda: str(_project_root() / "agent-workspace"))
    state_root: str = Field(default_factory=lambda: str(_project_root() / ".agent-state"))
    wiki_root: str = Field(default_factory=lambda: str(_project_root() / "research-wiki"))
    prd_path: str = Field(default_factory=lambda: str(_docs_root() / "research-agent-prd.md"))
    tech_spec_path: str = Field(default_factory=lambda: str(_docs_root() / "research-agent-tech-spec.md"))
    aris_repo_root: str = Field(
        default_factory=lambda: os.getenv("ARIS_REPO_ROOT", _default_aris_repo_root())
    )
    upstream_base_url: str = Field(
        default_factory=lambda: os.getenv("UPSTREAM_BASE_URL", "https://api.openai.com/v1")
    )
    upstream_api_key: str = Field(default_factory=lambda: os.getenv("UPSTREAM_API_KEY", ""))
    upstream_model: str = Field(default_factory=lambda: os.getenv("UPSTREAM_MODEL", ""))
    image_model: str = Field(default_factory=lambda: os.getenv("IMAGE_MODEL", "gpt-image-2"))
    request_timeout_seconds: float = Field(
        default_factory=lambda: float(os.getenv("REQUEST_TIMEOUT_SECONDS", "120"))
    )
    image_request_timeout_seconds: float = Field(
        default_factory=lambda: float(os.getenv("IMAGE_REQUEST_TIMEOUT_SECONDS", "300"))
    )
    presentation_template: str = Field(
        default_factory=lambda: os.getenv("PRESENTATION_TEMPLATE", "auto")
    )
    presentation_max_slides: int = Field(
        default_factory=lambda: int(os.getenv("PRESENTATION_MAX_SLIDES", "12"))
    )
    presentation_source_limit: int = Field(
        default_factory=lambda: int(os.getenv("PRESENTATION_SOURCE_LIMIT", "40"))
    )
    upload_max_files: int = Field(
        default_factory=lambda: int(os.getenv("UPLOAD_MAX_FILES", "20"))
    )
    upload_max_file_mb: int = Field(
        default_factory=lambda: int(os.getenv("UPLOAD_MAX_FILE_MB", "100"))
    )
    scholar_request_timeout_seconds: float = Field(
        default_factory=lambda: float(os.getenv("SCHOLAR_REQUEST_TIMEOUT_SECONDS", "30"))
    )
    scholar_results_per_source: int = Field(
        default_factory=lambda: int(os.getenv("SCHOLAR_RESULTS_PER_SOURCE", "4"))
    )
    wos_api_base_url: str = Field(
        default_factory=lambda: os.getenv(
            "WOS_API_BASE_URL", "https://api.clarivate.com/apis/wos-starter/v1"
        )
    )
    wos_api_key: str = Field(default_factory=lambda: os.getenv("WOS_API_KEY", ""))
    wos_default_db: str = Field(default_factory=lambda: os.getenv("WOS_DEFAULT_DB", "WOS"))
    cnki_search_endpoint: str = Field(default_factory=lambda: os.getenv("CNKI_SEARCH_ENDPOINT", ""))
    cnki_search_method: str = Field(default_factory=lambda: os.getenv("CNKI_SEARCH_METHOD", "GET"))
    cnki_api_key: str = Field(default_factory=lambda: os.getenv("CNKI_API_KEY", ""))
    cnki_auth_header: str = Field(default_factory=lambda: os.getenv("CNKI_AUTH_HEADER", "X-ApiKey"))
    cnki_auth_scheme: str = Field(default_factory=lambda: os.getenv("CNKI_AUTH_SCHEME", ""))
    cloud_sync_enabled: bool = Field(default_factory=lambda: _env_bool("CLOUD_SYNC_ENABLED"))
    seafile_base_url: str = Field(default_factory=lambda: os.getenv("SEAFILE_BASE_URL", ""))
    seafile_api_token: str = Field(default_factory=lambda: os.getenv("SEAFILE_API_TOKEN", ""))
    seafile_username: str = Field(default_factory=lambda: os.getenv("SEAFILE_USERNAME", ""))
    seafile_password: str = Field(default_factory=lambda: os.getenv("SEAFILE_PASSWORD", ""))
    seafile_repo_id: str = Field(default_factory=lambda: os.getenv("SEAFILE_REPO_ID", ""))
    seafile_repo_name: str = Field(
        default_factory=lambda: os.getenv("SEAFILE_REPO_NAME", "Research Agent")
    )
    seafile_remote_root: str = Field(
        default_factory=lambda: os.getenv("SEAFILE_REMOTE_ROOT", "research-agent")
    )
    seafile_share_links: bool = Field(
        default_factory=lambda: _env_bool("SEAFILE_SHARE_LINKS", True)
    )
    seafile_share_password: str = Field(
        default_factory=lambda: os.getenv("SEAFILE_SHARE_PASSWORD", "")
    )


config = AppConfig()
