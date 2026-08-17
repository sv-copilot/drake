"""VERIFY-phase binding for the saimon ↔ Drake integration.

Implements architecture §5 "VERIFY phase": validate the implementation against
research findings and detect regressions against known facts.

* :func:`check_against_research` → ``saimon.verify("implementation matches spec")``
* :func:`detect_regressions`     → ``saimon.evaluate(diff, criteria=["consistency"])``
* :func:`build_verify_report`    → compose both into the evidence narrative
"""

from __future__ import annotations

from typing import Any

from saimon.client import SaimonClient

SUPPORTED = "SUPPORTED"
REFUTED = "REFUTED"
INCONCLUSIVE = "INCONCLUSIVE"


def check_against_research(
    client: SaimonClient,
    spec: str,
    diff: str,
) -> str:
    """Verify that *diff* implements *spec*, returning a structured verdict.

    Returns one of ``SUPPORTED`` / ``REFUTED`` / ``INCONCLUSIVE``.
    """
    claim = f"implementation matches spec:\n{spec}\n\n{diff}"
    response = client.verify(claim)
    return _normalize_verdict(response)


def detect_regressions(client: SaimonClient, diff: str) -> list[dict[str, Any]]:
    """Surface consistency findings for *diff* via saimon evaluate."""
    response = client.evaluate(diff, criteria=["consistency"])
    return _extract_findings(response)


def build_verify_report(
    client: SaimonClient,
    spec: str,
    diff: str,
) -> dict[str, Any]:
    """Compose a VERIFY-phase report for the evidence narrative."""
    return {
        "verdict": check_against_research(client, spec, diff),
        "findings": detect_regressions(client, diff),
    }


def _normalize_verdict(response: Any) -> str:
    """Map a saimon verdict payload to a canonical verdict constant."""
    verdict: Any = None
    if isinstance(response, dict):
        verdict = response.get("overall_verdict")
        if verdict is None and isinstance(response.get("data"), dict):
            verdict = response["data"].get("overall_verdict")
    elif isinstance(response, str):
        verdict = response

    if verdict is None:
        return INCONCLUSIVE

    lowered = str(verdict).lower()
    if lowered == "supported":
        return SUPPORTED
    if lowered == "refuted":
        return REFUTED
    return INCONCLUSIVE


def _extract_findings(response: Any) -> list[dict[str, Any]]:
    """Extract consistency findings from a saimon evaluate payload."""
    if not isinstance(response, dict):
        return []
    data = response.get("data", response)
    if not isinstance(data, dict):
        return []
    scores = data.get("scores")
    if not isinstance(scores, list):
        scores = response.get("scores")
    if not isinstance(scores, list):
        return []
    return [
        score
        for score in scores
        if isinstance(score, dict) and score.get("criterion") == "consistency"
    ]
