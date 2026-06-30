from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from hosted_api.main import create_app
from hosted_api.sync.github import (
    FetchedFile,
    GitHubSyncConfig,
    GitHubSyncService,
    InMemorySyncCache,
)

FIXTURE_ROOT = Path(__file__).resolve().parents[3] / ".docs/examples"
REGISTRY = json.loads(
    (FIXTURE_ROOT / "projects-registry.example.json").read_text(encoding="utf-8"),
)
DEPENDENCY_TREE = json.loads(
    (FIXTURE_ROOT / "slice_dependency_tree.example.json").read_text(encoding="utf-8"),
)


class FakeContentsFetcher:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    def fetch_file(self, repo: str, ref: str, path: str) -> FetchedFile:
        self.calls.append((repo, ref, path))

        if (repo, ref, path) == (
            "example-org/example-portfolio",
            "ai-dev",
            ".docs/projects-registry.json",
        ):
            return FetchedFile(
                repo=repo,
                ref=ref,
                path=path,
                content=json.dumps(REGISTRY),
                sha="registry-sha",
                source="fake",
            )

        if (repo, ref, path) == (
            "example-org/example-app",
            "ai-dev",
            ".docs/examples/slice_dependency_tree.example.json",
        ):
            return FetchedFile(
                repo=repo,
                ref=ref,
                path=path,
                content=json.dumps(DEPENDENCY_TREE),
                sha="tree-sha",
                source="fake",
            )

        raise AssertionError(f"unexpected fetch: {(repo, ref, path)}")


def test_github_sync_loads_registry_and_dependency_tree() -> None:
    fetcher = FakeContentsFetcher()
    cache = InMemorySyncCache()
    service = GitHubSyncService(fetcher=fetcher, cache=cache)

    snapshot = service.pull(
        GitHubSyncConfig(
            registry_repo="example-org/example-portfolio",
            registry_ref="ai-dev",
            stale_after_seconds=60,
        ),
    )

    assert snapshot.registry["schema_version"] == 2
    assert snapshot.dependency_trees["example-app"].tree["slices"][0]["slice_id"] == "SMOKE-1"
    assert cache.status()["status"] == "ok"
    assert cache.status()["project_count"] == 1
    assert cache.status()["dependency_tree_count"] == 1
    assert cache.status()["last_synced_at"] is not None
    assert fetcher.calls == [
        (
            "example-org/example-portfolio",
            "ai-dev",
            ".docs/projects-registry.json",
        ),
        (
            "example-org/example-app",
            "ai-dev",
            ".docs/examples/slice_dependency_tree.example.json",
        ),
    ]


def test_sync_status_empty_before_first_pull() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.get("/api/v1/sync/status")

    assert response.status_code == 200
    assert response.json() == {
        "status": "empty",
        "last_synced_at": None,
        "stale_after_seconds": 300,
        "is_stale": True,
        "project_count": 0,
        "dependency_tree_count": 0,
        "files": [],
    }


def test_sync_endpoint_uses_mocked_fetcher() -> None:
    fetcher = FakeContentsFetcher()
    cache = InMemorySyncCache()
    app = create_app()
    app.state.github_sync_service = GitHubSyncService(fetcher=fetcher, cache=cache)
    client = TestClient(app)

    response = client.post(
        "/api/v1/sync",
        json={
            "registry_repo": "example-org/example-portfolio",
            "registry_ref": "ai-dev",
            "stale_after_seconds": 60,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["project_count"] == 1
    assert payload["dependency_tree_count"] == 1
    assert payload["is_stale"] is False
    assert payload["files"] == [
        {
            "repo": "example-org/example-portfolio",
            "ref": "ai-dev",
            "path": ".docs/projects-registry.json",
            "sha": "registry-sha",
            "source": "fake",
        },
        {
            "repo": "example-org/example-app",
            "ref": "ai-dev",
            "path": ".docs/examples/slice_dependency_tree.example.json",
            "sha": "tree-sha",
            "source": "fake",
        },
    ]
