"""Shared automation run history constants and helpers."""

from __future__ import annotations

import json
import re
from pathlib import Path

RUNS_ROOT = ".cursor/automation-runs"
RUN_ID_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+$")

REQUIRED_RUN_FILES = (
    "metadata.json",
    "payload.json",
    "prompt.txt",
    "events.jsonl",
)

OPTIONAL_RUN_FILES = (
    "result.json",
    "handoff.json",
)


def normalize_run_id(value: str) -> str:
    run_id = value.strip()
    if not run_id or not RUN_ID_PATTERN.fullmatch(run_id):
        raise ValueError(f"invalid run id: {value!r}")
    return run_id


def runs_root(repo_root: Path | None = None) -> Path:
    base = repo_root or Path.cwd()
    return base / RUNS_ROOT


def list_run_dirs(runs_dir: Path) -> list[Path]:
    if not runs_dir.is_dir():
        return []

    candidates = [
        path
        for path in runs_dir.iterdir()
        if path.is_dir() and RUN_ID_PATTERN.fullmatch(path.name)
    ]
    return sorted(candidates, key=lambda path: path.stat().st_mtime, reverse=True)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_events_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []

    events: list[dict] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON on line {line_number} of {path}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"event record must be an object on line {line_number} of {path}")
        events.append(payload)
    return events


def missing_required_files(run_dir: Path) -> list[str]:
    return [name for name in REQUIRED_RUN_FILES if not (run_dir / name).is_file()]
