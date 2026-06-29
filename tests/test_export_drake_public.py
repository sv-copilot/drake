from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from scripts.validate_drake_export import validate_tree

REPO_ROOT = Path(__file__).resolve().parents[1]
EXPORT_SCRIPT = REPO_ROOT / "scripts/export_drake_public.py"
VALIDATE_SCRIPT = REPO_ROOT / "scripts/validate_drake_export.py"


def run_export(output: Path, *, dry_run: bool = False) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(EXPORT_SCRIPT), "--output", str(output)]
    if dry_run:
        cmd.append("--dry-run")
    return subprocess.run(cmd, text=True, capture_output=True, check=False)


def test_dry_run_lists_paths(tmp_path: Path) -> None:
    result = run_export(tmp_path / "out", dry_run=True)
    assert result.returncode == 0, result.stderr or result.stdout
    assert "adapters/CONTRACT.md" in result.stdout
    assert "scripts/export_drake_public.py" in result.stdout
    assert not (tmp_path / "out").exists()


def test_export_writes_tree(tmp_path: Path) -> None:
    output = tmp_path / "drake-export"
    result = run_export(output)
    assert result.returncode == 0, result.stderr or result.stdout
    assert (output / "README.md").is_file()
    assert (output / "docs/getting-started.md").is_file()
    assert (output / "adapters/cursor/CURSOR-ADAPTER.md").is_file()
    assert (output / "scripts/dev-hosted.sh").is_file()
    assert (output / ".docs/hosted_api_sketch.schema.json").is_file()
    assert (output / ".docs/mcp_environment_profile.schema.json").is_file()
    assert (output / ".docs/slice_dependency_tree.schema.json").is_file()
    assert not (output / ".docs/projects-registry.json").exists()
    assert (output / ".docs/examples/projects-registry.example.json").is_file()


def test_scrub_validator_allows_public_drake_examples(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("Drake documents the example-app fixture.\n", encoding="utf-8")

    assert validate_tree(tmp_path) == []


def test_scrub_validator_rejects_private_control_plane_markers(tmp_path: Path) -> None:
    notes = tmp_path / "notes.md"
    private_marker = "simon" + "-projects"
    notes.write_text(f"Do not export {private_marker} planning notes.\n", encoding="utf-8")

    assert validate_tree(tmp_path) == ["private control-plane marker in notes.md"]


def test_current_tree_passes_scrub_validator() -> None:
    result = subprocess.run(
        [sys.executable, str(VALIDATE_SCRIPT), "--tree", str(REPO_ROOT)],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
