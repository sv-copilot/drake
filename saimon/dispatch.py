"""DISPATCH-phase binding for the saimon ↔ Drake integration.

Implements architecture §5 "DISPATCH phase": attach research context —
evidence, prior art, verified claims — to the implementing agent's brief before
dispatch. The context is exported from the saimon knowledge graph as markdown
and appended under a ``## Research Context`` section.
"""

from __future__ import annotations

import json
from typing import Any

from saimon.client import SaimonClient

RESEARCH_CONTEXT_HEADING = "## Research Context"


def build_task_context(client: SaimonClient, slice_id: str) -> str | None:
    """Fetch the slice's KG subgraph and export it as markdown task context.

    Returns ``None`` when the subgraph is empty (no research on record), so the
    dispatch path can fall back to a plain brief.
    """
    subgraph = client.search(f"slice:{slice_id}")
    if _subgraph_is_empty(subgraph):
        return None
    exported = client.export(
        content=json.dumps(subgraph),
        format="markdown",
    )
    if isinstance(exported, dict):
        return exported.get("content") or exported.get("result")
    return exported


def augment_brief(brief: str, task_context: str | None) -> str:
    """Append a research context section to a dispatch brief.

    The brief is returned unchanged when *task_context* is empty, so a missing
    subgraph never invalidates the dispatch payload.
    """
    if not task_context:
        return brief
    return f"{brief}\n\n{RESEARCH_CONTEXT_HEADING}\n\n{task_context}"


def attach_research_context(
    client: SaimonClient,
    slice_id: str,
    brief: str,
) -> str:
    """Build task context and attach it to the brief (dispatch hook)."""
    return augment_brief(brief, build_task_context(client, slice_id))


def _subgraph_is_empty(subgraph: Any) -> bool:
    """Return True when a saimon search result carries no research entries."""
    if not subgraph:
        return True
    if isinstance(subgraph, dict):
        data = subgraph.get("data", subgraph.get("results"))
        if data is None:
            return True
        return _subgraph_is_empty(data)
    if isinstance(subgraph, (list, tuple)):
        return len(subgraph) == 0
    if isinstance(subgraph, str):
        return subgraph.strip() == ""
    return False
