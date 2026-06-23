#!/usr/bin/env python3
"""Validate or produce normalized validation_results payloads."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from validation_results import (
    default_repo_validation_commands,
    run_validation_commands,
    validate_validation_results,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--file",
        type=Path,
        help="Validate an existing validation_results JSON file.",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Run repo validation commands and validate the produced payload.",
    )
    parser.add_argument(
        "--runtime",
        default="local-cli",
        help="Runtime label stored on generated payloads (default: local-cli).",
    )
    parser.add_argument(
        "--source",
        default="validate_validation_results",
        help="Source label stored on generated payloads.",
    )
    parser.add_argument(
        "--write",
        type=Path,
        help="When used with --run, write the generated payload to this path.",
    )
    args = parser.parse_args(argv)

    if args.file and args.run:
        print("Choose either --file or --run, not both.", file=sys.stderr)
        return 2

    if args.file:
        payload = json.loads(args.file.read_text(encoding="utf-8"))
        errors = validate_validation_results(payload, REPO_ROOT)
        if errors:
            print("validation_results validation failed:", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            return 1
        print(f"validation_results valid: {args.file}")
        return 0

    if args.run:
        commands = default_repo_validation_commands(REPO_ROOT)
        if not commands:
            print("no validation commands configured for this repo", file=sys.stderr)
            return 1
        payload = run_validation_commands(
            commands,
            cwd=REPO_ROOT,
            runtime=args.runtime,
            source=args.source,
        )
        errors = validate_validation_results(payload, REPO_ROOT)
        if errors:
            print("generated validation_results failed schema validation:", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            return 1
        if args.write:
            args.write.parent.mkdir(parents=True, exist_ok=True)
            args.write.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(payload, indent=2))
        return 0 if payload.get("overall") == "passed" else 1

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
