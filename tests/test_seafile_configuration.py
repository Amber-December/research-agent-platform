from __future__ import annotations

from pathlib import Path

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
