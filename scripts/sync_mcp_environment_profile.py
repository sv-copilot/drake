#!/usr/bin/env python3
"""Install or check MCP environment profile scaffold assets for product repos.

Conservative defaults mirror sync_slice_pipeline_local.py:
- check mode reports missing or stale assets without writing;
- install mode creates missing files and copies canonical tooling from this repo;
- existing non-empty project files are not overwritten unless --overwrite-existing.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from mcp_environment_profile import generate_placeholder_profile


REPO_ROOT = Path(__file__).resolve().parents[1]

MANAGED_FILE_SOURCES = {
    ".docs/mcp_environment_profile.schema.json": REPO_ROOT
    / ".docs/mcp_environment_profile.schema.json",
    ".docs/mcp_environment_profiles.md": REPO_ROOT / ".docs/mcp_environment_profiles.md",
    "scripts/mcp_environment_profile.py": REPO_ROOT / "scripts/mcp_environment_profile.py",
    "scripts/validate_mcp_environment_profile.py": REPO_ROOT
    / "scripts/validate_mcp_environment_profile.py",
    "tests/test_validate_mcp_environment_profile.py": REPO_ROOT
    / "tests/test_validate_mcp_environment_profile.py",
}

PLACEHOLDER_PROFILE_PATHS = (
    ".docs/mcp_environment_profile.json",
    "tests/fixtures/mcp_environment_profile.valid.json",
)


@dataclass(frozen=True)
class WriteResult:
    path: str
    status: str
    detail: str


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "project"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install or check MCP environment profile scaffold assets."
    )
    parser.add_argument("--target", required=True, help="Target repository path.")
    parser.add_argument(
        "--mode",
        choices=("check", "install"),
        default="check",
        help="check reports drift; install creates missing assets.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned writes without changing the target repository.",
    )
    parser.add_argument(
        "--overwrite-existing",
        action="store_true",
        help="Replace stale existing managed files. Use only after reviewing diffs.",
    )
    parser.add_argument("--project-name", help="Human-readable project name.")
    parser.add_argument("--project-id", help="Kebab-case project id.")
    return parser.parse_args()


def write_text_if_needed(
    target: Path,
    rel_path: str,
    content: str,
    *,
    mode: str,
    dry_run: bool,
    overwrite_existing: bool,
) -> WriteResult:
    dest = target / rel_path
    if dest.exists():
        current = dest.read_text(encoding="utf-8")
        if current == content:
            return WriteResult(rel_path, "ok", "already current")
        if mode == "check":
            return WriteResult(rel_path, "stale", "content differs")
        if current.strip() and not overwrite_existing:
            return WriteResult(
                rel_path,
                "skipped",
                "exists and differs; use --overwrite-existing after review",
            )
        if dry_run:
            return WriteResult(rel_path, "would_update", "content differs")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        return WriteResult(rel_path, "updated", "content replaced")

    if mode == "check":
        return WriteResult(rel_path, "missing", "file is absent")
    if dry_run:
        return WriteResult(rel_path, "would_create", "file is absent")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    return WriteResult(rel_path, "created", "file installed")


def sync_managed_files(
    target: Path,
    *,
    mode: str,
    dry_run: bool,
    overwrite_existing: bool,
) -> list[WriteResult]:
    results: list[WriteResult] = []
    for rel_path, source in MANAGED_FILE_SOURCES.items():
        if not source.is_file():
            raise SystemExit(f"canonical source missing: {source}")
        content = source.read_text(encoding="utf-8")
        results.append(
            write_text_if_needed(
                target,
                rel_path,
                content,
                mode=mode,
                dry_run=dry_run,
                overwrite_existing=overwrite_existing,
            )
        )
    return results


def sync_placeholder_profiles(
    target: Path,
    project_id: str,
    project_name: str,
    *,
    mode: str,
    dry_run: bool,
    overwrite_existing: bool,
) -> list[WriteResult]:
    profile = generate_placeholder_profile(
        project_id,
        description=(
            f"Placeholder MCP environment profile for {project_name}. "
            "Replace disabled servers before enabling automation."
        ),
    )
    content = json.dumps(profile, indent=2) + "\n"
    results: list[WriteResult] = []
    for rel_path in PLACEHOLDER_PROFILE_PATHS:
        results.append(
            write_text_if_needed(
                target,
                rel_path,
                content,
                mode=mode,
                dry_run=dry_run,
                overwrite_existing=overwrite_existing,
            )
        )
    return results


def sync_mcp_environment_profile_scaffold(
    target: Path,
    *,
    mode: str = "check",
    dry_run: bool = False,
    overwrite_existing: bool = False,
    project_name: str | None = None,
    project_id: str | None = None,
) -> list[WriteResult]:
    resolved_name = project_name or target.name
    resolved_id = project_id or slugify(resolved_name)
    results = sync_managed_files(
        target,
        mode=mode,
        dry_run=dry_run,
        overwrite_existing=overwrite_existing,
    )
    results.extend(
        sync_placeholder_profiles(
            target,
            resolved_id,
            resolved_name,
            mode=mode,
            dry_run=dry_run,
            overwrite_existing=overwrite_existing,
        )
    )
    return results


def print_results(results: list[WriteResult]) -> None:
    for result in results:
        print(f"{result.status:13} {result.path} - {result.detail}")


def exit_code_for_results(mode: str, results: list[WriteResult]) -> int:
    blocking = {"missing", "stale", "skipped"}
    if mode == "check" and any(result.status in blocking for result in results):
        return 1
    if mode == "install" and any(result.status == "skipped" for result in results):
        return 2
    return 0


def main() -> int:
    args = parse_args()
    target = Path(args.target).expanduser().resolve()

    if args.mode == "check" and not target.exists():
        raise SystemExit(f"target path does not exist: {target}")
    if args.mode == "install" and not args.dry_run:
        target.mkdir(parents=True, exist_ok=True)

    project_name = args.project_name or target.name
    project_id = args.project_id or slugify(project_name)
    results = sync_mcp_environment_profile_scaffold(
        target,
        mode=args.mode,
        dry_run=args.dry_run,
        overwrite_existing=args.overwrite_existing,
        project_name=project_name,
        project_id=project_id,
    )
    print_results(results)
    return exit_code_for_results(args.mode, results)


if __name__ == "__main__":
    sys.exit(main())
