#!/usr/bin/env python3
"""Fetch repository files from GitHub when local sibling repos are unavailable.

Cloud agents and the portfolio orchestrator often need slice docs from product
repos that are not cloned on disk. This script treats GitHub as the canonical
source for those paths at a given ref.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


GITHUB_API = "https://api.github.com"


@dataclass(frozen=True)
class FetchResult:
    path: str
    content: str
    sha: str | None
    source: str


class FetchError(RuntimeError):
    """Raised when one or more paths cannot be fetched."""


def _auth_headers() -> dict[str, str]:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "drake-fetch-github-path",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _decode_contents_payload(payload: dict[str, Any]) -> str:
    if payload.get("encoding") != "base64":
        raise FetchError(
            f"unsupported GitHub contents encoding for {payload.get('path')}: "
            f"{payload.get('encoding')!r}"
        )
    encoded = payload.get("content", "")
    if not isinstance(encoded, str):
        raise FetchError(f"invalid GitHub contents payload for {payload.get('path')}")
    return base64.b64decode(encoded).decode("utf-8")


def _fetch_via_gh_api(repo: str, ref: str, path: str) -> FetchResult:
    quoted_path = urllib.parse.quote(path, safe="/")
    command = [
        "gh",
        "api",
        f"repos/{repo}/contents/{quoted_path}",
        "-f",
        f"ref={ref}",
    ]
    result = subprocess.run(
        command,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise FetchError(f"gh api failed for {path}: {detail}")

    payload = json.loads(result.stdout)
    return FetchResult(
        path=path,
        content=_decode_contents_payload(payload),
        sha=payload.get("sha"),
        source="gh_api",
    )


def _fetch_via_http(repo: str, ref: str, path: str) -> FetchResult:
    quoted_path = urllib.parse.quote(path, safe="/")
    query = urllib.parse.urlencode({"ref": ref})
    url = f"{GITHUB_API}/repos/{repo}/contents/{quoted_path}?{query}"
    request = urllib.request.Request(url, headers=_auth_headers())
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise FetchError(f"HTTP {exc.code} for {path}: {body}") from exc
    except urllib.error.URLError as exc:
        raise FetchError(f"network error for {path}: {exc}") from exc

    return FetchResult(
        path=path,
        content=_decode_contents_payload(payload),
        sha=payload.get("sha"),
        source="http_api",
    )


def fetch_github_path(
    repo: str,
    ref: str,
    path: str,
    *,
    prefer_gh: bool = True,
) -> FetchResult:
    """Fetch a single file from GitHub at ref."""

    normalized = path.lstrip("/")
    if not normalized:
        raise FetchError("path must not be empty")

    if prefer_gh and shutil_which("gh"):
        try:
            return _fetch_via_gh_api(repo, ref, normalized)
        except (FetchError, json.JSONDecodeError, FileNotFoundError):
            return _fetch_via_http(repo, ref, normalized)
    return _fetch_via_http(repo, ref, normalized)


def fetch_github_paths(
    repo: str,
    ref: str,
    paths: list[str],
    *,
    prefer_gh: bool = True,
) -> list[FetchResult]:
    """Fetch multiple files, raising FetchError with all failures aggregated."""

    results: list[FetchResult] = []
    errors: list[str] = []
    for path in paths:
        try:
            results.append(fetch_github_path(repo, ref, path, prefer_gh=prefer_gh))
        except FetchError as exc:
            errors.append(str(exc))
    if errors:
        raise FetchError("; ".join(errors))
    return results


def write_results(results: list[FetchResult], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for item in results:
        target = output_dir / item.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(item.content, encoding="utf-8")


def shutil_which(command: str) -> str | None:
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(directory) / command
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="GitHub slug, e.g. owner/repo")
    parser.add_argument("--ref", required=True, help="Branch, tag, or commit SHA")
    parser.add_argument(
        "--path",
        action="append",
        dest="paths",
        default=[],
        help="Repository-relative file path (repeatable)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Optional directory to write fetched files preserving repo paths",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON payload to stdout instead of raw file contents",
    )
    parser.add_argument(
        "--http-only",
        action="store_true",
        help="Skip gh api and use the GitHub REST API directly",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.paths:
        parser.error("at least one --path is required")

    try:
        results = fetch_github_paths(
            args.repo,
            args.ref,
            args.paths,
            prefer_gh=not args.http_only,
        )
    except FetchError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.output_dir:
        write_results(results, args.output_dir)

    if args.json:
        payload = {
            "repo": args.repo,
            "ref": args.ref,
            "files": [
                {
                    "path": item.path,
                    "sha": item.sha,
                    "source": item.source,
                    "content": item.content,
                }
                for item in results
            ],
        }
        print(json.dumps(payload, indent=2))
        return 0

    if len(results) == 1 and not args.output_dir:
        sys.stdout.write(results[0].content)
        if not results[0].content.endswith("\n"):
            sys.stdout.write("\n")
        return 0

    for item in results:
        print(f"=== {item.path} ===")
        sys.stdout.write(item.content)
        if not item.content.endswith("\n"):
            sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
