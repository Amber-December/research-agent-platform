from __future__ import annotations

from pathlib import Path

from research_agent_platform import config as config_module
from tools.configure_tsinghua_seafile import _update_env


def test_seafile_env_configuration_persists_token_not_password(tmp_path: Path):
    env_path = tmp_path / ".env"
    env_path.write_text("SEAFILE_PASSWORD=old-secret\nUNRELATED=value\n", encoding="utf-8")

    _update_env(
        env_path,
        {
            "CLOUD_SYNC_ENABLED": "true",
            "SEAFILE_API_TOKEN": "token-value",
            "SEAFILE_PASSWORD": "",
        },
    )

    content = env_path.read_text(encoding="utf-8")
    assert "SEAFILE_API_TOKEN=token-value" in content
    assert "SEAFILE_PASSWORD=\n" in content
    assert "old-secret" not in content
    assert "UNRELATED=value" in content


def test_project_root_env_file_is_loaded(tmp_path: Path, monkeypatch):
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / ".env").write_text("CLOUD_SYNC_ENABLED=true\nSEAFILE_API_TOKEN=abc123\n", encoding="utf-8")
    monkeypatch.setattr(config_module, "_project_root", lambda: project_root)
    config_module._load_project_env()
    assert config_module._env_bool("CLOUD_SYNC_ENABLED") is True
    assert config_module.os.getenv("SEAFILE_API_TOKEN") == "abc123"
