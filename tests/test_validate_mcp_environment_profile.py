"""MCP environment profile validation.

Profiles are committed, so anything in one is public. The rules that matter:
no credentials in a forbidden tier, stdio servers declare a command, http servers
declare a url, and the default tier has to exist. This file ships inside the
slice-pipeline-local bundle, so an adopter gets the tests for the validator they
just installed.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = REPO_ROOT / "scripts/validate_mcp_environment_profile.py"
FIXTURE = REPO_ROOT / "tests/fixtures/mcp_environment_profile.valid.json"


def load_fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def run_validator(profile_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "--profile", str(profile_path)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def write_profile(tmp_path: Path, profile: dict) -> Path:
    path = tmp_path / "mcp_environment_profile.json"
    path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
    return path


def test_shipped_fixture_profile_is_valid() -> None:
    result = subprocess.run(
        [sys.executable, str(VALIDATOR)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout


def test_credentials_in_a_forbidden_tier_fail(tmp_path: Path) -> None:
    profile = load_fixture()
    dev_servers = profile["tiers"]["dev"]["mcp_servers"]
    first_server = next(iter(dev_servers))
    dev_servers[first_server]["credential_refs"] = ["SOME_TOKEN"]

    result = run_validator(write_profile(tmp_path, profile))

    assert result.returncode == 1
    assert "credential_refs" in result.stderr


def test_stdio_server_without_command_fails(tmp_path: Path) -> None:
    profile = load_fixture()
    dev_servers = profile["tiers"]["dev"]["mcp_servers"]
    first_server = next(iter(dev_servers))
    dev_servers[first_server].pop("command", None)

    result = run_validator(write_profile(tmp_path, profile))

    assert result.returncode == 1
    assert "requires command" in result.stderr


def test_default_tier_must_exist(tmp_path: Path) -> None:
    profile = load_fixture()
    profile["default_tier"] = "nowhere"

    result = run_validator(write_profile(tmp_path, profile))

    assert result.returncode == 1
    assert "default_tier" in result.stderr


def test_enabled_production_server_needs_a_human_gate(tmp_path: Path) -> None:
    profile = load_fixture()
    profile["credential_policy"]["human_gate_tiers"] = []
    production_servers = profile["tiers"]["production"]["mcp_servers"]
    first_server = next(iter(production_servers))
    production_servers[first_server]["enabled"] = True

    result = run_validator(write_profile(tmp_path, profile))

    assert result.returncode == 1
    assert "human_gate_tiers" in result.stderr
