"""Slice selection: what gets dispatched next, and what does not.

The selector answers the question an adopter asks first ("what do I work on
next?"), so its ordering and exclusions are contract, not implementation detail.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SELECTOR = REPO_ROOT / "scripts/select_next_automation_slice.py"


def slice_row(
    number: int,
    slice_id: str,
    *,
    state: str = "ready",
    status: str = "ready",
    priority: int | None = None,
    dependencies: list[int] | None = None,
    automation_eligible: bool = True,
    operator_gates: list[str] | None = None,
) -> dict:
    row = {
        "slice_id": slice_id,
        "slice_number": number,
        "group": "technical",
        "title": f"slice {slice_id}",
        "state": state,
        "status": status,
        "dependencies": dependencies or [],
        "blocks": [],
        "operator_gates": operator_gates or [],
        "checkpoint": "low-risk",
        "automation_eligible": automation_eligible,
        "priority": priority if priority is not None else number,
        "risk": "low",
        "effort": "small",
        "tier": "P0",
    }
    return row


def run_selector(
    tmp_path: Path,
    rows: list[dict],
    *extra: str,
    fanout_limit: int = 1,
) -> subprocess.CompletedProcess[str]:
    tree = {
        "schema_version": 2,
        "generated_at": "2026-10-05T00:00:00Z",
        "source_backlog_path": ".docs/slice_backlog.md",
        "default_fanout_limit": fanout_limit,
        "slices": rows,
    }
    path = tmp_path / "tree.json"
    path.write_text(json.dumps(tree), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(SELECTOR), "--tree", str(path), *extra],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def picked(result: subprocess.CompletedProcess[str]) -> list[str]:
    return [row["slice_id"] for row in json.loads(result.stdout)["selected"]]


def test_priority_beats_slice_number(tmp_path: Path) -> None:
    result = run_selector(
        tmp_path,
        [
            slice_row(1, "LATE-1", priority=9),
            slice_row(2, "SOON-1", priority=1),
        ],
    )

    assert result.returncode == 0
    assert picked(result) == ["SOON-1"]


def test_missing_priority_falls_back_to_slice_number(tmp_path: Path) -> None:
    first = slice_row(1, "A-1")
    first.pop("priority")
    second = slice_row(2, "B-1")
    second.pop("priority")

    result = run_selector(tmp_path, [second, first])

    assert result.returncode == 0
    assert picked(result) == ["A-1"]


def test_gated_slices_are_never_selected(tmp_path: Path) -> None:
    result = run_selector(
        tmp_path,
        [
            slice_row(1, "GATED-1", state="gated"),
            slice_row(2, "READY-1", priority=5),
        ],
    )

    assert picked(result) == ["READY-1"]


def test_operator_gates_exclude_a_slice(tmp_path: Path) -> None:
    result = run_selector(
        tmp_path,
        [
            slice_row(1, "HELD-1", operator_gates=["operator approval"]),
            slice_row(2, "READY-1"),
        ],
    )

    assert picked(result) == ["READY-1"]


def test_slices_are_not_selected_over_incomplete_dependencies(tmp_path: Path) -> None:
    result = run_selector(
        tmp_path,
        [
            slice_row(1, "BLOCKED-BY-DEP", dependencies=[2]),
            slice_row(2, "DEP-1", state="shaped", status="planned"),
        ],
    )

    assert result.returncode == 1
    assert picked(result) == []


def test_dependencies_in_a_terminal_state_unblock(tmp_path: Path) -> None:
    result = run_selector(
        tmp_path,
        [
            slice_row(1, "READY-NOW", dependencies=[2]),
            slice_row(2, "DONE-1", state="validated", status="done"),
        ],
    )

    assert result.returncode == 0
    assert picked(result) == ["READY-NOW"]


def test_non_automation_eligible_slices_are_skipped(tmp_path: Path) -> None:
    result = run_selector(
        tmp_path,
        [
            slice_row(1, "MANUAL-1", automation_eligible=False),
            slice_row(2, "AUTO-1"),
        ],
    )

    assert picked(result) == ["AUTO-1"]


def test_the_tree_default_caps_the_wave(tmp_path: Path) -> None:
    result = run_selector(
        tmp_path,
        [slice_row(1, "A-1"), slice_row(2, "B-1"), slice_row(3, "C-1")],
        fanout_limit=2,
    )

    assert picked(result) == ["A-1", "B-1"]


def test_max_can_lower_the_wave_but_not_raise_it(tmp_path: Path) -> None:
    rows = [slice_row(1, "A-1"), slice_row(2, "B-1"), slice_row(3, "C-1")]

    lowered = run_selector(tmp_path, rows, "--max", "1", fanout_limit=2)
    raised = run_selector(tmp_path, rows, "--max", "5", fanout_limit=2)

    assert picked(lowered) == ["A-1"]
    assert picked(raised) == ["A-1", "B-1"]


def test_nothing_runnable_is_exit_one_with_an_empty_payload(tmp_path: Path) -> None:
    result = run_selector(tmp_path, [slice_row(1, "GATED-1", state="gated")])

    assert result.returncode == 1
    assert picked(result) == []
