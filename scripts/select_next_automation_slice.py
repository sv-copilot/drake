#!/usr/bin/env python3
"""Select the next automation-eligible slice from the dependency tree.

Prints JSON to stdout for webhook, GitHub Actions, and slice-agent-runner
consumption.

Usage:
  python3 scripts/select_next_automation_slice.py
  python3 scripts/select_next_automation_slice.py --tree .docs/slice_dependency_tree.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from slice_lifecycle import canonical_state, is_runnable_state, is_terminal_state, load_dependency_tree


def slice_by_number(tree: dict) -> dict[int, dict]:
    return {row["slice_number"]: row for row in tree["slices"]}


def is_done(row: dict) -> bool:
    status = str(row.get("status", "")).lower()
    state = canonical_state(row.get("state"))
    return status in {"done"} or is_terminal_state(state)


def is_runnable(row: dict) -> bool:
    status = str(row.get("status", "")).lower()
    state = canonical_state(row.get("state"))
    if state == "gated" or row.get("operator_gates"):
        return False
    if status != "ready" and not is_runnable_state(state):
        return False
    if not row.get("automation_eligible", False):
        return False
    return True


def deps_complete(row: dict, by_number: dict[int, dict]) -> bool:
    for dep in row.get("dependencies", []):
        dep_row = by_number.get(dep)
        if dep_row is None or not is_done(dep_row):
            return False
    return True


def fanout_limit_for_rank(rank: int, tree: dict) -> int:
    del rank
    return int(tree.get("default_fanout_limit", 3))


def select_runnable_slices(
    tree: dict,
    *,
    max_results: int | None = None,
) -> list[dict]:
    by_number = slice_by_number(tree)
    runnable: list[dict] = []

    for row in sorted(tree["slices"], key=lambda item: item["slice_number"]):
        if not is_runnable(row):
            continue
        if not deps_complete(row, by_number):
            continue
        runnable.append(row)

    if not runnable:
        return []

    wave_fanout = fanout_limit_for_rank(runnable[0]["slice_number"], tree)
    cap = wave_fanout if max_results is None else min(wave_fanout, max_results)
    return runnable[: max(cap, 0)]


def build_payload(tree_path: Path, tree: dict, selected: list[dict]) -> dict:
    fanout_limit = (
        fanout_limit_for_rank(selected[0]["slice_number"], tree) if selected else None
    )
    return {
        "dependency_tree_path": str(tree_path),
        "fanout_limit": fanout_limit,
        "selected": [
            {
                "slice_id": row["slice_id"],
                "target_slice_id": row["slice_id"],
                "slice_number": row["slice_number"],
                "target_slice_number": row["slice_number"],
                "title": row.get("title"),
                "target_slice_title": row.get("title"),
                "operator_gates": row.get("operator_gates", []),
            }
            for row in selected
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tree",
        type=Path,
        default=Path(".docs/slice_dependency_tree.json"),
        help="Path to slice dependency tree JSON",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=None,
        help="Optional cap on results (still respects default_fanout_limit)",
    )
    args = parser.parse_args(argv)

    if not args.tree.is_file():
        print(f"dependency tree not found: {args.tree}", file=sys.stderr)
        return 2

    tree = load_dependency_tree(args.tree)
    selected = select_runnable_slices(tree, max_results=args.max)
    payload = build_payload(args.tree, tree, selected)
    print(json.dumps(payload, indent=2))
    return 0 if selected else 1


if __name__ == "__main__":
    raise SystemExit(main())
