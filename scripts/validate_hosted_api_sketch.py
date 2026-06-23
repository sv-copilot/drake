#!/usr/bin/env python3
"""Validate hosted API sketch JSON against schema and semantic rules.

Usage:
  python3 scripts/validate_hosted_api_sketch.py
  python3 scripts/validate_hosted_api_sketch.py --file path/to/sketch.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = REPO_ROOT / ".docs/hosted_api_sketch.schema.json"
DEFAULT_EXAMPLE = REPO_ROOT / ".docs/examples/hosted_api_sketch.example.json"

SECRET_LIKE_PATTERNS = (
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"ghs_[A-Za-z0-9]{20,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"https?://[^\s\"']+/webhook[s]?/[^\s\"']+"),
    re.compile(r"Bearer\s+[A-Za-z0-9._-]{20,}"),
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_jsonschema():
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        import subprocess

        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet", "jsonschema"]
        )
        from jsonschema import Draft202012Validator
    return Draft202012Validator


def validate_with_schema(document: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    Draft202012Validator = ensure_jsonschema()
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(document), key=lambda err: list(err.path))
    return [
        f"schema: {err.message} ({'.'.join(str(part) for part in err.path)})"
        for err in errors
    ]


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


def find_secret_like_values(document: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for text in collect_string_values(document):
        for pattern in SECRET_LIKE_PATTERNS:
            if pattern.search(text):
                errors.append(
                    "semantic: document contains a value that looks like a secret or webhook URL"
                )
                return errors
    return errors


def validate_semantics(document: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    views = document.get("views") or {}
    dashboard = views.get("dashboard") or {}
    dispatch = views.get("dispatch") or {}

    repo_ids = {repo["id"] for repo in dashboard.get("repos") or []}
    for slice_entry in dashboard.get("slices") or []:
        repo_id = slice_entry.get("repo_id")
        if repo_id not in repo_ids:
            errors.append(
                f"semantic: slice {slice_entry.get('slice_id')!r} references unknown repo_id {repo_id!r}"
            )

    for run_entry in dashboard.get("runs") or []:
        repo_id = run_entry.get("repo_id")
        if repo_id not in repo_ids:
            errors.append(
                f"semantic: run {run_entry.get('run_id')!r} references unknown repo_id {repo_id!r}"
            )

    dispatch_repo_ids = set(repo_ids)
    for dispatch_entry in dispatch.get("webhook_dispatches") or []:
        repo_id = dispatch_entry.get("repo_id")
        if repo_id not in dispatch_repo_ids:
            errors.append(
                f"semantic: dispatch {dispatch_entry.get('dispatch_id')!r} references unknown repo_id {repo_id!r}"
            )

    orchestrator_run_id = dispatch.get("orchestrator_run_id")
    if orchestrator_run_id:
        for dispatch_entry in dispatch.get("webhook_dispatches") or []:
            if dispatch_entry.get("orchestrator_run_id") != orchestrator_run_id:
                errors.append(
                    f"semantic: dispatch {dispatch_entry.get('dispatch_id')!r} orchestrator_run_id "
                    f"does not match dispatch view"
                )

    errors.extend(find_secret_like_values(document))
    return errors


def validate_hosted_api_sketch(
    document: dict[str, Any],
    schema: dict[str, Any],
) -> list[str]:
    errors = validate_with_schema(document, schema)
    errors.extend(validate_semantics(document))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_EXAMPLE,
        help="Hosted API sketch JSON path",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA,
        help="JSON Schema path",
    )
    args = parser.parse_args(argv)

    if not args.file.is_file():
        print(f"sketch file not found: {args.file}", file=sys.stderr)
        return 2
    if not args.schema.is_file():
        print(f"schema not found: {args.schema}", file=sys.stderr)
        return 2

    document = load_json(args.file)
    schema = load_json(args.schema)
    errors = validate_hosted_api_sketch(document, schema)

    if errors:
        print("hosted API sketch validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"hosted API sketch valid: {args.file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
