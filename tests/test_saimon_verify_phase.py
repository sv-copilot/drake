from __future__ import annotations

import json
from typing import Any

import httpx

from saimon.client import SaimonClient
from saimon import verify_phase


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


# --- client evaluate + verify path -----------------------------------------------


def test_evaluate_sends_content_and_criteria() -> None:
    captured: list[httpx.Request] = []
    client = make_client(
        captured,
        {"/tools/evaluate_content": {"data": {"scores": []}}},
    )

    client.evaluate("some diff", criteria=["consistency"])

    assert captured[0].url.path == "/tools/evaluate_content"
    assert json.loads(captured[0].content) == {
        "content": "some diff",
        "criteria": ["consistency"],
    }


def test_verify_uses_verify_claim_endpoint() -> None:
    captured: list[httpx.Request] = []
    client = make_client(
        captured,
        {"/tools/verify_claim": {"data": {"overall_verdict": "supported"}}},
    )

    client.verify("implementation matches spec")

    assert captured[0].url.path == "/tools/verify_claim"


# --- check_against_research --------------------------------------------------------


def test_check_against_research_supported() -> None:
    captured: list[httpx.Request] = []
    client = make_client(
        captured,
        {"/tools/verify_claim": {"data": {"overall_verdict": "supported"}}},
    )

    verdict = verify_phase.check_against_research(client, "spec", "diff")

    assert verdict == verify_phase.SUPPORTED
    assert "implementation matches spec" in json.loads(captured[0].content)["claim"]


def test_check_against_research_refuted() -> None:
    captured: list[httpx.Request] = []
    client = make_client(
        captured,
        {"/tools/verify_claim": {"overall_verdict": "refuted"}},
    )

    assert verify_phase.check_against_research(client, "spec", "diff") == verify_phase.REFUTED


def test_check_against_research_unknown_defaults_inconclusive() -> None:
    captured: list[httpx.Request] = []
    client = make_client(
        captured,
        {"/tools/verify_claim": {"overall_verdict": "gibberish"}},
    )

    assert verify_phase.check_against_research(client, "spec", "diff") == verify_phase.INCONCLUSIVE


def test_check_against_research_missing_verdict_inconclusive() -> None:
    captured: list[httpx.Request] = []
    client = make_client(
        captured,
        {"/tools/verify_claim": {"data": {}}},
    )

    assert verify_phase.check_against_research(client, "spec", "diff") == verify_phase.INCONCLUSIVE


# --- detect_regressions -------------------------------------------------------------


def test_detect_regressions_surfaces_consistency_findings() -> None:
    captured: list[httpx.Request] = []
    scores = [
        {"criterion": "consistency", "score": 0.2, "notes": "drift detected"},
        {"criterion": "clarity", "score": 0.9, "notes": "clear"},
    ]
    client = make_client(
        captured,
        {"/tools/evaluate_content": {"data": {"scores": scores}}},
    )

    findings = verify_phase.detect_regressions(client, "diff")

    assert findings == [scores[0]]
    payload = json.loads(captured[0].content)
    assert payload["criteria"] == ["consistency"]


def test_detect_regressions_no_consistency_returns_empty() -> None:
    captured: list[httpx.Request] = []
    client = make_client(
        captured,
        {
            "/tools/evaluate_content": {
                "data": {"scores": [{"criterion": "clarity", "score": 0.9}]}
            }
        },
    )

    assert verify_phase.detect_regressions(client, "diff") == []


# --- verify report -------------------------------------------------------------------


def test_build_verify_report_composes_verdict_and_findings() -> None:
    captured: list[httpx.Request] = []
    client = make_client(
        captured,
        {
            "/tools/verify_claim": {"data": {"overall_verdict": "refuted"}},
            "/tools/evaluate_content": {
                "data": {
                    "scores": [{"criterion": "consistency", "score": 0.1, "notes": "x"}]
                }
            },
        },
    )

    report = verify_phase.build_verify_report(client, "spec", "diff")

    assert report["verdict"] == verify_phase.REFUTED
    assert report["findings"][0]["criterion"] == "consistency"
