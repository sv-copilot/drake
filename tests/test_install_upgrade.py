"""Re-running the installer must move the target forward, not leave it behind.

Two upgrade hazards live here:

* framework-owned tooling that is executed (the selector, the lifecycle helpers,
  the hook scripts) must be refreshed on install, or an adopter keeps executing
  old code while the config, the docs and CI describe new code;
* adopter-owned files (the agent contract, prompts, conventions) must survive an
  install untouched, because those are the files people actually edit.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
INSTALLER = SCRIPTS_DIR / "sync_slice_pipeline_local.py"
SELECTOR = SCRIPTS_DIR / "select_next_automation_slice.py"


def _load_installer():
    sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        return importlib.import_module("sync_slice_pipeline_local")
    finally:
        sys.path.pop(0)


installer = _load_installer()


def run_installer(target: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(INSTALLER),
            "--target",
            str(target),
            "--project-name",
            "Upgrade Probe",
            "--project-id",
            "upgrade-probe",
            "--github-slug",
            "probe-org/upgrade-probe",
            "--validation-commands",
            "bash scripts/ci_preflight.sh",
            *extra,
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_managed_paths_are_all_installed_by_the_bundle() -> None:
    """Framework-owned files must actually be written, for every harness choice.

    A managed path nobody installs is a rule that never applies: the refresh
    silently does nothing and the runner keeps executing old code.
    """
    cursor_only = {
        ".cursor/hooks/block-task-tool.sh",
        ".cursor/hooks/block-subagent.sh",
    }
    harness_agnostic = installer.MANAGED_PATHS - cursor_only

    for harnesses in (["cursor"], ["claude"], ["codex"], ["generic"], ["cursor", "claude"]):
        installed = installer.installed_paths_for(harnesses)
        assert harness_agnostic <= installed, harnesses

    # The Cursor hook scripts are only written when Cursor is selected, and are
    # managed so a re-install refreshes them rather than leaving a stale copy.
    assert installer.MANAGED_PATHS <= installer.installed_paths_for(["cursor"])


def test_install_refreshes_a_modified_managed_script(tmp_path: Path) -> None:
    target = tmp_path / "product"
    target.mkdir()

    assert run_installer(target, "--mode", "install").returncode == 0

    installed_selector = target / "scripts/select_next_automation_slice.py"
    installed_selector.write_text("# stale local copy\n", encoding="utf-8")

    result = run_installer(target, "--mode", "install")

    assert result.returncode == 0, result.stderr or result.stdout
    assert installed_selector.read_text(encoding="utf-8") == SELECTOR.read_text(
        encoding="utf-8"
    )


def test_check_reads_harness_settings_back_from_the_target(tmp_path: Path) -> None:
    """Install with --harness-command, check without it: not stale.

    check compares the target against the flags it is given, but the harness id,
    model and command are recorded in the installed config, so check re-reads them.
    Reporting a false "stale" here trains people to ignore the report.
    """
    target = tmp_path / "product"
    target.mkdir()

    assert (
        run_installer(
            target,
            "--mode",
            "install",
            "--harnesses",
            "generic",
            "--harness-command",
            "bash scripts/harness_stub.sh {prompt_file}",
        ).returncode
        == 0
    )

    result = run_installer(target, "--mode", "check")

    assert result.returncode == 0, result.stdout
    assert "stale" not in result.stdout


def test_install_leaves_adopter_owned_files_alone(tmp_path: Path) -> None:
    target = tmp_path / "product"
    target.mkdir()
    (target / "AGENTS.md").write_text("# my own contract\n", encoding="utf-8")

    run_installer(target, "--mode", "install")

    assert (target / "AGENTS.md").read_text(encoding="utf-8") == "# my own contract\n"


def test_install_for_codex_writes_no_cursor_or_claude_views(tmp_path: Path) -> None:
    """Harness-agnostic means: install for codex and get no other harness's files."""
    target = tmp_path / "product"
    target.mkdir()

    assert run_installer(target, "--mode", "install", "--harnesses", "codex").returncode == 0

    assert (target / "AGENTS.md").is_file()
    assert (target / ".drake/slice-pipeline.config.json").is_file()
    assert not (target / ".cursor").exists()
    assert not (target / ".claude").exists()
    assert not (target / "CLAUDE.md").exists()


def test_claude_view_is_generated_from_the_canonical_agent(tmp_path: Path) -> None:
    """One body, harness-specific frontmatter; the canonical file stays the source."""
    target = tmp_path / "product"
    target.mkdir()

    assert run_installer(target, "--mode", "install", "--harnesses", "claude").returncode == 0

    canonical = (target / ".drake/agents/slice-implementer.md").read_text(encoding="utf-8")
    claude = (target / ".claude/agents/slice-implementer.md").read_text(encoding="utf-8")

    assert claude.split("---", 2)[2] == canonical.split("---", 2)[2]
    assert "name: slice-implementer" in claude
    assert "model:" not in claude.split("---", 2)[1]


def test_check_reports_a_stale_managed_script_as_blocking(tmp_path: Path) -> None:
    target = tmp_path / "product"
    target.mkdir()

    assert run_installer(target, "--mode", "install").returncode == 0

    (target / "scripts/slice_lifecycle.py").write_text("# stale\n", encoding="utf-8")

    result = run_installer(target, "--mode", "check")

    assert result.returncode == 1
    assert "slice_lifecycle.py" in result.stdout
    assert "stale" in result.stdout


def test_the_installer_placeholder_tree_is_current_schema() -> None:
    """The first tree an adopter sees must satisfy the published schema on its own.

    It used to be schema_version 1 with a slice named after an internal smoke fixture, missing
    group/state/risk/effort/tier and relying on the v1->v2 normalizer to be accepted.
    """
    import json

    import sync_slice_pipeline_local as installer

    docs = installer.placeholder_docs(
        {
            "SLICE_BACKLOG_PATH": ".docs/slice_backlog.md",
            "DEPENDENCY_TREE_PATH": ".docs/slice_dependency_tree.json",
            "SLICE_DETAIL_DIR": ".docs/slices",
        }
    )
    tree = json.loads(next(text for path, text in docs.items() if path.endswith(".json")))

    assert tree["schema_version"] == 2
    required = ("group", "state", "risk", "effort", "tier")
    for row in tree["slices"]:
        for field in required:
            assert field in row, f"{field} missing from the placeholder slice"
        assert "SMOKE" not in row["slice_id"].upper(), "placeholder must not leak an internal fixture name"
