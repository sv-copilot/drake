#!/usr/bin/env python3
"""Export a curated Drake OSS tree.

Copies allowed artifacts into a fresh output directory (no source .git), applies
rewrite rules, and generates adopter-facing stubs. Private workspaces may keep a
manifest at `.docs/drake_public_export_manifest.md`; the public repo uses the
curated rules in this script directly.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / ".docs/drake_public_export_manifest.md"

TEXT_SUFFIXES = {
    ".md",
    ".mdc",
    ".py",
    ".sh",
    ".json",
    ".yml",
    ".yaml",
    ".txt",
    ".example",
    ".gitignore",
    ".gitattributes",
}

INCLUDE_DIRS = [
    "adapters",
    "templates/slice-pipeline-local",
    "tools/slice-agent-runner",
    ".github/workflows",
    ".cursor/skills/slice-pipeline-local",
    ".cursor/agents",
    ".cursor/hooks",
    ".docs/examples",
]

TEST_PATHS = [
    "tests/test_export_drake_public.py",
    "tests/fixtures/validation-results/sample-passed.json",
    "tests/fixtures/validation-results/sample-partial.json",
    "tests/fixtures/mcp_environment_profile.valid.json",
]

INCLUDE_FILES = [
    ".cursor/hooks.json",
    ".docs/hosted-ip-staging.md",
    ".docs/hosted_api_sketch.schema.json",
    ".docs/mcp_environment_profile.schema.json",
    ".docs/slice_dependency_tree.schema.json",
    "SECRETS.example.md",
    ".gitignore",
    "scripts/dev-hosted.sh",
    "scripts/hosted-ip-staging.sh",
]

SCRIPT_ALLOWLIST = [
    "scripts/sync_slice_pipeline_local.py",
    "scripts/sync_mcp_environment_profile.py",
    "scripts/slice_lifecycle.py",
    "scripts/select_next_automation_slice.py",
    "scripts/validate_slice_dependency_tree.py",
    "scripts/validate_mcp_environment_profile.py",
    "scripts/validate_automation_run_dir.py",
    "scripts/validate_validation_results.py",
    "scripts/validate_hosted_api_sketch.py",
    "scripts/validate_worker_credential_refs.py",
    "scripts/validation_results.py",
    "scripts/mcp_environment_profile.py",
    "scripts/automation_run_history.py",
    "scripts/fetch_github_path.py",
    "scripts/export_drake_public.py",
    "scripts/validate_drake_export.py",
]

EXCLUDE_PARTS = {
    "node_modules",
    "dist",
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".cursor/automation-runs",
}

EXCLUDE_REL_PATHS = {
    ".docs/product_strategy.md",
    ".docs/product_strategy_refinement.md",
    ".docs/course_correct_rollout.md",
    ".docs/bootstrap_spillover.json",
    ".docs/projects-registry.json",
    ".docs/slice_dependency_tree.json",
    ".docs/slice_backlog.md",
    ".docs/agent_prompts",
    ".docs/agent_automations.md",
    ".docs/agent_automation_execution_policy.md",
    ".docs/naming_decision.md",
    ".docs/drake_public_launch_policy.md",
    ".docs/drake_public_export_manifest.md",
    "AUTOMATIONS.md",
    "WORKSPACE.md",
    "ONBOARDING.md",
    "drake.code-workspace",
    "projects",
}

REWRITE_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"<workspace-root>"), "<workspace-root>"),
    (re.compile(r"<home>/"), "<home>/"),
    (re.compile(r"sv-copilot/drake"), "sv-copilot/drake"),
    (re.compile(r"\bca0e860f-c5e5-4c09-976d-cbcb13e8389f\b"), "00000000-0000-0000-0000-000000000000"),
    (re.compile(r"\bb5337289-7526-4979-8b61-d4e8cbb8bd12\b"), "00000000-0000-0000-0000-000000000000"),
    (re.compile(r"\bdbc2b006-57d6-43f5-b6be-c0a9d3db9efe\b"), "00000000-0000-0000-0000-000000000000"),
]

EXAMPLE_PRODUCT_SLUGS = ("example-app", "example-app", "example-app", "example-app")


@dataclass(frozen=True)
class PlannedPath:
    destination: Path
    source: Path | None = None
    content: str | None = None


def _rel(path: Path) -> str:
    return path.as_posix()


def _is_excluded(rel: str) -> bool:
    if rel in EXCLUDE_REL_PATHS:
        return True
    for part in EXCLUDE_PARTS:
        if f"/{part}/" in f"/{rel}/" or rel.startswith(f"{part}/") or rel == part:
            return True
    return False


def _should_rewrite(path: Path) -> bool:
    if path.name in {"hooks.json", ".gitignore"}:
        return True
    return path.suffix in TEXT_SUFFIXES or path.suffixes[-2:] == [".example", ".md"]


def apply_rewrites(text: str) -> str:
    for pattern, replacement in REWRITE_RULES:
        text = pattern.sub(replacement, text)
    for slug in EXAMPLE_PRODUCT_SLUGS:
        text = re.sub(rf"\b{re.escape(slug)}\b", "example-app", text)
    text = re.sub(r"\bsimon-projects\b", "drake", text)
    return text


def plan_export() -> list[PlannedPath]:
    planned: list[PlannedPath] = []

    for rel_dir in INCLUDE_DIRS:
        src_dir = REPO_ROOT / rel_dir
        if not src_dir.is_dir():
            continue
        for src in sorted(src_dir.rglob("*")):
            if not src.is_file():
                continue
            rel = _rel(src.relative_to(REPO_ROOT))
            if _is_excluded(rel):
                continue
            planned.append(PlannedPath(destination=Path(rel), source=src))

    for rel_file in INCLUDE_FILES:
        src = REPO_ROOT / rel_file
        if src.is_file():
            planned.append(PlannedPath(destination=Path(rel_file), source=src))

    for rel_script in SCRIPT_ALLOWLIST:
        src = REPO_ROOT / rel_script
        if src.is_file():
            planned.append(PlannedPath(destination=Path(rel_script), source=src))

    for rel_test in TEST_PATHS:
        src = REPO_ROOT / rel_test
        if src.is_file():
            planned.append(PlannedPath(destination=Path(rel_test), source=src))

    for rel_path, content in generated_artifacts():
        planned.append(PlannedPath(destination=rel_path, content=content))

    return planned


def drake_agents_stub() -> str:
    return """# AGENTS.md

Operating contract for AI agents working in a **Drake** governance repository.

Drake provides repository-native governance for AI-assisted development: slice
planning, dependency graphs, adapter contracts, and validation tooling.

## Branch policy

- `main` — stable integration branch for adopters.
- `ai-dev` — agent integration branch when using Drake automations.
- `agent/*` or `cursor/*` — feature branches for isolated slices.

## Validation before PR

From repo root:

```bash
bash scripts/ci_preflight.sh
```

## Scope

- Keep product runtime code in its own repositories.
- Use `.docs/examples/` for fictional registry and slice-tree samples.
- Do not commit secrets, live automation tokens, or operator registry data.

See `docs/getting-started.md` for a minimal adoption path.
"""


def drake_readme_stub() -> str:
    return """# Drake

**Autonomous Development Governance** — repository-native governance for
AI-assisted software development.

## Quick start

```bash
bash scripts/ci_preflight.sh
```

See `docs/getting-started.md` and `adapters/CONTRACT.md`.
"""


def drake_getting_started() -> str:
    return """# Getting started

1. Clone `sv-copilot/drake` (public OSS export).
2. Copy `.docs/examples/projects-registry.example.json` to your operator layout.
3. Install slice-pipeline-local from `templates/slice-pipeline-local/`.
4. Run `bash scripts/ci_preflight.sh` before opening a PR.

Full guides land in later documentation slices.
"""


def drake_ci_preflight() -> str:
    return """#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

echo "== Drake CI preflight =="

echo "-- python scripts compile"
python3 -m py_compile scripts/*.py

echo "-- drake export scrub validation"
python3 scripts/validate_drake_export.py --tree "$repo_root"

echo "-- example registry JSON"
python3 -m json.tool .docs/examples/projects-registry.example.json >/dev/null
python3 -m json.tool .docs/examples/slice_dependency_tree.example.json >/dev/null

echo "-- dependency tree example validation"
python3 scripts/validate_slice_dependency_tree.py \\
  --tree .docs/examples/slice_dependency_tree.example.json

echo "-- MCP environment profile validation"
python3 scripts/validate_mcp_environment_profile.py

echo "-- validation_results schema fixtures"
python3 scripts/validate_validation_results.py --file tests/fixtures/validation-results/sample-passed.json

echo "-- export smoke tests"
python3 -c "import pytest" 2>/dev/null || python3 -m pip install --user pytest
python3 -m pytest tests/test_export_drake_public.py -q

echo "-- slice-agent-runner build"
npm --prefix tools/slice-agent-runner ci
npm --prefix tools/slice-agent-runner run typecheck
npm --prefix tools/slice-agent-runner run build

echo "ci preflight passed"
"""


def generated_artifacts() -> list[tuple[Path, str]]:
    return [
        (Path("AGENTS.md"), drake_agents_stub()),
        (Path("README.md"), drake_readme_stub()),
        (Path("docs/getting-started.md"), drake_getting_started()),
        (Path("scripts/ci_preflight.sh"), drake_ci_preflight()),
    ]


def write_planned(plan: PlannedPath, output_root: Path) -> None:
    dest = output_root / plan.destination
    dest.parent.mkdir(parents=True, exist_ok=True)
    if plan.content is not None:
        dest.write_text(plan.content, encoding="utf-8")
        if dest.suffix == ".sh":
            dest.chmod(0o755)
        return
    assert plan.source is not None
    if _should_rewrite(plan.source):
        text = apply_rewrites(plan.source.read_text(encoding="utf-8"))
        dest.write_text(text, encoding="utf-8")
    else:
        shutil.copy2(plan.source, dest)


def export_tree(output_root: Path, *, dry_run: bool) -> list[PlannedPath]:
    planned = plan_export()
    if dry_run:
        return planned
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    for plan in planned:
        write_planned(plan, output_root)
    return planned


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/tmp/drake-export"),
        help="Output directory for export tree",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List planned copies without writing files",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=MANIFEST_PATH,
        help="Manifest markdown path (used for existence check)",
    )
    args = parser.parse_args(argv)

    if args.manifest != MANIFEST_PATH and not args.manifest.is_file():
        print(f"manifest not found: {args.manifest}", file=sys.stderr)
        return 2

    planned = export_tree(args.output.resolve(), dry_run=args.dry_run)
    verb = "would write" if args.dry_run else "wrote"
    for plan in sorted(planned, key=lambda p: str(p.destination)):
        kind = "generate" if plan.content is not None else "copy"
        print(f"{verb} ({kind}): {plan.destination}")
    print(f"drake export complete: {len(planned)} paths -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
