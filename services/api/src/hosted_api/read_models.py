from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from hosted_api.sync.github import (
    ProjectTree,
    SyncSnapshot,
    SyncedFile,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
EXAMPLE_REGISTRY = REPO_ROOT / ".docs/examples/projects-registry.example.json"
EXAMPLE_TREE = REPO_ROOT / ".docs/examples/slice_dependency_tree.example.json"
EXAMPLE_HOSTED_API = REPO_ROOT / ".docs/examples/hosted_api_sketch.example.json"


@dataclass(frozen=True)
class DashboardProjection:
    portfolio: dict[str, Any]
    repos: list[dict[str, Any]]
    slices: list[dict[str, Any]]
    runs: list[dict[str, Any]]
    dispatches: list[dict[str, Any]]


def snapshot_from_examples() -> SyncSnapshot:
    registry = _load_json(EXAMPLE_REGISTRY)
    tree = _load_json(EXAMPLE_TREE)
    project = registry["projects"][0]
    project_id = project["id"]
    tree_path = project.get("docs", {}).get("dependency_tree") or str(
        EXAMPLE_TREE.relative_to(REPO_ROOT),
    )
    return SyncSnapshot(
        synced_at=datetime.now(UTC),
        stale_after_seconds=300,
        registry=registry,
        dependency_trees={
            project_id: ProjectTree(
                project_id=project_id,
                github_slug=project["github_slug"],
                ref=project.get("integration_branch", "ai-dev"),
                path=tree_path,
                tree=tree,
            ),
        },
        files=[
            SyncedFile(
                repo="example-org/example-portfolio",
                ref="ai-dev",
                path=".docs/projects-registry.json",
                sha=None,
                source="example_fixture",
            ),
            SyncedFile(
                repo=project["github_slug"],
                ref=project.get("integration_branch", "ai-dev"),
                path=tree_path,
                sha=None,
                source="example_fixture",
            ),
        ],
    )


def build_dashboard(
    snapshot: SyncSnapshot,
    *,
    include_example_runtime: bool = False,
) -> DashboardProjection:
    registry = snapshot.registry
    projects = registry.get("projects", [])
    slices = _slice_rows(snapshot)
    repos = [_repo_row(project, snapshot) for project in projects]
    portfolio = _portfolio_summary(registry, repos, slices)
    return DashboardProjection(
        portfolio=portfolio,
        repos=repos,
        slices=slices,
        runs=runs_from_examples() if include_example_runtime else [],
        dispatches=dispatches_from_examples() if include_example_runtime else [],
    )


def dispatches_from_examples() -> list[dict[str, Any]]:
    document = _load_json(EXAMPLE_HOSTED_API)
    dispatches = document.get("views", {}).get("dispatch", {}).get(
        "webhook_dispatches",
        [],
    )
    return [_sanitize_dispatch(dispatch) for dispatch in dispatches]


def runs_from_examples() -> list[dict[str, Any]]:
    document = _load_json(EXAMPLE_HOSTED_API)
    return document.get("views", {}).get("dashboard", {}).get("runs", [])


def _sanitize_dispatch(dispatch: dict[str, Any]) -> dict[str, Any]:
    sanitized = dict(dispatch)
    env_name = sanitized.get("webhook_url_env_name")
    if isinstance(env_name, str):
        sanitized["webhook_url_env_name"] = (
            env_name.replace("SIMON_PROJECTS", "EXAMPLE_PORTFOLIO")
            .replace("RESEARCH_SERVICE", "EXAMPLE_APP")
        )
    return sanitized


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _portfolio_summary(
    registry: dict[str, Any],
    repos: list[dict[str, Any]],
    slices: list[dict[str, Any]],
) -> dict[str, Any]:
    orchestrator = registry.get("orchestrator") or {}
    return {
        "global_fanout_limit": int(orchestrator.get("global_fanout_limit") or 1),
        "same_repo_max_when_others_idle": int(
            orchestrator.get("same_repo_max_when_others_idle") or 1,
        ),
        "repo_count": len(repos),
        "automation_enabled_count": sum(
            1 for repo in repos if repo.get("automation_enabled") is True
        ),
        "ready_slice_count": sum(1 for item in slices if item.get("state") == "ready"),
        "running_slice_count": sum(
            1 for item in slices if item.get("state") == "running"
        ),
    }


def _repo_row(project: dict[str, Any], snapshot: SyncSnapshot) -> dict[str, Any]:
    project_id = project["id"]
    docs = project.get("docs") or {}
    slice_summary = _slice_summary(
        snapshot.dependency_trees.get(project_id).tree
        if project_id in snapshot.dependency_trees
        else {},
    )
    return {
        "id": project_id,
        "github_slug": project["github_slug"],
        "integration_branch": project.get("integration_branch", "ai-dev"),
        "automation_enabled": bool(project.get("automation_enabled", False)),
        "priority": project.get("priority"),
        "readiness": project.get("readiness") or {},
        "repo_native_paths": {
            "registry_project_id": project_id,
            "slice_backlog": docs.get("slice_backlog", ".docs/slice_backlog.md"),
            "dependency_tree": docs.get("dependency_tree", ".docs/slice_dependency_tree.json"),
            "agent_automations": docs.get(
                "agent_automations",
                ".docs/agent_automations.md",
            ),
        },
        "workers": [_worker_row(worker) for worker in project.get("workers", [])],
        "slice_summary": slice_summary,
    }


def _worker_row(worker: dict[str, Any]) -> dict[str, Any]:
    return {
        "worker_id": worker["worker_id"],
        "adapter_type": worker["adapter_type"],
        "role": worker["role"],
        "enabled": bool(worker.get("enabled", False)),
        "primary": bool(worker.get("primary", False)),
        "model_slug": worker.get("model_slug"),
        "credential_ref_names": worker.get("credential_refs", []),
        "webhook_env_names": worker.get("webhook_env", {}),
    }


def _slice_rows(snapshot: SyncSnapshot) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for project in snapshot.registry.get("projects", []):
        project_id = project["id"]
        project_tree = snapshot.dependency_trees.get(project_id)
        if project_tree is None:
            continue
        for item in project_tree.tree.get("slices", []):
            rows.append(
                {
                    "slice_id": item["slice_id"],
                    "slice_number": item["slice_number"],
                    "title": item["title"],
                    "state": item.get("state", "ready"),
                    "repo_id": project_id,
                    "github_slug": project["github_slug"],
                    "automation_eligible": bool(item.get("automation_eligible", False)),
                    "operator_gates": item.get("operator_gates", []),
                    "dependencies": item.get("dependencies", []),
                    "repo_native_path": item.get("repo_native_path")
                    or project_tree.path,
                },
            )
    return rows


def _slice_summary(tree: dict[str, Any]) -> dict[str, int]:
    slices = tree.get("slices", [])
    return {
        "ready_count": sum(1 for item in slices if item.get("state") == "ready"),
        "running_count": sum(1 for item in slices if item.get("state") == "running"),
        "blocked_count": sum(1 for item in slices if item.get("state") == "blocked"),
        "validated_count": sum(
            1
            for item in slices
            if item.get("state") in {"validated", "promoted", "released"}
        ),
    }
