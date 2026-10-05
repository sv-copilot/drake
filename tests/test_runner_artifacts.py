"""The runner's contract artifacts must satisfy the published schemas.

The fixture in tests/fixtures/automation-runs/stub-harness-run was produced by the
real runner driving the stub harness: no credentials, no model call, no network.
If the runner's output drifts from adapters/*.schema.json, this fails.
"""

from __future__ import annotations

import json
import pathlib
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import validate_run_artifacts as artifacts  # noqa: E402

FIXTURE = (
    REPO_ROOT / "tests" / "fixtures" / "automation-runs" / "stub-harness-run"
)


@pytest.fixture(autouse=True)
def _require_jsonschema():
    pytest.importorskip("jsonschema")


def test_fixture_run_satisfies_contracts():
    problems = artifacts.validate(FIXTURE)
    assert problems == [], problems


def test_evidence_records_the_harness_that_ran():
    evidence = json.loads((FIXTURE / "evidence.json").read_text(encoding="utf-8"))
    assert evidence["status"] == "success"
    assert evidence["adapter_info"]["adapter_type"] == "generic"
    assert evidence["harness"]["exit_code"] == 0
    assert evidence["evidence_items"], (
        "a harness that wrote a file must produce at least one evidence item"
    )
    assert evidence["timestamps"]["completed_at"]


def test_packet_names_the_slice_and_the_harness():
    packet = json.loads((FIXTURE / "task-packet.json").read_text(encoding="utf-8"))
    assert packet["task_type"] == "implement_slice"
    assert packet["adapter_type"] == "generic"
    assert packet["slice_ref"]["slice_id"]
    assert packet["payload"]["instructions"].strip()
    assert packet["payload"]["working_directory"]


def test_validator_reports_missing_artifacts(tmp_path):
    problems = artifacts.validate(tmp_path)
    assert len(problems) == 2
    assert all("missing" in problem for problem in problems)


def test_relative_schema_reference_resolves_locally():
    """evidence-contract refs validation-results by relative path; must not need network."""
    import json as _json

    schema = _json.loads(
        (REPO_ROOT / "adapters" / "evidence-contract.schema.json").read_text(
            encoding="utf-8"
        )
    )
    references = _json.dumps(schema).count("validation-results.schema.json")
    assert references >= 1
    problems = artifacts.validate(FIXTURE)
    assert not any("Unresolvable" in problem for problem in problems)
