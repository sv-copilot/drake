from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from saimon.client import SaimonClient
from saimon import dispatch


def make_client(
    captured: list[httpx.Request],
    responses: dict[str, Any],
) -> SaimonClient:
    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        body = responses.get(request.url.path, {"status": "ok"})
        return httpx.Response(200, json=body, request=request)

    return SaimonClient(
        base_url="http://saimon.test",
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )


# --- client export ---------------------------------------------------------------


def test_export_sends_content_and_format() -> None:
    captured: list[httpx.Request] = []
    client = make_client(captured, {"/tools/export_content": {"content": "# ctx"}})

    result = client.export("raw subgraph", format="markdown")

    assert result == {"content": "# ctx"}
    assert captured[0].url.path == "/tools/export_content"
    assert json.loads(captured[0].content) == {
        "content": "raw subgraph",
        "format": "markdown",
    }


# --- build_task_context -----------------------------------------------------------


def test_build_task_context_exports_subgraph() -> None:
    captured: list[httpx.Request] = []
    client = make_client(
        captured,
        {
            "/tools/search_knowledge_graph": {"data": [{"id": "n1"}]},
            "/tools/export_content": {"content": "# Research context body"},
        },
    )

    context = dispatch.build_task_context(client, "DEMO-1")

    assert context == "# Research context body"
    search_req = captured[0]
    assert search_req.url.path == "/tools/search_knowledge_graph"
    assert json.loads(search_req.content)["query"] == "slice:DEMO-1"


def test_build_task_context_empty_subgraph_returns_none() -> None:
    captured: list[httpx.Request] = []
    client = make_client(
        captured,
        {"/tools/search_knowledge_graph": {"data": []}},
    )

    assert dispatch.build_task_context(client, "DEMO-1") is None
    # No export call should happen for an empty subgraph.
    assert all(req.url.path != "/tools/export_content" for req in captured)


# --- brief augmentation -----------------------------------------------------------


def test_augment_brief_appends_context_section() -> None:
    brief = "# Task: do the thing"
    augmented = dispatch.augment_brief(brief, "prior decision memo")

    assert augmented.startswith(brief)
    assert "## Research Context" in augmented
    assert "prior decision memo" in augmented


def test_augment_brief_empty_context_leaves_brief_unchanged() -> None:
    brief = "# Task: do the thing"
    assert dispatch.augment_brief(brief, None) == brief
    assert dispatch.augment_brief(brief, "") == brief


def test_attach_research_context_composes_both_steps() -> None:
    captured: list[httpx.Request] = []
    client = make_client(
        captured,
        {
            "/tools/search_knowledge_graph": {"data": [{"id": "n1"}]},
            "/tools/export_content": {"content": "# ctx"},
        },
    )

    brief = dispatch.attach_research_context(client, "DEMO-1", "# Task")

    assert brief == "# Task\n\n## Research Context\n\n# ctx"
