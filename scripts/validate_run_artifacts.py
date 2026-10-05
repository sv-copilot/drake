#!/usr/bin/env python3
"""Validate a Drake run directory against the published contracts.

Usage:
  python3 scripts/validate_run_artifacts.py --run .drake/runs/<run-label>
  python3 scripts/validate_run_artifacts.py \
      --run tests/fixtures/automation-runs/stub-harness-run

Every harness run leaves a task packet and an evidence record behind. Those two
documents are what the rest of the pipeline reads, so they have schemas; this
script checks a run against them.

The schemas carry absolute https $ids and reference each other by relative path,
so a plain validator tries to fetch them over the network and fails. This script
registers the local copies, so validation works offline and cannot silently skip a
broken reference.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ADAPTER_DIR = REPO_ROOT / "adapters"

ARTIFACTS = (
    ("task-packet.json", "task-packet.schema.json", "task packet"),
    ("evidence.json", "evidence-contract.schema.json", "evidence"),
)


def build_registry():
    """Register every local schema under its file name, its $id, and the raw URL."""
    from referencing import Registry, Resource

    resources = []
    for path in sorted(ADAPTER_DIR.glob("*.schema.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        resource = Resource.from_contents(schema)
        resources.append((path.name, resource))
        schema_id = schema.get("$id")
        if schema_id:
            resources.append((schema_id, resource))
            resources.append(
                (
                    schema_id.replace(
                        "https://github.com/", "https://raw.githubusercontent.com/"
                    ),
                    resource,
                )
            )
    return Registry().with_resources(resources)


def validate(run_dir: Path) -> list[str]:
    """Return a list of problems; empty means the run satisfies its contracts."""
    try:
        from jsonschema import Draft7Validator
    except ImportError:  # pragma: no cover - dependency is declared in CI
        return ["jsonschema is not installed: pip install jsonschema"]

    registry = build_registry()
    problems: list[str] = []

    for filename, schema_name, label in ARTIFACTS:
        artifact = run_dir / filename
        if not artifact.is_file():
            problems.append(f"{label}: missing {artifact}")
            continue

        schema = json.loads((ADAPTER_DIR / schema_name).read_text(encoding="utf-8"))
        validator = Draft7Validator(schema, registry=registry)
        try:
            document = json.loads(artifact.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            problems.append(f"{label}: {filename} is not valid JSON: {exc}")
            continue

        for error in sorted(
            validator.iter_errors(document), key=lambda item: list(item.path)
        ):
            location = "/".join(str(part) for part in error.path) or "(root)"
            problems.append(f"{label}: {location}: {error.message}")

    return problems


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, help="Run directory to validate.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_dir = Path(args.run).expanduser().resolve()

    if not run_dir.is_dir():
        print(f"run directory not found: {run_dir}", file=sys.stderr)
        return 2

    problems = validate(run_dir)
    if problems:
        print(f"run artifacts invalid: {run_dir}")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print(f"run artifacts valid: {run_dir}")
    print("  task-packet.json  -> task-packet.schema.json")
    print("  evidence.json     -> evidence-contract.schema.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
