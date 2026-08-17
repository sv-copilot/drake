"""SYNC-phase binding for the saimon ↔ Drake integration.

Implements architecture §5 "SYNC phase": record slice outcomes and new findings
back into the knowledge graph so future REFINE/DISPATCH cycles start warm.
Completes the Saimon ↔ Drake loop.
"""

from __future__ import annotations

import json
from typing import Any

from saimon.client import SaimonClient


def record_outcome(
    client: SaimonClient,
    slice_id: str,
    outcome: str,
    findings: list[str] | None = None,
) -> Any:
    """Record a slice outcome as a research_note in the KG.

    Idempotent: if a note for *slice_id* already exists, returns ``None`` and
    does not write a duplicate.
    """
    if _already_recorded(client, slice_id):
        return None
    payload = {
        "slice_id": slice_id,
        "outcome": outcome,
        "findings": findings or [],
    }
    note = client.generate(json.dumps(payload), content_type="research_note")
    return client.store_content(
        title=f"slice:{slice_id}",
        content_type="research_note",
        body=_note_body(note),
        metadata={"slice_id": slice_id},
    )


def sync_hook(
    client: SaimonClient,
    slice_id: str,
    outcome: str,
    findings: list[str] | None = None,
) -> Any:
    """Non-blocking sync hook for the post-merge/tree-sync path.

    Never raises: a saimon outage must not fail the tree-sync commit.
    """
    try:
        return record_outcome(client, slice_id, outcome, findings)
    except Exception:
        return None


def _already_recorded(client: SaimonClient, slice_id: str) -> bool:
    subgraph = client.search(f"research_note:{slice_id}")
    return not _is_empty(subgraph)


def _note_body(note: Any) -> str:
    if isinstance(note, str):
        return note
    if isinstance(note, dict):
        return note.get("content") or note.get("body") or json.dumps(note)
    return str(note)


def _is_empty(subgraph: Any) -> bool:
    if not subgraph:
        return True
    if isinstance(subgraph, dict):
        data = subgraph.get("data", subgraph.get("results"))
        if data is None:
            return True
        return _is_empty(data)
    if isinstance(subgraph, (list, tuple)):
        return len(subgraph) == 0
    if isinstance(subgraph, str):
        return subgraph.strip() == ""
    return False
