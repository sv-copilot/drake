"""Content slice kind: scenes as first-class dispatchable slices.

Extends the Drake slice model with a ``kind`` discriminator:

* ``product`` — code/product unit; acceptance routes to test runners (unchanged).
* ``content`` — creative scene; acceptance routes to saimon continuity/lore/style
  checks instead of test runners.

A content slice carries a ``content_brief`` describing the scene. The lifecycle
phases (REFINE → DISPATCH → VERIFY → SYNC) stay the same; only acceptance changes.
"""

from __future__ import annotations

import json
from typing import Any

SLICE_KINDS = ("product", "content")
DEFAULT_KIND = "product"

CONTENT_BRIEF_FIELDS = (
    "scene_id",
    "beats",
    "pov",
    "characters",
    "setting",
    "continuity_constraints",
    "voice_profile",
)

CONTENT_BRIEF_LIST_FIELDS = frozenset({"beats", "characters", "continuity_constraints"})


def slice_kind(row: dict[str, Any]) -> str:
    """Return the slice kind, defaulting to ``product`` when absent."""
    kind = row.get("kind")
    if kind is None:
        return DEFAULT_KIND
    return kind if kind in SLICE_KINDS else DEFAULT_KIND


def validate_content_brief(brief: Any) -> list[str]:
    """Return validation errors for a content_brief (empty list when valid)."""
    if not isinstance(brief, dict):
        return ["content_brief must be an object"]

    errors: list[str] = []
    for field in CONTENT_BRIEF_FIELDS:
        if field not in brief:
            errors.append(f"content_brief missing required field: {field}")
    for field in CONTENT_BRIEF_LIST_FIELDS:
        value = brief.get(field)
        if value is not None and not isinstance(value, list):
            errors.append(f"content_brief.{field} must be a list")
    return errors


def validate_content_slice(row: dict[str, Any]) -> list[str]:
    """Return kind/content_brief validation errors for a slice row."""
    kind = row.get("kind")
    if kind is None:
        return []  # default product slice — unchanged behavior
    if kind not in SLICE_KINDS:
        return [f"kind must be one of {SLICE_KINDS}, got {kind!r}"]
    if kind == "product":
        return []

    brief = row.get("content_brief")
    if brief is None:
        return ["content slice requires content_brief"]
    return validate_content_brief(brief)


def route_acceptance(row: dict[str, Any]) -> str:
    """Return the acceptance route for a slice.

    ``content`` → ``"saimon"`` (continuity/lore/style checks);
    ``product`` → ``"tests"`` (unit/integration test runners).
    """
    return "saimon" if slice_kind(row) == "content" else "tests"


def content_acceptance_checks(brief: dict[str, Any]) -> dict[str, Any]:
    """Build the saimon verify/evaluate checks for a content brief."""
    scene_id = brief.get("scene_id") or "scene"
    return {
        "verify": f"scene {scene_id} preserves continuity and lore",
        "evaluate": {
            "content": json.dumps(brief),
            "criteria": ["consistency"],
        },
    }
