#!/usr/bin/env python3
"""Validate a Drake public export tree against scrub gates."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SECRET_PATTERNS = [
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"gho_[A-Za-z0-9]{20,}"),
    re.compile(r"ghs_[A-Za-z0-9]{20,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._-]{20,}"),
]

MAC_PATH_PATTERN = re.compile("/" + "Users" + "/simon")

PRIVATE_MARKER_PATTERNS = [
    re.compile(r"\bsimon-projects\b"),
]

PRIVATE_DOC_NAMES = {
    "product_strategy.md",
    "product_strategy_refinement.md",
    "projects-registry.json",
    "naming_decision.md",
    "drake_public_launch_policy.md",
    "drake_public_export_manifest.md",
}

SCRUB_TOOL_PATHS = {
    "scripts/export_drake_public.py",
    "scripts/validate_drake_export.py",
}

TEXT_SUFFIXES = {
    ".md",
    ".mdc",
    ".py",
    ".sh",
    ".json",
    ".yml",
    ".yaml",
    ".txt",
    ".toml",
    ".example",
    ".gitignore",
}


def iter_text_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if ".cursor/automation-runs" in rel:
            files.append(path)
            continue
        if path.suffix in TEXT_SUFFIXES or path.name in {"hooks.json", ".gitignore"}:
            files.append(path)
    return files


def validate_tree(root: Path) -> list[str]:
    errors: list[str] = []

    for rel_name in PRIVATE_DOC_NAMES:
        matches = list(root.rglob(rel_name))
        if matches:
            errors.append(f"forbidden private artifact present: {matches[0].relative_to(root)}")

    automation_runs = list(root.glob(".cursor/automation-runs/**"))
    if automation_runs:
        errors.append("forbidden path present: .cursor/automation-runs/")

    for path in iter_text_files(root):
        rel = path.relative_to(root).as_posix()
        if rel in SCRUB_TOOL_PATHS:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                errors.append(f"secret-like pattern in {rel}")

        if MAC_PATH_PATTERN.search(text):
            errors.append(f"operator mac path in {rel}")

        for pattern in PRIVATE_MARKER_PATTERNS:
            if pattern.search(text):
                errors.append(f"private control-plane marker in {rel}")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tree",
        type=Path,
        required=True,
        help="Export tree root to validate",
    )
    args = parser.parse_args(argv)

    root = args.tree.resolve()
    if not root.is_dir():
        print(f"export tree not found: {root}", file=sys.stderr)
        return 2

    errors = validate_tree(root)
    if errors:
        print("drake export validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"drake export validation passed: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
