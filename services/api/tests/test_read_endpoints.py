from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from hosted_api.main import create_app
from hosted_api.sync.github import InMemorySyncCache, ProjectTree, SyncSnapshot

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))


def test_read_endpoints_return_example_portfolio_projection() -> None:
    client = TestClient(create_app())

    portfolio = client.get("/api/v1/portfolio")
    repos = client.get("/api/v1/repos")
    slices = client.get("/api/v1/repos/example-app/slices")
    runs = client.get("/api/v1/runs")
    dispatches = client.get("/api/v1/dispatches")

    assert portfolio.status_code == 200
    assert portfolio.json() == {
        "global_fanout_limit": 1,
        "same_repo_max_when_others_idle": 1,
        "repo_count": 1,
        "automation_enabled_count": 0,
        "ready_slice_count": 1,
        "running_slice_count": 0,
    }

    assert repos.status_code == 200
    assert repos.json()[0]["id"] == "example-app"
    assert repos.json()[0]["workers"][0]["credential_ref_names"] == ["GH_TOKEN"]
    assert repos.json()[0]["repo_native_paths"]["dependency_tree"] == (
        ".docs/examples/slice_dependency_tree.example.json"
    )

    assert slices.status_code == 200
    assert slices.json()[0]["slice_id"] == "SMOKE-1"
    assert slices.json()[0]["state"] == "ready"
    assert slices.json()[0]["operator_gates"] == []

    assert runs.status_code == 200
    assert runs.json()[0]["run_id"] == "2026-06-21T17-30-00Z-hosted-arch-1"
    assert runs.json()[0]["artifact_source"] == "local_automation_runs"

    assert dispatches.status_code == 200
    assert dispatches.json()[0]["dispatch_id"] == "dispatch-20260621-001"
    assert dispatches.json()[0]["webhook_url_env_name"].endswith("_WEBHOOK_URL")


def test_read_endpoints_return_404_for_unknown_resources() -> None:
    client = TestClient(create_app())

    assert client.get("/api/v1/repos/missing").status_code == 404
    assert client.get("/api/v1/repos/missing/slices").status_code == 404
    assert client.get("/api/v1/runs/missing").status_code == 404


def test_run_detail_returns_fixture_run() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/runs/2026-06-21T16-00-00Z-rs-slice")

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["pr_url"] == "https://github.com/sv-copilot/example-app/pull/42"


def test_hosted_api_sketch_example_validates_locally() -> None:
    from scripts.validate_hosted_api_sketch import (
        load_json,
        validate_hosted_api_sketch,
    )

    document = load_json(REPO_ROOT / ".docs/examples/hosted_api_sketch.example.json")
    schema = load_json(REPO_ROOT / ".docs/hosted_api_sketch.schema.json")

    assert validate_hosted_api_sketch(document, schema) == []


def test_read_projection_can_be_embedded_in_hosted_sketch_shape() -> None:
    from scripts.validate_hosted_api_sketch import (
        load_json,
        validate_with_schema,
    )

    client = TestClient(create_app())
    dashboard = {
        "portfolio": client.get("/api/v1/portfolio").json(),
        "repos": client.get("/api/v1/repos").json(),
        "slices": client.get("/api/v1/repos/example-app/slices").json(),
        "runs": client.get("/api/v1/runs").json(),
    }
    fixture = json.loads(
        (REPO_ROOT / ".docs/examples/hosted_api_sketch.example.json").read_text(
            encoding="utf-8",
        ),
    )
    fixture["views"]["dashboard"] = dashboard
    fixture["views"]["dispatch"]["webhook_dispatches"] = client.get(
        "/api/v1/dispatches",
    ).json()

    schema = load_json(REPO_ROOT / ".docs/hosted_api_sketch.schema.json")
    assert validate_with_schema(fixture, schema) == []


def test_read_endpoints_do_not_expose_webhook_values_or_private_prefixes() -> None:
    client = TestClient(create_app())

    payload = {
        "repos": client.get("/api/v1/repos").json(),
        "dispatches": client.get("/api/v1/dispatches").json(),
        "runs": client.get("/api/v1/runs").json(),
    }
    serialized = json.dumps(payload)

    assert "SIMON_PROJECTS" not in serialized
    assert "RESEARCH_SERVICE" not in serialized
    assert "https://hooks.slack.com" not in serialized
    assert "webhook.site" not in serialized
    assert "secret" not in serialized.lower()
    assert all(
        dispatch["webhook_url_env_name"].endswith("_WEBHOOK_URL")
        for dispatch in payload["dispatches"]
    )


def test_cache_backed_read_projection_counts_multiple_repos_and_missing_trees() -> None:
    app = create_app()
    app.state.sync_cache = InMemorySyncCache(
        snapshot=SyncSnapshot(
            synced_at=datetime.now(UTC),
            stale_after_seconds=300,
            registry={
                "orchestrator": {
                    "global_fanout_limit": 4,
                    "same_repo_max_when_others_idle": 2,
                },
                "projects": [
                    {
                        "id": "alpha",
                        "github_slug": "example-org/alpha",
                        "integration_branch": "ai-dev",
                        "automation_enabled": True,
                        "docs": {
                            "dependency_tree": ".docs/alpha-tree.json",
                        },
                        "workers": [
                            {
                                "worker_id": "alpha-worker",
                                "adapter_type": "cursor",
                                "role": "slice_pipeline",
                                "enabled": True,
                                "primary": True,
                                "credential_refs": ["GH_TOKEN"],
                                "webhook_env": {
                                    "url": "ALPHA_WEBHOOK_URL",
                                },
                            },
                        ],
                    },
                    {
                        "id": "beta",
                        "github_slug": "example-org/beta",
                        "integration_branch": "ai-dev",
                        "automation_enabled": False,
                        "docs": {
                            "dependency_tree": ".docs/beta-tree.json",
                        },
                        "workers": [],
                    },
                ],
            },
            dependency_trees={
                "alpha": ProjectTree(
                    project_id="alpha",
                    github_slug="example-org/alpha",
                    ref="ai-dev",
                    path=".docs/alpha-tree.json",
                    tree={
                        "slices": [
                            {
                                "slice_id": "READY-1",
                                "slice_number": 1,
                                "title": "Ready",
                                "state": "ready",
                                "automation_eligible": True,
                            },
                            {
                                "slice_id": "RUN-1",
                                "slice_number": 2,
                                "title": "Running",
                                "state": "running",
                                "automation_eligible": True,
                            },
                            {
                                "slice_id": "BLOCKED-1",
                                "slice_number": 3,
                                "title": "Blocked",
                                "state": "blocked",
                                "automation_eligible": False,
                            },
                            {
                                "slice_id": "DONE-1",
                                "slice_number": 4,
                                "title": "Promoted",
                                "state": "promoted",
                                "automation_eligible": False,
                            },
                        ],
                    },
                ),
            },
            files=[],
        ),
    )
    client = TestClient(app)

    portfolio = client.get("/api/v1/portfolio").json()
    repos = {repo["id"]: repo for repo in client.get("/api/v1/repos").json()}

    assert portfolio["repo_count"] == 2
    assert portfolio["automation_enabled_count"] == 1
    assert portfolio["ready_slice_count"] == 1
    assert portfolio["running_slice_count"] == 1
    assert repos["alpha"]["slice_summary"] == {
        "ready_count": 1,
        "running_count": 1,
        "blocked_count": 1,
        "validated_count": 1,
    }
    assert repos["beta"]["slice_summary"] == {
        "ready_count": 0,
        "running_count": 0,
        "blocked_count": 0,
        "validated_count": 0,
    }
    assert client.get("/api/v1/repos/beta/slices").json() == []
    assert client.get("/api/v1/repos/missing/slices").status_code == 404
    assert client.get("/api/v1/runs").json() == []
    assert client.get("/api/v1/dispatches").json() == []
    assert client.get("/api/v1/runs/2026-06-21T16-00-00Z-rs-slice").status_code == 404


def test_read_endpoints_reject_mutation_methods() -> None:
    client = TestClient(create_app())

    paths = [
        "/api/v1/portfolio",
        "/api/v1/repos",
        "/api/v1/repos/example-app",
        "/api/v1/repos/example-app/slices",
        "/api/v1/runs",
        "/api/v1/runs/2026-06-21T16-00-00Z-rs-slice",
        "/api/v1/dispatches",
    ]

    for path in paths:
        assert client.post(path).status_code in {405, 422}
        assert client.put(path).status_code == 405
        assert client.patch(path).status_code == 405
        assert client.delete(path).status_code == 405
