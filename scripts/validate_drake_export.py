#!/usr/bin/env python3
"""Validate a Drake public export tree against the scrub gates.

This gate is the last line of defence before private control-plane material
becomes public, so it runs in CI on every change to the integration branches
(via ``scripts/ci_preflight.sh``) and must FAIL LOUDLY rather than warn.

A note on the marker literals below: a scrub gate has to contain the tokens it
scrubs. ``PRIVATE_MARKER_PATTERNS`` is the minimum set needed to catch a leak of
the private control-plane workspace, its repository URLs, its hostnames, and its
private product slugs. None of them is a credential, and this module is exempt
from its own scan (``SCRUB_TOOL_PATHS``) so the gate cannot flag its own rules.

Files are scanned as text; binary files and undecodable encodings are skipped.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SECRET_PATTERNS = [
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"gho_[A-Za-z0-9]{20,}"),
    re.compile(r"ghs_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"Bearer\s+[A-Za-z0-9._-]{20,}"),
    re.compile(r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}"),
]

# Absolute personal home directories. An adopter's own path is a portability
# bug and the maintainer's is a private disclosure, so both are gated.
HOME_PATH_PATTERNS = [
    re.compile(r"/(?:Users|home)/[A-Za-z0-9._-]+/"),
]

# Private control-plane workspace, repository URLs, hostnames, product slugs.
# Separators are normalised because these leak both as dash slugs and as
# screaming-snake env var names (`foo-bar` / `FOO_BAR`), and there is
# deliberately no trailing word boundary so a match cannot be defeated by a
# following underscore.
PRIVATE_MARKER_PATTERNS = [
    re.compile(r"\bsimon[-_]projects", re.IGNORECASE),
    re.compile(r"\bdrake[-_]governance", re.IGNORECASE),
    re.compile(r"github\.com/\s*sv-copilot/simon[-_]projects", re.IGNORECASE),
    re.compile(r"github\.com/\s*sv-copilot/drake[-_]governance", re.IGNORECASE),
    re.compile(r"\bspencervaradi(?:[-_]site)?", re.IGNORECASE),
    re.compile(r"\bjobhunter", re.IGNORECASE),
    re.compile(r"\bresearch[-_]service", re.IGNORECASE),
    re.compile(r"\bone[-_]star", re.IGNORECASE),
]

# Private planning artifacts that must never reach an export tree.
PRIVATE_DOC_NAMES = {
    "product_strategy.md",
    "product_strategy_refinement.md",
    "projects-registry.json",
    "naming_decision.md",
    "drake_public_launch_policy.md",
    "drake_public_export_manifest.md",
}

# The scrub tooling carries the marker literals by design; exempting the tools
# is what keeps the gate functional. Add a path here ONLY for a file that must
# name a marker in order to scrub it.
SCRUB_TOOL_PATHS = {
    "scripts/export_drake_public.py",
    "scripts/validate_drake_export.py",
    # The hosted read-model API sanitises legacy private env-var names out of
    # everything it serves, and its test asserts they never appear in output.
    # Scrubber code has to name what it scrubs.
    "services/api/src/hosted_api/read_models.py",
    "services/api/tests/test_read_endpoints.py",
}

FORBIDDEN_PATH_PREFIXES = {
    ".cursor/automation-runs/",
    ".drake/runs/",
}

SKIPPED_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    ".next",
    "__pycache__",
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
    ".cfg",
    ".ini",
}


def iter_text_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if any(part in SKIPPED_DIRS for part in rel.split("/")):
            continue
        if rel.startswith(tuple(FORBIDDEN_PATH_PREFIXES)):
            files.append(path)
            continue
        if path.suffix in TEXT_SUFFIXES or path.name in {"hooks.json", ".gitignore"}:
            files.append(path)
    return files


def validate_tree(root: Path) -> list[str]:
    """Return every scrub violation found in ``root`` (empty list = clean)."""
    errors: list[str] = []

    for rel_name in PRIVATE_DOC_NAMES:
        matches = list(root.rglob(rel_name))
        if matches:
            errors.append(
                f"forbidden private artifact present: {matches[0].relative_to(root)}"
            )

    for prefix in FORBIDDEN_PATH_PREFIXES:
        if list(root.glob(f"{prefix}**")):
            errors.append(f"forbidden path present: {prefix}")

    for path in iter_text_files(root):
        rel = path.relative_to(root).as_posix()
        if rel in SCRUB_TOOL_PATHS:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        if any(pattern.search(text) for pattern in SECRET_PATTERNS):
            errors.append(f"secret-like pattern in {rel}")

        if any(pattern.search(text) for pattern in HOME_PATH_PATTERNS):
            errors.append(f"operator home path in {rel}")

        if any(pattern.search(text) for pattern in PRIVATE_MARKER_PATTERNS):
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
