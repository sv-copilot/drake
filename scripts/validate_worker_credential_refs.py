#!/usr/bin/env python3
"""Validate worker credential_refs declarations in the projects registry."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from projects_registry import resolve_worker_credential_refs

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = REPO_ROOT / ".docs" / "projects-registry.json"

CREDENTIAL_NAME_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]+$")
WEBHOOK_ENV_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]+_WEBHOOK_(URL|TOKEN)$")


def validate_registry_credentials(registry: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for project in registry.get("projects", []):
        project_id = project.get("id", "unknown")
        automation_enabled = project.get("automation_enabled") is True
        for worker in project.get("workers") or []:
            worker_id = worker.get("worker_id", "unknown")
            prefix = f"project {project_id} worker {worker_id}"
            if worker.get("enabled") is False:
                continue

            declared = worker.get("credential_refs")
            if not isinstance(declared, list) or not declared:
                if automation_enabled:
                    errors.append(f"{prefix}: credential_refs must be a non-empty array")
                continue

            if len(declared) != len(set(declared)):
                errors.append(f"{prefix}: credential_refs contains duplicates")

            for ref in declared:
                if not isinstance(ref, str) or not CREDENTIAL_NAME_PATTERN.match(ref):
                    errors.append(f"{prefix}: invalid credential_refs entry {ref!r}")

            webhook_env = worker.get("webhook_env") or {}
            webhook_names = {
                value
                for value in (webhook_env.get("url"), webhook_env.get("token"))
                if isinstance(value, str)
            }
            overlap = webhook_names.intersection(declared)
            if overlap:
                errors.append(
                    f"{prefix}: credential_refs must not include orchestrator dispatch "
                    f"webhook_env names: {sorted(overlap)}"
                )

            role = worker.get("role")
            if role == "slice_pipeline" and "GH_TOKEN" not in declared:
                errors.append(f"{prefix}: slice_pipeline credential_refs must include GH_TOKEN")

            resolved = resolve_worker_credential_refs(worker)
            if sorted(resolved) != sorted(set(resolved)):
                errors.append(f"{prefix}: resolved credential_refs are not unique")

            for ref in declared:
                if WEBHOOK_ENV_PATTERN.match(ref) and ref not in {
                    "PORTFOLIO_PLAN_ORCHESTRATOR_WEBHOOK_URL",
                    "PORTFOLIO_PLAN_ORCHESTRATOR_WEBHOOK_TOKEN",
                    "PLAN_NEXT_SLICE_WEBHOOK_URL",
                    "PLAN_NEXT_SLICE_WEBHOOK_TOKEN",
                    "SLICE_PIPELINE_WEBHOOK_URL",
                    "SLICE_PIPELINE_WEBHOOK_TOKEN",
                }:
                    if ref.endswith("_WEBHOOK_URL") or ref.endswith("_WEBHOOK_TOKEN"):
                        project_prefix = project_id.upper().replace("-", "_")
                        if ref.startswith(f"{project_prefix}_"):
                            errors.append(
                                f"{prefix}: project-scoped webhook env {ref!r} belongs in "
                                "webhook_env (orchestrator scope), not credential_refs"
                            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--registry",
        type=Path,
        default=DEFAULT_REGISTRY,
        help="Path to projects registry JSON",
    )
    args = parser.parse_args()
    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    errors = validate_registry_credentials(registry)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("worker credential_refs validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
