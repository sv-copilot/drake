#!/usr/bin/env python3
"""Validate MCP environment profile JSON against schema and semantics.

Usage:
  python3 scripts/validate_mcp_environment_profile.py
  python3 scripts/validate_mcp_environment_profile.py --profile path/to/profile.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mcp_environment_profile import (
    TIER_NAMES,
    find_secret_like_values,
    iter_server_entries,
    load_profile,
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_with_schema(profile: dict, schema: dict) -> list[str]:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        import subprocess

        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet", "jsonschema"]
        )
        from jsonschema import Draft202012Validator

    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(profile), key=lambda err: list(err.path))
    return [
        f"schema: {err.message} ({'.'.join(str(part) for part in err.path)})"
        for err in errors
    ]


def validate_semantics(profile: dict) -> list[str]:
    errors: list[str] = []
    tiers = profile.get("tiers") or {}
    default_tier = profile.get("default_tier")

    if default_tier not in tiers:
        errors.append(
            f"semantic: default_tier {default_tier!r} missing from tiers"
        )

    policy = profile.get("credential_policy") or {}
    forbidden_tiers = set(policy.get("forbidden_in_tiers") or [])
    human_gate_tiers = set(policy.get("human_gate_tiers") or [])

    for tier_name, server_name, server in iter_server_entries(profile):
        if tier_name not in TIER_NAMES:
            errors.append(
                f"semantic: unknown tier {tier_name!r} on server {server_name!r}"
            )

        credential_refs = server.get("credential_refs") or []
        if tier_name in forbidden_tiers and credential_refs:
            errors.append(
                f"semantic: {tier_name}.{server_name} declares credential_refs "
                f"but tier is forbidden in credential_policy"
            )

        if tier_name == "production" and server.get("enabled", True):
            if tier_name not in human_gate_tiers:
                errors.append(
                    f"semantic: production.{server_name} is enabled but production "
                    "is not listed in credential_policy.human_gate_tiers"
                )

        transport = server.get("transport")
        if transport == "stdio" and not server.get("command"):
            errors.append(
                f"semantic: {tier_name}.{server_name} stdio transport requires command"
            )
        if transport in {"sse", "streamable_http"} and not server.get("url"):
            errors.append(
                f"semantic: {tier_name}.{server_name} {transport} transport requires url"
            )

    errors.extend(find_secret_like_values(profile))
    return errors


def main(argv: list[str] | None = None) -> int:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        type=Path,
        default=repo_root / "tests/fixtures/mcp_environment_profile.valid.json",
        help="MCP environment profile JSON path",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=repo_root / ".docs/mcp_environment_profile.schema.json",
        help="JSON Schema path",
    )
    args = parser.parse_args(argv)

    if not args.profile.is_file():
        print(f"profile not found: {args.profile}", file=sys.stderr)
        return 2
    if not args.schema.is_file():
        print(f"schema not found: {args.schema}", file=sys.stderr)
        return 2

    profile = load_profile(args.profile)
    schema = load_json(args.schema)
    errors = validate_with_schema(profile, schema)
    errors.extend(validate_semantics(profile))

    if errors:
        print("MCP environment profile validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"MCP environment profile valid: {args.profile}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
