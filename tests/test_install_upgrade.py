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
    installed = set(installer.TEMPLATE_FILES) | {
        f"scripts/{name}" for name in installer.REPO_SCRIPTS_TO_INSTALL
    }

    assert installer.MANAGED_PATHS <= installed


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


def test_install_leaves_adopter_owned_files_alone(tmp_path: Path) -> None:
    target = tmp_path / "product"
    target.mkdir()
    (target / "AGENTS.md").write_text("# my own contract\n", encoding="utf-8")

    run_installer(target, "--mode", "install")

    assert (target / "AGENTS.md").read_text(encoding="utf-8") == "# my own contract\n"


def test_check_reports_a_stale_managed_script_as_blocking(tmp_path: Path) -> None:
    target = tmp_path / "product"
    target.mkdir()

    assert run_installer(target, "--mode", "install").returncode == 0

    (target / "scripts/slice_lifecycle.py").write_text("# stale\n", encoding="utf-8")

    result = run_installer(target, "--mode", "check")

    assert result.returncode == 1
    assert "slice_lifecycle.py" in result.stdout
    assert "stale" in result.stdout
