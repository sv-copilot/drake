"""Dependency-tree cycles must fail validation.

The README promises "no cycles" as a gate on the dependency tree. For a long time
it was a promise the validator did not keep: a two-slice cycle validated clean,
which means both slices were permanently undispatable and nothing said so.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = REPO_ROOT / "scripts/validate_slice_dependency_tree.py"


def slice_row(number: int, slice_id: str, dependencies: list[int]) -> dict:
    return {
        "slice_id": slice_id,
        "slice_number": number,
        "group": "technical",
        "title": f"slice {number}",
        "state": "ready",
        "status": "ready",
        "dependencies": dependencies,
        "blocks": [],
        "operator_gates": [],
        "checkpoint": "low-risk",
        "automation_eligible": True,
        "priority": number,
        "last_known_pr": None,
        "risk": "low",
        "effort": "small",
        "tier": "P0",
    }


def write_tree(path: Path, slices: list[dict]) -> Path:
    path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "generated_at": "2026-10-05T00:00:00Z",
                "source_backlog_path": ".docs/slice_backlog.md",
                "default_fanout_limit": 1,
                "slices": slices,
            }
        ),
        encoding="utf-8",
    )
    return path


def run_validator(tree_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "--tree", str(tree_path)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_acyclic_tree_passes(tmp_path: Path) -> None:
    tree = write_tree(
        tmp_path / "tree.json",
        [slice_row(1, "A-1", []), slice_row(2, "B-1", [1])],
    )

    result = run_validator(tree)

    assert result.returncode == 0, result.stderr or result.stdout


def test_two_slice_cycle_fails(tmp_path: Path) -> None:
    tree = write_tree(
        tmp_path / "tree.json",
        [slice_row(1, "A-1", [2]), slice_row(2, "B-1", [1])],
    )

    result = run_validator(tree)

    assert result.returncode == 1
    assert "dependency cycle" in result.stderr


def test_self_dependency_is_a_cycle(tmp_path: Path) -> None:
    tree = write_tree(tmp_path / "tree.json", [slice_row(1, "A-1", [1])])

    result = run_validator(tree)

    assert result.returncode == 1
    assert "dependency cycle" in result.stderr


def test_longer_cycle_names_the_loop(tmp_path: Path) -> None:
    tree = write_tree(
        tmp_path / "tree.json",
        [
            slice_row(1, "A-1", [3]),
            slice_row(2, "B-1", [1]),
            slice_row(3, "C-1", [2]),
        ],
    )

    result = run_validator(tree)

    assert result.returncode == 1
    assert "dependency cycle" in result.stderr
