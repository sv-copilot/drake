"""The slice-pipeline-local bundle must ship everything it references.

The installer used to reference template files and scripts that did not exist in
the repository, so an adopter's first command died with a traceback and nothing in
CI noticed. These tests are the cheap guard for that class of defect.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"


def _load_installer():
    """Import scripts/sync_slice_pipeline_local.py without a package layout."""
    sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        return importlib.import_module("sync_slice_pipeline_local")
    finally:
        sys.path.pop(0)


installer = _load_installer()


def test_every_template_asset_exists() -> None:
    missing = [
        rel_path
        for rel_path in installer.TEMPLATE_FILES
        if not (installer.TEMPLATE_ROOT / rel_path).is_file()
    ]

    assert missing == [], f"template bundle is missing: {missing}"


def test_every_harness_view_source_exists() -> None:
    for harness, views in installer.HARNESS_VIEW_FILES.items():
        for source, dest in views:
            assert (installer.TEMPLATE_ROOT / source).is_file(), f"{harness}: {source}"
            assert dest and not dest.startswith("/"), f"{harness}: {dest}"


def test_installer_and_runner_agree_on_harness_ids() -> None:
    """The installer and the runner must accept exactly the same harness ids."""
    import re

    runner_source = (
        REPO_ROOT / "tools" / "slice-agent-runner" / "src" / "harnesses.ts"
    ).read_text(encoding="utf-8")
    runner_ids = re.findall(r'^    id: "([a-z]+)",$', runner_source, flags=re.MULTILINE)

    assert runner_ids, "could not parse harness ids out of harnesses.ts"
    assert tuple(runner_ids) == tuple(installer.HARNESS_IDS)


def test_every_repo_script_exists() -> None:
    missing = [
        name
        for name in installer.REPO_SCRIPTS_TO_INSTALL
        if not (SCRIPTS_DIR / name).is_file()
    ]

    assert missing == [], f"installer copies missing scripts: {missing}"


def test_missing_bundle_assets_reports_nothing_for_this_tree() -> None:
    assert installer.missing_bundle_assets() == []


def test_installed_selector_and_its_dependency_are_both_offered() -> None:
    """The generated config runs the selector, so the selector must be installed."""
    installed = installer.installed_paths_for(["cursor"])

    assert "scripts/select_next_automation_slice.py" in installed
    assert "scripts/slice_lifecycle.py" in installed


def test_runner_required_files_are_installed_or_adopter_supplied() -> None:
    """Files the runner's check demands must be installed, not assumed.

    ``tools/slice-agent-runner`` fails ``check`` when any of these is absent. The
    dependency tree and backlog are authored by the adopter (the installer writes
    placeholders for both), and everything else has to come from the bundle.
    """
    installed = installer.installed_paths_for(["cursor"])
    adopter_authored = {".docs/slice_dependency_tree.json", ".docs/slice_backlog.md"}
    runner_required = {
        "AGENTS.md",
        ".docs/git_workflow.md",
        ".docs/agent_automations.md",
        ".docs/agent_prompts/slice-pipeline-automation.md",
        ".docs/agent_prompts/slice-pipeline-handoff-contract.md",
    }

    assert runner_required <= installed
    assert runner_required.isdisjoint(adopter_authored)
