from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

from research_agent_platform import api as api_module
from research_agent_platform import agent as agent_module


def test_openai_compatible_chat_completion_routes_to_task(service, monkeypatch):
    monkeypatch.setattr(api_module, "agent", service)
    client = TestClient(api_module.app)

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "research-agent-platform",
            "messages": [{"role": "user", "content": "/present 做一个中文汇报"}],
            "metadata": {"session_id": None, "user_id": "qingxiaoda-user"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["choices"][0]["message"]["role"] == "assistant"
    assert payload["x_agent_task"]["status"] == "completed"
    assert payload["x_agent_task"]["task_id"]

    task = service.get_task(payload["x_agent_task"]["task_id"])
    assert task is not None
    assert task.user_id == "qingxiaoda-user"


def test_openai_compatible_responses_and_task_files(service, monkeypatch):
    monkeypatch.setattr(api_module, "agent", service)
    client = TestClient(api_module.app)

    response = client.post(
        "/v1/responses",
        json={
            "model": "research-agent-platform",
            "input": "/present 做一个中文汇报",
            "metadata": {"session_id": "session-1"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    task_id = payload["metadata"]["task_id"]
    files = client.get(f"/api/tasks/{task_id}/files").json()

    assert payload["metadata"]["status"] == "completed"
    assert files["task_id"] == task_id
    assert any(item["relative_path"].endswith("SLIDES_OUTLINE.md") for item in files["files"])
    assert not any(item["relative_path"].endswith("Content/slides_outline_checkpoint.md") for item in files["files"])
    assert any(item["relative_path"].startswith("presentation/") for item in files["files"])


def test_session_file_upload_creates_session_and_classifies_files(service, monkeypatch):
    monkeypatch.setattr(api_module, "agent", service)
    client = TestClient(api_module.app)

    response = client.post(
        "/api/session/files",
        data={"user_id": "local", "target": "auto"},
        files=[
            ("files", ("result.png", b"png-data", "image/png")),
            ("files", ("draft.pdf", b"pdf-data", "application/pdf")),
            ("files", ("train.py", b"print('ok')", "text/x-python")),
        ],
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["user_id"] == "local"
    assert payload["upload_batch_id"].startswith("upload_")
    session = service.store.load_session(payload["session_id"])
    assert session is not None
    assert session.upload_batches[-1].upload_batch_id == payload["upload_batch_id"]
    assert set(session.upload_batches[-1].relative_paths) == {
        "figures/uploads/result.png",
        "paper/uploads/draft.pdf",
        "code/uploads/train.py",
    }
    assert f"local/{payload['session_id']}" in payload["workspace_root"].replace("\\", "/")
    paths = {item["relative_path"] for item in payload["files"]}
    assert paths == {
        "figures/uploads/result.png",
        "paper/uploads/draft.pdf",
        "code/uploads/train.py",
    }
    for item in payload["files"]:
        assert item["size"] > 0
        assert Path(item["absolute_path"]).exists()


def test_session_file_upload_reuses_session_and_preserves_duplicate_names(service, monkeypatch):
    monkeypatch.setattr(api_module, "agent", service)
    client = TestClient(api_module.app)

    first = client.post(
        "/api/session/files",
        data={"target": "plan"},
        files={"files": ("notes.txt", b"first", "text/plain")},
    ).json()
    second = client.post(
        "/api/session/files",
        data={"session_id": first["session_id"], "target": "plan"},
        files={"files": ("notes.txt", b"second", "text/plain")},
    )

    assert second.status_code == 200
    payload = second.json()
    assert payload["session_id"] == first["session_id"]
    assert first["files"][0]["relative_path"] == "plan/uploads/notes.txt"
    assert payload["files"][0]["relative_path"] == "plan/uploads/notes_2.txt"


def test_session_file_upload_rejects_invalid_target(service, monkeypatch):
    monkeypatch.setattr(api_module, "agent", service)
    client = TestClient(api_module.app)

    response = client.post(
        "/api/session/files",
        data={"target": "outside"},
        files={"files": ("notes.txt", b"content", "text/plain")},
    )

    assert response.status_code == 400


def test_manual_session_cloud_sync_endpoint(service, monkeypatch):
    monkeypatch.setattr(api_module, "agent", service)
    client = TestClient(api_module.app)
    session = service.store.create_session()

    response = client.post(f"/api/sessions/{session.session_id}/sync")

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == session.session_id
    assert payload["cloud_workspace"]["status"] == "disabled"


def test_approve_returns_before_background_completion(service, monkeypatch):
    monkeypatch.setattr(api_module, "agent", service)

    async def scenario():
        original_generate_text = agent_module.generate_text

        async def generate_with_choices(*, system_prompt, user_prompt, model=None, temperature=0.3):
            content = await original_generate_text(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=model,
                temperature=temperature,
            )
            if "Current stage: Slides Outline" in user_prompt:
                return content + "\n\n## Decision Required\n- Option A: concise\n- Option B: detailed\n"
            return content

        monkeypatch.setattr(agent_module, "generate_text", generate_with_choices)
        start = await service.chat(None, "/present 做一个中文汇报")
        task_id = start["task_id"]
        release = asyncio.Event()
        original_approve = service.approve_task

        async def delayed_approve(approved_task_id: str, feedback: str = ""):
            await release.wait()
            return await original_approve(approved_task_id, feedback)

        monkeypatch.setattr(service, "approve_task", delayed_approve)
        response = await api_module.api_approve(task_id, {"feedback": ""})

        assert response["status"] == "running"
        assert response["checkpoint"] is None
        assert "后台" in response["text"]
        assert task_id in api_module.background_tasks
        assert not api_module.background_tasks[task_id].done()

        release.set()
        await api_module.background_tasks[task_id]
        task = service.get_task(task_id)
        assert task is not None
        assert task.status == "completed"

    asyncio.run(scenario())


def test_background_failure_is_persisted(service, monkeypatch):
    monkeypatch.setattr(api_module, "agent", service)

    async def scenario():
        original_generate_text = agent_module.generate_text

        async def generate_with_choices(*, system_prompt, user_prompt, model=None, temperature=0.3):
            content = await original_generate_text(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=model,
                temperature=temperature,
            )
            if "Current stage: Slides Outline" in user_prompt:
                return content + "\n\n## Decision Required\n- Option A: concise\n- Option B: detailed\n"
            return content

        monkeypatch.setattr(agent_module, "generate_text", generate_with_choices)
        start = await service.chat(None, "/present 做一个中文汇报")
        task_id = start["task_id"]

        async def failing_approve(approved_task_id: str, feedback: str = ""):
            raise RuntimeError("image provider unavailable")

        monkeypatch.setattr(service, "approve_task", failing_approve)
        response = await api_module.api_approve(task_id, {"feedback": ""})
        assert response["status"] == "running"
        await api_module.background_tasks[task_id]

        payload = api_module.task_status_payload(task_id)
        assert payload["status"] == "failed"
        assert payload["error"] == "image provider unavailable"
        assert any("image provider unavailable" in item for item in payload["progress"])

    asyncio.run(scenario())


def test_task_status_payload_supports_progress_polling(service, monkeypatch):
    monkeypatch.setattr(api_module, "agent", service)
    original_generate_text = agent_module.generate_text

    async def generate_with_choices(*, system_prompt, user_prompt, model=None, temperature=0.3):
        content = await original_generate_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            temperature=temperature,
        )
        if "Current stage: Slides Outline" in user_prompt:
            return content + "\n\n## Decision Required\n- Option A: concise\n- Option B: detailed\n"
        return content

    monkeypatch.setattr(agent_module, "generate_text", generate_with_choices)
    start = asyncio.run(service.chat(None, "/present 做一个中文汇报"))

    payload = api_module.task_status_payload(start["task_id"])

    assert payload["status"] == "waiting_human"
    assert payload["current_stage_name"] == "slides_outline"
    assert payload["checkpoint"]["title"] == "Presentation Outline Approval"
    assert payload["progress"]
    assert payload["artifacts"]


def test_chat_page_contains_task_polling_and_restore(service, monkeypatch):
    monkeypatch.setattr(api_module, "agent", service)
    client = TestClient(api_module.app)

    response = client.get("/chat")

    assert response.status_code == 200
    assert "setTimeout(pollTask, 1500)" in response.text
    assert "restoreTaskState();" in response.text
    assert "已批准，正在后台生成" in response.text
    assert ".actions[hidden] { display:none; }" in response.text
    assert "--source attachments|selected|session|workspace" in response.text
