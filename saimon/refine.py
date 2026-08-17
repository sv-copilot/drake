"""REFINE-phase binding for the saimon ↔ Drake integration.

Implements architecture §5 "REFINE phase":

* technical audit     → :func:`surface_research`  (saimon.search)
* research solutions  → :func:`verify_approach`   (saimon.verify)
* document decisions  → :func:`record_decision`   (saimon.generate, decision_record)
"""

from __future__ import annotations

from typing import Any

from saimon.client import SaimonClient


def surface_research(
    client: SaimonClient,
    topic: str,
    *,
    limit: int = 5,
) -> Any:
    """Surface prior research for *topic* via the saimon knowledge graph."""
    return client.search(topic, limit=limit)


def verify_approach(client: SaimonClient, claim: str) -> Any:
    """Verify whether an approach described by *claim* is viable."""
    return client.verify(claim)


def record_decision(client: SaimonClient, memo: str) -> Any:
    """Record a decision memo into the saimon knowledge graph."""
    return client.generate(memo, content_type="decision_record")
