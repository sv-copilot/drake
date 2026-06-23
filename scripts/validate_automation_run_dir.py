#!/usr/bin/env python3
"""Validate automation run history artifacts under .cursor/automation-runs/<run-id>/.

Usage:
  python3 scripts/validate_automation_run_dir.py --run .cursor/automation-runs/<run-id>
  python3 scripts/validate_automation_run_dir.py --run tests/fixtures/automation-runs/sample-run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from automation_run_history import (
    OPTIONAL_RUN_FILES,
    REQUIRED_RUN_FILES,
    load_json,
    missing_required_files,
    normalize_run_id,
    parse_events_jsonl,
)


def load_schema(repo_root: Path) -> dict:
    schema_path = repo_root / ".docs" / "run_history_artifact.schema.json"
    return load_json(schema_path)


def validate_json_with_schema(payload: dict, schema: dict, label: str) -> list[str]:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        import subprocess

        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet", "jsonschema"]
        )
        from jsonschema import Draft202012Validator

    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda err: list(err.path))
    return [
        f"{label}: {err.message} ({'.'.join(str(part) for part in err.path)})"
        for err in errors
    ]


def validate_run_dir(run_dir: Path, repo_root: Path) -> list[str]:
    errors: list[str] = []

    if not run_dir.is_dir():
        return [f"run directory not found: {run_dir}"]

    try:
        normalize_run_id(run_dir.name)
    except ValueError as exc:
        errors.append(f"semantic: {exc}")

    missing = missing_required_files(run_dir)
    if missing:
        errors.append(f"semantic: missing required files: {', '.join(missing)}")

    schema_doc = load_schema(repo_root)
    defs = schema_doc.get("$defs", {})

    metadata_path = run_dir / "metadata.json"
    if metadata_path.is_file():
        metadata = load_json(metadata_path)
        errors.extend(
            validate_json_with_schema(metadata, defs["metadata"], "metadata.json")
        )

    events_path = run_dir / "events.jsonl"
    if events_path.is_file():
        try:
            events = parse_events_jsonl(events_path)
        except ValueError as exc:
            errors.append(f"semantic: {exc}")
            events = []
        for index, event in enumerate(events, start=1):
            errors.extend(
                validate_json_with_schema(
                    event,
                    defs["event_record"],
                    f"events.jsonl line {index}",
                )
            )

    handoff_path = run_dir / "handoff.json"
    if handoff_path.is_file():
        handoff = load_json(handoff_path)
        errors.extend(
            validate_json_with_schema(handoff, defs["handoff"], "handoff.json")
        )

    payload_path = run_dir / "payload.json"
    if payload_path.is_file():
        try:
            load_json(payload_path)
        except json.JSONDecodeError as exc:
            errors.append(f"semantic: payload.json is not valid JSON: {exc}")

    prompt_path = run_dir / "prompt.txt"
    if prompt_path.is_file() and not prompt_path.read_text(encoding="utf-8").strip():
        errors.append("semantic: prompt.txt must not be empty")

    allowed = set(REQUIRED_RUN_FILES) | set(OPTIONAL_RUN_FILES)
    for child in run_dir.iterdir():
        if child.is_file() and child.name not in allowed:
            errors.append(f"semantic: unexpected file in run directory: {child.name}")

    return errors


def main(argv: list[str] | None = None) -> int:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run",
        type=Path,
        required=True,
        help="Path to a run directory under .cursor/automation-runs/",
    )
    args = parser.parse_args(argv)

    errors = validate_run_dir(args.run.resolve(), repo_root)
    if errors:
        print("automation run directory validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"automation run directory valid: {args.run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
