from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from saimon.client import (
    SaimonClient,
    SaimonError,
    SaimonUnreachableError,
)
from saimon import refine


def make_transport(
    captured: list[httpx.Request],
    responses: dict[str, Any] | None = None,
) -> httpx.MockTransport:
    responses = responses or {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        body = json.dumps(responses.get(request.url.path, {"status": "ok"}))
        return httpx.Response(200, json=json.loads(body), request=request)

    return httpx.MockTransport(handler)


def make_client(
    captured: list[httpx.Request],
    responses: dict[str, Any] | None = None,
    api_key: str | None = "test-key",
) -> SaimonClient:
    return SaimonClient(
        base_url="http://saimon.test",
        api_key=api_key,
        transport=make_transport(captured, responses),
    )


# --- client request shape + auth -------------------------------------------------


def test_search_sends_correct_path_payload_and_auth() -> None:
    captured: list[httpx.Request] = []
    client = make_client(captured)

    result = client.search("patterns for X in codebase", limit=3)

    assert result == {"status": "ok"}
    assert len(captured) == 1
    req = captured[0]
    assert req.method == "POST"
    assert req.url.path == "/tools/search_knowledge_graph"
    assert json.loads(req.content) == {"query": "patterns for X in codebase", "limit": 3}
    assert req.headers["X-Saimon-API-Key"] == "test-key"


def test_verify_sends_claim_payload() -> None:
    captured: list[httpx.Request] = []
    client = make_client(captured)

    client.verify("is approach Y viable?")

    assert captured[0].url.path == "/tools/verify_claim"
    assert json.loads(captured[0].content) == {"claim": "is approach Y viable?"}


def test_generate_sends_content_and_type() -> None:
    captured: list[httpx.Request] = []
    client = make_client(captured)

    client.generate("memo text", content_type="decision_record")

    assert captured[0].url.path == "/tools/generate_content"
    assert json.loads(captured[0].content) == {
        "content": "memo text",
        "content_type": "decision_record",
    }


def test_no_api_key_omits_auth_header() -> None:
    captured: list[httpx.Request] = []
    client = make_client(captured, api_key=None)

    client.search("q")

    assert "X-Saimon-API-Key" not in captured[0].headers


def test_health_returns_json() -> None:
    captured: list[httpx.Request] = []
    client = make_client(captured, responses={"/health": {"status": "ok"}})

    assert client.health() == {"status": "ok"}
    assert captured[0].method == "GET"
    assert captured[0].url.path == "/health"


# --- error handling ---------------------------------------------------------------


def test_unreachable_saimon_raises_clear_error() -> None:
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    client = SaimonClient(
        base_url="http://saimon.test",
        api_key="k",
        transport=httpx.MockTransport(boom),
    )

    with pytest.raises(SaimonUnreachableError, match="saimon"):
        client.search("q")


def test_http_error_raises_saimon_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom", request=request)

    client = SaimonClient(
        base_url="http://saimon.test",
        api_key="k",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(SaimonError):
        client.verify("claim")


# --- refine composition -----------------------------------------------------------


def test_refine_surface_research_composes_client() -> None:
    captured: list[httpx.Request] = []
    client = make_client(captured)

    result = refine.surface_research(client, "topic")

    assert result == {"status": "ok"}
    assert captured[0].url.path == "/tools/search_knowledge_graph"


def test_refine_verify_approach_composes_client() -> None:
    captured: list[httpx.Request] = []
    client = make_client(captured)

    refine.verify_approach(client, "claim")

    assert captured[0].url.path == "/tools/verify_claim"


def test_refine_record_decision_composes_client() -> None:
    captured: list[httpx.Request] = []
    client = make_client(captured)

    refine.record_decision(client, "decision memo")

    assert captured[0].url.path == "/tools/generate_content"
    assert json.loads(captured[0].content)["content_type"] == "decision_record"
