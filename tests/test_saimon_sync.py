from __future__ import annotations

import json
from typing import Any

import httpx

from saimon.client import SaimonClient
from saimon import sync_phase


def make_client(
    captured: list[httpx.Request],
    responses: dict[str, Any],
    *,
    search_results: list[dict[str, Any]] | None = None,
) -> SaimonClient:
    search_index = 0
    search_results = search_results or []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal search_index
        captured.append(request)
        if request.url.path == "/tools/search_knowledge_graph" and search_results:
            body = search_results[min(search_index, len(search_results) - 1)]
            search_index += 1
        else:
            body = responses.get(request.url.path, {"status": "ok"})
        return httpx.Response(200, json=body, request=request)

    return SaimonClient(
        base_url="http://saimon.test",
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )


# --- client store_content ----------------------------------------------------------


def test_store_content_sends_payload() -> None:
    captured: list[httpx.Request] = []
    client = make_client(
        captured,
        {"/tools/store_content": {"node_id": "kg-1"}},
    )

    result = client.store_content(
        title="slice:DEMO-1",
        content_type="research_note",
        body="note body",
        metadata={"slice_id": "DEMO-1"},
    )

    assert result == {"node_id": "kg-1"}
    assert captured[0].url.path == "/tools/store_content"
    assert json.loads(captured[0].content) == {
        "title": "slice:DEMO-1",
        "content_type": "research_note",
        "body": "note body",
        "metadata": {"slice_id": "DEMO-1"},
    }


# --- record_outcome ----------------------------------------------------------------


def test_record_outcome_generates_and_stores_with_linkage() -> None:
    captured: list[httpx.Request] = []
    client = make_client(
        captured,
        {
            "/tools/generate_content": {"content": "generated note"},
            "/tools/store_content": {"node_id": "kg-1"},
        },
        search_results=[{"data": []}],
    )

    result = sync_phase.record_outcome(client, "DEMO-1", "validated", ["finding a"])

    assert result == {"node_id": "kg-1"}
    paths = [req.url.path for req in captured]
    assert paths == [
        "/tools/search_knowledge_graph",
        "/tools/generate_content",
        "/tools/store_content",
    ]
    generate_payload = json.loads(captured[1].content)
    assert generate_payload["content_type"] == "research_note"
    assert "DEMO-1" in generate_payload["content"]
    store_payload = json.loads(captured[2].content)
    assert store_payload["metadata"] == {"slice_id": "DEMO-1"}


def test_record_outcome_is_idempotent() -> None:
    captured: list[httpx.Request] = []
    client = make_client(
        captured,
        {
            "/tools/generate_content": {"content": "generated note"},
            "/tools/store_content": {"node_id": "kg-1"},
        },
        search_results=[{"data": [{"id": "existing-note"}]}],
    )

    result = sync_phase.record_outcome(client, "DEMO-1", "validated")

    assert result is None
    # Only the existence search happened — no generate/store.
    assert [req.url.path for req in captured] == ["/tools/search_knowledge_graph"]


# --- sync hook (non-blocking) ---------------------------------------------------------


def test_sync_hook_swallows_errors() -> None:
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("saimon down", request=request)

    client = SaimonClient(
        base_url="http://saimon.test",
        api_key="k",
        transport=httpx.MockTransport(boom),
    )

    # Must not raise — the tree-sync path must never fail on a saimon outage.
    assert sync_phase.sync_hook(client, "DEMO-1", "validated") is None


def test_sync_hook_records_when_available() -> None:
    captured: list[httpx.Request] = []
    client = make_client(
        captured,
        {
            "/tools/generate_content": {"content": "generated note"},
            "/tools/store_content": {"node_id": "kg-1"},
        },
        search_results=[{"data": []}],
    )

    assert sync_phase.sync_hook(client, "DEMO-1", "validated") == {"node_id": "kg-1"}
