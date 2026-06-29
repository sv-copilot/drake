from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from hosted_api.read_models import (
    DashboardProjection,
    build_dashboard,
    dispatches_from_examples,
    runs_from_examples,
    snapshot_from_examples,
)
from hosted_api.sync.github import GitHubSyncService, InMemorySyncCache, SyncSnapshot

router = APIRouter(prefix="/api/v1", tags=["read"])


class PortfolioResponse(BaseModel):
    global_fanout_limit: int
    same_repo_max_when_others_idle: int | None = None
    repo_count: int
    automation_enabled_count: int = 0
    ready_slice_count: int = 0
    running_slice_count: int = 0


class RepoResponse(BaseModel):
    id: str
    github_slug: str
    integration_branch: str
    automation_enabled: bool
    priority: int | None = None
    readiness: dict[str, bool]
    repo_native_paths: dict[str, str]
    workers: list[dict[str, Any]] = []
    slice_summary: dict[str, int] = {}


class SliceResponse(BaseModel):
    slice_id: str
    slice_number: int
    title: str
    state: str
    repo_id: str
    github_slug: str | None = None
    automation_eligible: bool
    operator_gates: list[str] = []
    dependencies: list[int] = []
    repo_native_path: str


class RunResponse(BaseModel):
    run_id: str
    repo_id: str
    slice_id: str | None = None
    task_id: str | None = None
    runtime: str
    status: str
    started_at: str
    completed_at: str | None = None
    model_slug: str | None = None
    artifact_source: str | None = None
    repo_native_artifact_path: str | None = None
    evidence_status: str | None = None
    pr_url: str | None = None
    handoff_path: str | None = None


class DispatchResponse(BaseModel):
    dispatch_id: str
    orchestrator_run_id: str
    repo_id: str
    worker_id: str
    slice_id: str
    adapter_type: str | None = None
    status: str
    dispatched_at: str
    webhook_url_env_name: str | None = None
    chain_back: bool | None = None
    retry_count: int = 0
    task_packet_id: str | None = None
    error_summary: str | None = None


@router.get("/portfolio", response_model=PortfolioResponse)
def portfolio(request: Request) -> dict[str, Any]:
    return _dashboard(request).portfolio


@router.get("/repos", response_model=list[RepoResponse])
def repos(request: Request) -> list[dict[str, Any]]:
    return _dashboard(request).repos


@router.get("/repos/{repo_id}", response_model=RepoResponse)
def repo_detail(repo_id: str, request: Request) -> dict[str, Any]:
    for repo in _dashboard(request).repos:
        if repo["id"] == repo_id:
            return repo
    raise HTTPException(status_code=404, detail=f"repo not found: {repo_id}")


@router.get("/repos/{repo_id}/slices", response_model=list[SliceResponse])
def repo_slices(repo_id: str, request: Request) -> list[dict[str, Any]]:
    matches = [item for item in _dashboard(request).slices if item["repo_id"] == repo_id]
    if not matches and not any(repo["id"] == repo_id for repo in _dashboard(request).repos):
        raise HTTPException(status_code=404, detail=f"repo not found: {repo_id}")
    return matches


@router.get("/runs", response_model=list[RunResponse], response_model_exclude_none=True)
def runs() -> list[dict[str, Any]]:
    return runs_from_examples()


@router.get("/runs/{run_id}", response_model=RunResponse, response_model_exclude_none=True)
def run_detail(run_id: str) -> dict[str, Any]:
    for run in runs_from_examples():
        if run["run_id"] == run_id:
            return run
    raise HTTPException(status_code=404, detail=f"run not found: {run_id}")


@router.get("/dispatches", response_model=list[DispatchResponse])
def dispatches() -> list[dict[str, Any]]:
    return dispatches_from_examples()


def _dashboard(request: Request) -> DashboardProjection:
    return build_dashboard(_snapshot(request))


def _snapshot(request: Request) -> SyncSnapshot:
    service = getattr(request.app.state, "github_sync_service", None)
    if isinstance(service, GitHubSyncService) and service.cache.snapshot is not None:
        return service.cache.snapshot

    cache = getattr(request.app.state, "sync_cache", None)
    if isinstance(cache, InMemorySyncCache) and cache.snapshot is not None:
        return cache.snapshot

    return snapshot_from_examples()
