"""Shared validation result helpers for cross-runtime parity."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any

CHECK_STATUSES = frozenset({"passed", "failed", "skipped", "error"})
OVERALL_STATUSES = frozenset({"passed", "failed", "not_run", "partial"})

DEFAULT_OUTPUT_TAIL_LINES = 20
DEFAULT_COMMAND_TIMEOUT_SECONDS = 900


def tail_output(text: str, max_lines: int = DEFAULT_OUTPUT_TAIL_LINES) -> str:
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text.rstrip()
    omitted = len(lines) - max_lines
    return f"... ({omitted} lines omitted)\n" + "\n".join(lines[-max_lines:])


def derive_check_name(command: str, explicit_name: str | None = None) -> str:
    if explicit_name:
        return explicit_name.strip()
    stripped = command.strip()
    if not stripped:
        return "unnamed-check"
    first_token = stripped.split()[0]
    if "/" in first_token or first_token.endswith(".py") or first_token.endswith(".sh"):
        return Path(first_token).name
    return first_token


def run_check(
    command: str,
    *,
    check_name: str | None = None,
    cwd: Path | str | None = None,
    timeout_seconds: int = DEFAULT_COMMAND_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    name = derive_check_name(command, check_name)
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            shell=True,
            cwd=str(cwd) if cwd is not None else None,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        duration_ms = int((time.monotonic() - started) * 1000)
        combined = (completed.stdout or "") + (completed.stderr or "")
        status = "passed" if completed.returncode == 0 else "failed"
        return {
            "check_name": name,
            "status": status,
            "command": command,
            "exit_code": completed.returncode,
            "output": tail_output(combined),
            "duration_ms": duration_ms,
        }
    except subprocess.TimeoutExpired as exc:
        duration_ms = int((time.monotonic() - started) * 1000)
        combined = (exc.stdout or "") + (exc.stderr or "")
        return {
            "check_name": name,
            "status": "error",
            "command": command,
            "exit_code": 124,
            "output": tail_output(combined or f"command timed out after {timeout_seconds}s"),
            "duration_ms": duration_ms,
        }
    except OSError as exc:
        duration_ms = int((time.monotonic() - started) * 1000)
        return {
            "check_name": name,
            "status": "error",
            "command": command,
            "exit_code": 1,
            "output": str(exc),
            "duration_ms": duration_ms,
        }


def compute_overall(checks: list[dict[str, Any]]) -> str:
    if not checks:
        return "not_run"

    statuses = [check.get("status") for check in checks]
    if all(status == "skipped" for status in statuses):
        return "not_run"
    if any(status in {"failed", "error"} for status in statuses):
        if any(status == "passed" for status in statuses):
            return "partial"
        return "failed"
    if any(status == "passed" for status in statuses):
        return "passed"
    return "not_run"


def build_validation_results(
    checks: list[dict[str, Any]],
    *,
    runtime: str | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "overall": compute_overall(checks),
        "checks": checks,
    }
    if runtime:
        payload["runtime"] = runtime
    if source:
        payload["source"] = source
    return payload


def run_validation_commands(
    commands: list[str],
    *,
    cwd: Path | str | None = None,
    runtime: str | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    checks = [run_check(command, cwd=cwd) for command in commands]
    return build_validation_results(checks, runtime=runtime, source=source)


def validation_results_schema_path(repo_root: Path | None = None) -> Path:
    base = repo_root or Path(__file__).resolve().parents[1]
    return base / "adapters" / "validation-results.schema.json"


def load_validation_results_schema(repo_root: Path | None = None) -> dict[str, Any]:
    return json.loads(validation_results_schema_path(repo_root).read_text(encoding="utf-8"))


def validate_validation_results(payload: dict[str, Any], repo_root: Path | None = None) -> list[str]:
    try:
        from jsonschema import Draft7Validator
    except ImportError:
        import sys

        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet", "jsonschema"]
        )
        from jsonschema import Draft7Validator

    schema = load_validation_results_schema(repo_root)
    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda err: list(err.path))
    return [
        f"{err.message} ({'.'.join(str(part) for part in err.path)})"
        for err in errors
    ]


def load_slice_pipeline_validation_commands(repo_root: Path | None = None) -> list[str]:
    base = repo_root or Path(__file__).resolve().parents[1]
    config_path = base / ".cursor" / "slice-pipeline-local.config.json"
    if not config_path.is_file():
        return []

    config = json.loads(config_path.read_text(encoding="utf-8"))
    commands = config.get("validationCommands") or []
    if isinstance(commands, str):
        return [commands]
    if isinstance(commands, list):
        return [str(command) for command in commands if str(command).strip()]
    return []


def default_repo_validation_commands(repo_root: Path | None = None) -> list[str]:
    configured = load_slice_pipeline_validation_commands(repo_root)
    if configured:
        return configured
    base = repo_root or Path(__file__).resolve().parents[1]
    return ["bash scripts/ci_preflight.sh"] if (base / "scripts" / "ci_preflight.sh").is_file() else []
