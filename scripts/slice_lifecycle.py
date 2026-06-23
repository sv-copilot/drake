"""Shared slice lifecycle constants for dependency-tree tooling."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

LIFECYCLE_STATES = frozenset(
    {
        "proposed",
        "shaped",
        "ready",
        "gated",
        "running",
        "blocked",
        "review",
        "validated",
        "promoted",
        "released",
        "archived",
    }
)

# Legacy alias accepted on read; writers should emit validated.
LEGACY_DONE_STATE = "done"

CURRENT_TREE_SCHEMA_VERSION = 2

V1_SLICE_DEFAULTS = {
    "group": "technical",
    "risk": "low",
    "effort": "small",
    "tier": "P1",
}

TERMINAL_STATES = frozenset({"validated", "promoted", "released", "archived", LEGACY_DONE_STATE})

RUNNABLE_STATES = frozenset({"ready"})

LEGACY_STATUS_TO_STATE = {
    "done": "validated",
    "ready": "ready",
    "needs-research": "shaped",
    "needs-design": "shaped",
    "blocked": "blocked",
    "in progress": "running",
}


def normalize_state(value: str | None) -> str:
    if not value:
        return ""
    return str(value).strip().lower()


def canonical_state(value: str | None) -> str:
    normalized = normalize_state(value)
    if normalized == LEGACY_DONE_STATE:
        return "validated"
    return normalized


def is_terminal_state(value: str | None) -> bool:
    normalized = normalize_state(value)
    return normalized in TERMINAL_STATES or canonical_state(normalized) in TERMINAL_STATES


def is_runnable_state(value: str | None) -> bool:
    return normalize_state(value) in RUNNABLE_STATES


def expected_state_for_row(row: dict) -> str | None:
    """Return the canonical lifecycle state implied by row semantics."""
    gates = row.get("operator_gates") or []
    status = normalize_state(row.get("status"))
    state = normalize_state(row.get("state"))

    if gates:
        if state in {"ready", "shaped", "proposed"}:
            return "gated"
        if not state:
            return "gated"

    if state:
        return canonical_state(state)

    if status in LEGACY_STATUS_TO_STATE:
        return LEGACY_STATUS_TO_STATE[status]

    return None


def infer_group(slice_id: str) -> str:
    if slice_id.startswith("PROD-"):
        return "product"
    return "technical"


def normalize_slice_row(row: dict) -> dict:
    """Return a schema v2 slice row with canonical lifecycle state."""
    normalized = deepcopy(row)
    for key, value in V1_SLICE_DEFAULTS.items():
        if key == "group":
            continue
        normalized.setdefault(key, value)
    normalized["group"] = normalized.get("group") or infer_group(normalized["slice_id"])

    inferred = expected_state_for_row(normalized)
    if inferred:
        normalized["state"] = inferred
    elif normalized.get("state"):
        normalized["state"] = canonical_state(normalized["state"])
    else:
        normalized["state"] = "ready"

    return normalized


def normalize_dependency_tree(tree: dict) -> dict:
    """Return a schema v2 tree with canonical slice rows."""
    normalized = deepcopy(tree)
    normalized["schema_version"] = CURRENT_TREE_SCHEMA_VERSION
    normalized["slices"] = [normalize_slice_row(row) for row in tree.get("slices", [])]
    return normalized


def _row_migration_changes(before: dict, after: dict) -> list[str]:
    changes: list[str] = []
    slice_id = before.get("slice_id", "?")
    for key in ("state", "group", "risk", "effort", "tier"):
        if before.get(key) != after.get(key):
            changes.append(
                f"{slice_id}: {key} {before.get(key)!r} -> {after.get(key)!r}"
            )
    if "state" not in before and after.get("state"):
        changes.append(f"{slice_id}: inferred state={after['state']!r}")
    return changes


def migrate_dependency_tree(tree: dict) -> tuple[dict, list[str]]:
    """Upgrade legacy trees to canonical schema v2 form."""
    changes: list[str] = []
    source_version = int(tree.get("schema_version", 1))
    if source_version < CURRENT_TREE_SCHEMA_VERSION:
        changes.append(
            f"schema_version: {source_version} -> {CURRENT_TREE_SCHEMA_VERSION}"
        )

    migrated = normalize_dependency_tree(tree)
    for before, after in zip(tree.get("slices", []), migrated["slices"], strict=False):
        changes.extend(_row_migration_changes(before, after))

    deduped: list[str] = []
    seen: set[str] = set()
    for change in changes:
        if change not in seen:
            deduped.append(change)
            seen.add(change)
    return migrated, deduped


def trees_equivalent(left: dict, right: dict) -> bool:
    return json.dumps(left, sort_keys=True) == json.dumps(right, sort_keys=True)


def load_dependency_tree(path: Path | str) -> dict:
    """Load a dependency tree and normalize legacy v1/v2 aliases on read."""
    tree_path = Path(path)
    raw = json.loads(tree_path.read_text(encoding="utf-8"))
    return normalize_dependency_tree(raw)
