import asyncio

import httpx

from research_agent_platform import upstream


def test_request_retries_one_transient_gateway_failure(monkeypatch):
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(502, json={"error": {"message": "temporarily unavailable"}})
        return httpx.Response(200, json={"ok": True})

    original_client = httpx.AsyncClient
    monkeypatch.setattr(
        upstream.httpx,
        "AsyncClient",
        lambda **kwargs: original_client(transport=httpx.MockTransport(handler), **kwargs),
    )

    result = asyncio.run(upstream._request("POST", "/chat/completions", {"messages": []}))

    assert result == {"ok": True}
    assert attempts == 2


def test_request_retries_two_transient_gateway_failures(monkeypatch):
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            return httpx.Response(502, json={"error": {"message": "temporarily unavailable"}})
        return httpx.Response(200, json={"ok": True})

    original_client = httpx.AsyncClient
    monkeypatch.setattr(
        upstream.httpx,
        "AsyncClient",
        lambda **kwargs: original_client(transport=httpx.MockTransport(handler), **kwargs),
    )

    result = asyncio.run(upstream._request("POST", "/chat/completions", {"messages": []}))

    assert result == {"ok": True}
    assert attempts == 3
