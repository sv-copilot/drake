"""`drake-setup` is the front door, so it gets tested like one.

The scenarios below are the promises the wizard makes: a plan run changes nothing, an apply run
reaches the level it claims, the seeded plan survives the installer (which ships its own
placeholder), the same command twice is idempotent, and an unreachable level is refused with a
reason instead of half-applied.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SETUP = REPO_ROOT / "scripts" / "drake-setup.py"
RUNNER = REPO_ROOT / "tools" / "slice-agent-runner" / "dist" / "index.js"


def make_product(tmp_path: Path) -> Path:
    """A small but real product repository: git, an npm test script, one source file."""
    target = tmp_path / "product"
    (target / "src").mkdir(parents=True)
    (target / "src" / "index.ts").write_text("export const x = 1;\n", encoding="utf-8")
    (target / "package.json").write_text(
        json.dumps({"name": "product", "scripts": {"test": "echo tests pass", "lint": "echo lint ok"}}),
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q"], cwd=target, check=True)
    subprocess.run(["git", "add", "-A"], cwd=target, check=True)
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "init"],
        cwd=target,
        check=True,
    )
    return target


def run_setup(target: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SETUP), "--target", str(target), "--project-id", "product", *args],
        text=True,
        capture_output=True,
        check=False,
    )


def untracked(target: Path) -> set[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain"], cwd=target, text=True, capture_output=True, check=True
    )
    return {line[3:] for line in result.stdout.splitlines() if line.strip()}


def test_a_plan_run_changes_nothing(tmp_path: Path) -> None:
    target = make_product(tmp_path)

    result = run_setup(target)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "plan only" in result.stdout
    assert untracked(target) == set(), "a plan run must not write anything"


def test_level_zero_reaches_level_zero(tmp_path: Path) -> None:
    target = make_product(tmp_path)

    result = run_setup(target, "--level", "L0", "--apply")
    assert result.returncode == 0, result.stdout + result.stderr

    config = json.loads((target / ".drake" / "slice-pipeline.config.json").read_text(encoding="utf-8"))
    assert config["harness"]["id"], "a harness must be recorded even at L0"
    assert "npm test" in json.dumps(config), "detected validation commands must reach the config"
    assert (target / "SETUP.md").is_file(), "the runbook is the handover"
    assert (target / "AGENTS.md").is_file()

    tree = json.loads((target / ".docs" / "slice_dependency_tree.json").read_text(encoding="utf-8"))
    ids = [row["slice_id"] for row in tree["slices"]]
    assert ids[:3] == ["PRODUCT-1", "PRODUCT-2", "PRODUCT-3"], (
        "the seeded plan must survive the installer's own placeholder tree"
    )
    assert all((target / ".docs" / "slices" / f"{i}.md").is_file() for i in ids)

    validated = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "validate_slice_dependency_tree.py"), "--tree", str(target / ".docs" / "slice_dependency_tree.json")],
        text=True,
        capture_output=True,
        check=False,
    )
    assert validated.returncode == 0, validated.stdout + validated.stderr


def test_a_level_that_needs_a_harness_is_refused_without_one(tmp_path: Path) -> None:
    target = make_product(tmp_path)

    result = run_setup(target, "--level", "L1", "--harness", "generic", "--apply")
    assert result.returncode == 2, "an unreachable level must be refused, not half-applied"
    assert "harness-command" in (result.stdout + result.stderr)
    assert untracked(target) == set(), "a refusal must not leave a partial install behind"


def test_applying_twice_changes_nothing_the_second_time(tmp_path: Path) -> None:
    target = make_product(tmp_path)
    args = ("--level", "L0", "--apply")

    first = run_setup(target, *args)
    assert first.returncode == 0, first.stdout + first.stderr
    after_first = untracked(target)

    second = run_setup(target, *args)
    assert second.returncode == 0, second.stdout + second.stderr
    assert "(nothing)" in second.stdout, "the second run must report that it wrote nothing"
    assert untracked(target) == after_first


def test_level_one_wires_a_harness_and_proves_it_without_a_model(tmp_path: Path) -> None:
    target = make_product(tmp_path)
    if not RUNNER.is_file():
        # A clone without a built runner can still be configured, but the dry-run proof cannot run.
        result = run_setup(target, "--level", "L1", "--harness", "generic",
                           "--harness-command", "bash scripts/harness_stub.sh {prompt_file}", "--apply")
        assert "runner not built" in result.stdout
        return

    result = run_setup(
        target,
        "--level",
        "L1",
        "--harness",
        "generic",
        "--harness-command",
        f"bash {REPO_ROOT}/scripts/harness_stub.sh {{prompt_file}}",
        "--apply",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "dry run renders the task packet without calling a model" in result.stdout
