from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from hosted_api.sync.github import (
    DEFAULT_REGISTRY_PATH,
    DEFAULT_STALE_AFTER_SECONDS,
    GitHubSyncConfig,
    GitHubSyncError,
    GitHubSyncService,
    InMemorySyncCache,
    SyncSnapshot,
)

router = APIRouter(prefix="/api/v1/sync", tags=["sync"])


class SyncRequest(BaseModel):
    registry_repo: str = Field(
        ...,
        description="GitHub slug containing the portfolio registry.",
        examples=["example-org/example-portfolio"],
    )
    registry_ref: str = Field(
        default="ai-dev",
        description="Branch, tag, or SHA to read.",
    )
    registry_path: str = Field(
        default=DEFAULT_REGISTRY_PATH,
        description="Repo-relative path to projects-registry.json.",
    )
    stale_after_seconds: int = Field(
        default=DEFAULT_STALE_AFTER_SECONDS,
        ge=1,
        description="Age after which the cache status reports stale.",
    )

    def to_config(self) -> GitHubSyncConfig:
        return GitHubSyncConfig(
            registry_repo=self.registry_repo,
            registry_ref=self.registry_ref,
            registry_path=self.registry_path,
            stale_after_seconds=self.stale_after_seconds,
        )


class SyncedFileResponse(BaseModel):
    repo: str
    ref: str
    path: str
    sha: str | None
    source: str


class SyncStatusResponse(BaseModel):
    status: str
    last_synced_at: str | None
    stale_after_seconds: int
    is_stale: bool
    project_count: int
    dependency_tree_count: int
    files: list[SyncedFileResponse] = []


@router.post("", response_model=SyncStatusResponse)
def pull_sync(payload: SyncRequest, request: Request) -> SyncStatusResponse:
    service = _sync_service(request)
    try:
        snapshot = service.pull(payload.to_config())
    except GitHubSyncError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return _status_response(service.cache, snapshot)


@router.get("/status", response_model=SyncStatusResponse)
def sync_status(request: Request) -> SyncStatusResponse:
    service = _sync_service(request)
    return _status_response(service.cache)


def _sync_service(request: Request) -> GitHubSyncService:
    service = getattr(request.app.state, "github_sync_service", None)
    if isinstance(service, GitHubSyncService):
        return service

    cache = getattr(request.app.state, "sync_cache", None)
    if not isinstance(cache, InMemorySyncCache):
        cache = InMemorySyncCache()
        request.app.state.sync_cache = cache

    service = GitHubSyncService(cache=cache)
    request.app.state.github_sync_service = service
    return service


def _status_response(
    cache: InMemorySyncCache,
    snapshot: SyncSnapshot | None = None,
) -> SyncStatusResponse:
    status: dict[str, Any] = cache.status()
    active_snapshot = snapshot or cache.snapshot
    files = []
    if active_snapshot is not None:
        files = [
            SyncedFileResponse(
                repo=file.repo,
                ref=file.ref,
                path=file.path,
                sha=file.sha,
                source=file.source,
            )
            for file in active_snapshot.files
        ]

    return SyncStatusResponse(**status, files=files)
