from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from hosted_api.main import create_app

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))


def test_read_endpoints_return_example_portfolio_projection() -> None:
    client = TestClient(create_app())

    portfolio = client.get("/api/v1/portfolio")
    repos = client.get("/api/v1/repos")
    slices = client.get("/api/v1/repos/example-app/slices")
    runs = client.get("/api/v1/runs")

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
    assert runs.json() == []


def test_read_endpoints_return_404_for_unknown_resources() -> None:
    client = TestClient(create_app())

    assert client.get("/api/v1/repos/missing").status_code == 404
    assert client.get("/api/v1/repos/missing/slices").status_code == 404
    assert client.get("/api/v1/runs/missing").status_code == 404


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

    schema = load_json(REPO_ROOT / ".docs/hosted_api_sketch.schema.json")
    assert validate_with_schema(fixture, schema) == []
