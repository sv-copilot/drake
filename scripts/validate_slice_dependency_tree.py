#!/usr/bin/env python3
"""Validate slice dependency tree JSON against schema and lifecycle semantics.

Usage:
  python3 scripts/validate_slice_dependency_tree.py
  python3 scripts/validate_slice_dependency_tree.py --tree .docs/slice_dependency_tree.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from slice_lifecycle import (
    is_terminal_state,
    load_dependency_tree,
    normalize_state,
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_with_schema(tree: dict, schema: dict) -> list[str]:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        import subprocess

        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet", "jsonschema"]
        )
        from jsonschema import Draft202012Validator

    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(tree), key=lambda err: list(err.path))
    return [f"schema: {err.message} ({'.'.join(str(part) for part in err.path)})" for err in errors]


def validate_semantics(tree: dict) -> list[str]:
    errors: list[str] = []
    slices = tree.get("slices", [])
    by_number = {row["slice_number"]: row for row in slices}
    seen_ids: set[str] = set()

    for row in slices:
        slice_id = row["slice_id"]
        if slice_id in seen_ids:
            errors.append(f"semantic: duplicate slice_id {slice_id}")
        seen_ids.add(slice_id)

        for dep in row.get("dependencies", []):
            if dep not in by_number:
                errors.append(
                    f"semantic: {slice_id} dependency {dep} missing from tree"
                )

        for blocked in row.get("blocks", []):
            if blocked not in by_number:
                errors.append(
                    f"semantic: {slice_id} blocks unknown slice_number {blocked}"
                )

        gates = row.get("operator_gates") or []
        state = normalize_state(row.get("state"))
        status = normalize_state(row.get("status"))

        if gates and state in {"ready", "shaped", "proposed"}:
            errors.append(
                f"semantic: {slice_id} has operator_gates but state={state}; expected gated"
            )

        if is_terminal_state(state) and status not in {"done", "blocked"}:
            if not (state == "archived" and status == "blocked"):
                errors.append(
                    f"semantic: {slice_id} terminal state={state} requires status=done"
                )

    return errors


def main(argv: list[str] | None = None) -> int:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tree",
        type=Path,
        default=repo_root / ".docs/slice_dependency_tree.json",
        help="Dependency tree JSON path",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=repo_root / ".docs/slice_dependency_tree.schema.json",
        help="JSON Schema path",
    )
    args = parser.parse_args(argv)

    if not args.tree.is_file():
        print(f"dependency tree not found: {args.tree}", file=sys.stderr)
        return 2
    if not args.schema.is_file():
        print(f"schema not found: {args.schema}", file=sys.stderr)
        return 2

    tree = load_dependency_tree(args.tree)
    schema = load_json(args.schema)
    errors = validate_with_schema(tree, schema)
    errors.extend(validate_semantics(tree))

    if errors:
        print("slice dependency tree validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"slice dependency tree valid: {args.tree}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
