#!/usr/bin/env python3
"""Shared constants and helpers for MCP environment profile documents."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

TIER_NAMES = ("dev", "staging", "production")
TRANSPORT_TYPES = ("stdio", "sse", "streamable_http")

# Patterns that suggest a literal secret was committed into a profile file.
SECRET_LIKE_PATTERNS = (
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"ghs_[A-Za-z0-9]{20,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*\S+"),
    re.compile(r"Bearer\s+[A-Za-z0-9._-]{20,}"),
)


def load_profile(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_server_entries(profile: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    entries: list[tuple[str, str, dict[str, Any]]] = []
    for tier_name, tier in (profile.get("tiers") or {}).items():
        for server_name, server in (tier.get("mcp_servers") or {}).items():
            entries.append((tier_name, server_name, server))
    return entries


def collect_string_values(value: Any) -> list[str]:
    strings: list[str] = []
    if isinstance(value, str):
        strings.append(value)
    elif isinstance(value, dict):
        for nested in value.values():
            strings.extend(collect_string_values(nested))
    elif isinstance(value, list):
        for nested in value:
            strings.extend(collect_string_values(nested))
    return strings


def generate_placeholder_profile(
    project_id: str,
    *,
    description: str | None = None,
) -> dict[str, Any]:
    """Return a schema-valid starter profile for a bootstrapped product repo."""
    profile_id = project_id.strip().lower()
    profile_id = re.sub(r"[^a-z0-9-]+", "-", profile_id).strip("-")
    if not profile_id or not profile_id[0].isalpha():
        profile_id = f"project-{profile_id or 'placeholder'}"

    summary = description or (
        f"Placeholder MCP environment profile for {profile_id}. "
        "Replace disabled servers before enabling automation."
    )
    return {
        "schema_version": 1,
        "profile_id": profile_id,
        "description": summary,
        "default_tier": "dev",
        "credential_policy": {
            "forbidden_in_tiers": ["dev"],
            "human_gate_tiers": ["production"],
        },
        "tiers": {
            "dev": {
                "description": "Local development; add MCP servers as tooling needs arise.",
                "mcp_servers": {
                    "placeholder": {
                        "enabled": False,
                        "transport": "stdio",
                        "command": "echo",
                        "args": ["mcp-not-configured"],
                        "credential_refs": [],
                        "notes": (
                            "Scaffold placeholder. Remove or replace when declaring "
                            "real MCP servers."
                        ),
                    }
                },
            }
        },
    }


def find_secret_like_values(profile: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for text in collect_string_values(profile):
        for pattern in SECRET_LIKE_PATTERNS:
            if pattern.search(text):
                errors.append(
                    f"semantic: profile contains secret-like value matching {pattern.pattern!r}"
                )
                break
    return errors
