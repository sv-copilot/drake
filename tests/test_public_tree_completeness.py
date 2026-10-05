"""The public tree must keep the parts a private export does not produce.

The framework is exported from a private workspace whose manifest covers a *subset* of the
public repository — it lists `adapters/`, `templates/`, the runner, an allowlist of scripts and
a few docs. It does not cover `apps/`, `services/`, or the release and rehearsal scripts, and
its exporter rebuilds its output as a fresh tree.

So if an export output were ever published wholesale, the public repository would silently lose
work that only exists here: the hosted web shell, the read API, the release path, the clean-room
scripts, the example configuration. That failure is invisible until someone goes looking for a
file that is not there, and by then it is in a release.

This test makes the loss loud, in CI, on the next push — and because `scripts/cut_release.sh`
refuses to tag unless CI is green on `main`, a loss blocks the next release instead of shipping
inside it.
"""

from __future__ import annotations

import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

# Paths that exist only in the public repository: the private export cannot produce them.
PUBLIC_ONLY = (
    # hosted surfaces the export manifest does not list at all
    "apps/web/package.json",
    "apps/web/app/page.tsx",
    "services/api/pyproject.toml",
    # the runner and its contracts
    "tools/slice-agent-runner/src/harnesses.ts",
    "adapters/harnesses.json",
    "adapters/task-packet.schema.json",
    "adapters/evidence-contract.schema.json",
    # the release path
    "scripts/ci_preflight.sh",
    "scripts/cut_release.sh",
    "scripts/adoption_chain_retest.sh",
    "scripts/harness_matrix_smoke.sh",
    "scripts/adoption_smoke.sh",
    "scripts/harness_stub.sh",
    "scripts/validate_run_artifacts.py",
    "scripts/cleanroom-setup.sh",
    "scripts/cleanroom-run.sh",
    "scripts/slice-cron.sh",
    ".github/workflows/release-verify.yml",
    # the recommendations and the configuration people copy
    "docs/whitepaper.md",
    "docs/harnesses.md",
    "docs/example-configuration.md",
    "docs/scheduling.md",
    "examples/governed-workspace/.drake/slice-pipeline.config.json",
    "examples/governed-workspace/.docs/slice_dependency_tree.json",
    # the tests that keep all of the above honest
    "tests/test_release_management.py",
    "tests/test_example_configuration.py",
    "tests/test_harness_catalogue.py",
    "tests/test_public_tree_completeness.py",
    "README.md",
    "LICENSE",
)


def test_public_only_paths_are_present() -> None:
    missing = [path for path in PUBLIC_ONLY if not (REPO_ROOT / path).exists()]

    assert missing == [], (
        "these paths exist only in the public repository and are now missing:\n  "
        + "\n  ".join(missing)
        + "\nIf an export was published wholesale, its manifest does not cover these areas — "
        "restore them from git history before releasing."
    )


def test_the_hosted_surfaces_are_not_empty_shells() -> None:
    """Existence is cheap to fake; these have to have content to be worth keeping."""
    web_app = REPO_ROOT / "apps" / "web" / "app" / "page.tsx"
    api = REPO_ROOT / "services" / "api" / "pyproject.toml"
    runner = REPO_ROOT / "tools" / "slice-agent-runner" / "src" / "harnesses.ts"

    assert "export default" in web_app.read_text(encoding="utf-8") or "function" in web_app.read_text(
        encoding="utf-8"
    )
    assert "[project]" in api.read_text(encoding="utf-8")
    assert "HARNESSES" in runner.read_text(encoding="utf-8")
