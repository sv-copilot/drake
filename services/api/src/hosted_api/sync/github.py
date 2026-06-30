from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

GITHUB_API = "https://api.github.com"
DEFAULT_REGISTRY_PATH = ".docs/projects-registry.json"
DEFAULT_TREE_PATH = ".docs/slice_dependency_tree.json"
DEFAULT_STALE_AFTER_SECONDS = 300


class GitHubSyncError(RuntimeError):
    """Raised when GitHub read sync cannot complete."""


@dataclass(frozen=True)
class FetchedFile:
    repo: str
    ref: str
    path: str
    content: str
    sha: str | None = None
    source: str = "github_contents"


class ContentsFetcher(Protocol):
    def fetch_file(self, repo: str, ref: str, path: str) -> FetchedFile:
        """Fetch a text file from a repository ref."""


@dataclass(frozen=True)
class GitHubSyncConfig:
    registry_repo: str
    registry_ref: str
    registry_path: str = DEFAULT_REGISTRY_PATH
    stale_after_seconds: int = DEFAULT_STALE_AFTER_SECONDS


@dataclass(frozen=True)
class SyncedFile:
    repo: str
    ref: str
    path: str
    sha: str | None
    source: str


@dataclass(frozen=True)
class ProjectTree:
    project_id: str
    github_slug: str
    ref: str
    path: str
    tree: dict[str, Any]


@dataclass(frozen=True)
class SyncSnapshot:
    synced_at: datetime
    stale_after_seconds: int
    registry: dict[str, Any]
    dependency_trees: dict[str, ProjectTree]
    files: list[SyncedFile]

    @property
    def is_stale(self) -> bool:
        return datetime.now(UTC) - self.synced_at > timedelta(
            seconds=self.stale_after_seconds,
        )


@dataclass
class InMemorySyncCache:
    snapshot: SyncSnapshot | None = None

    def set(self, snapshot: SyncSnapshot) -> None:
        self.snapshot = snapshot

    def status(self) -> dict[str, Any]:
        if self.snapshot is None:
            return {
                "status": "empty",
                "last_synced_at": None,
                "stale_after_seconds": DEFAULT_STALE_AFTER_SECONDS,
                "is_stale": True,
                "project_count": 0,
                "dependency_tree_count": 0,
            }

        return {
            "status": "ok",
            "last_synced_at": self.snapshot.synced_at.isoformat(),
            "stale_after_seconds": self.snapshot.stale_after_seconds,
            "is_stale": self.snapshot.is_stale,
            "project_count": len(self.snapshot.registry.get("projects", [])),
            "dependency_tree_count": len(self.snapshot.dependency_trees),
        }


@dataclass
class GitHubContentsFetcher:
    api_base: str = GITHUB_API
    timeout_seconds: int = 30
    token_env_names: tuple[str, ...] = ("GH_TOKEN", "GITHUB_TOKEN")

    def fetch_file(self, repo: str, ref: str, path: str) -> FetchedFile:
        normalized_path = path.lstrip("/")
        if not normalized_path:
            raise GitHubSyncError("path must not be empty")

        quoted_path = urllib.parse.quote(normalized_path, safe="/")
        query = urllib.parse.urlencode({"ref": ref})
        url = f"{self.api_base}/repos/{repo}/contents/{quoted_path}?{query}"
        request = urllib.request.Request(url, headers=self._headers())

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout_seconds,
            ) as response:
                payload = json.load(response)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise GitHubSyncError(
                f"GitHub contents request failed for {repo}:{normalized_path}: "
                f"HTTP {exc.code} {body}",
            ) from exc
        except urllib.error.URLError as exc:
            raise GitHubSyncError(
                f"GitHub contents request failed for {repo}:{normalized_path}: {exc}",
            ) from exc

        return FetchedFile(
            repo=repo,
            ref=ref,
            path=normalized_path,
            content=_decode_contents_payload(payload),
            sha=payload.get("sha"),
        )

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "drake-hosted-api-sync",
        }
        token = _first_env_value(self.token_env_names)
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers


@dataclass
class GitHubSyncService:
    fetcher: ContentsFetcher = field(default_factory=GitHubContentsFetcher)
    cache: InMemorySyncCache = field(default_factory=InMemorySyncCache)

    def pull(self, config: GitHubSyncConfig) -> SyncSnapshot:
        if not config.registry_repo:
            raise GitHubSyncError("registry_repo is required")
        if not config.registry_ref:
            raise GitHubSyncError("registry_ref is required")

        registry_file = self.fetcher.fetch_file(
            config.registry_repo,
            config.registry_ref,
            config.registry_path,
        )
        registry = _load_json(registry_file)
        files = [_synced_file(registry_file)]
        trees: dict[str, ProjectTree] = {}

        for project in registry.get("projects", []):
            project_id = _required_str(project, "id")
            github_slug = _required_str(project, "github_slug")
            ref = str(project.get("integration_branch") or config.registry_ref)
            tree_path = _dependency_tree_path(project)
            tree_file = self.fetcher.fetch_file(github_slug, ref, tree_path)
            tree = _load_json(tree_file)
            trees[project_id] = ProjectTree(
                project_id=project_id,
                github_slug=github_slug,
                ref=ref,
                path=tree_path,
                tree=tree,
            )
            files.append(_synced_file(tree_file))

        snapshot = SyncSnapshot(
            synced_at=datetime.now(UTC),
            stale_after_seconds=config.stale_after_seconds,
            registry=registry,
            dependency_trees=trees,
            files=files,
        )
        self.cache.set(snapshot)
        return snapshot


def _first_env_value(names: tuple[str, ...]) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


def _decode_contents_payload(payload: dict[str, Any]) -> str:
    if payload.get("encoding") != "base64":
        raise GitHubSyncError(
            f"unsupported GitHub contents encoding: {payload.get('encoding')!r}",
        )
    encoded = payload.get("content")
    if not isinstance(encoded, str):
        raise GitHubSyncError("invalid GitHub contents payload")
    return base64.b64decode(encoded).decode("utf-8")


def _load_json(file: FetchedFile) -> dict[str, Any]:
    try:
        payload = json.loads(file.content)
    except json.JSONDecodeError as exc:
        raise GitHubSyncError(f"invalid JSON in {file.repo}:{file.path}") from exc
    if not isinstance(payload, dict):
        raise GitHubSyncError(f"expected JSON object in {file.repo}:{file.path}")
    return payload


def _required_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise GitHubSyncError(f"project missing required string field {key!r}")
    return value


def _dependency_tree_path(project: dict[str, Any]) -> str:
    docs = project.get("docs") or {}
    path = docs.get("dependency_tree") or DEFAULT_TREE_PATH
    if not isinstance(path, str) or not path:
        raise GitHubSyncError("project docs.dependency_tree must be a string")
    return path


def _synced_file(file: FetchedFile) -> SyncedFile:
    return SyncedFile(
        repo=file.repo,
        ref=file.ref,
        path=file.path,
        sha=file.sha,
        source=file.source,
    )
