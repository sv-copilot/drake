"""The example configuration must stay a configuration, not a decoration.

An example that does not validate, or that names a harness the catalogue does not have, is
worse than no example: it is a template people copy into their own repository and then debug.
So the example is tested like the machinery it describes.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
EXAMPLE = REPO_ROOT / "examples" / "governed-workspace"
CONFIG = EXAMPLE / ".drake" / "slice-pipeline.config.json"
TREE = EXAMPLE / ".docs" / "slice_dependency_tree.json"
WRAPPER = EXAMPLE / "scripts" / "run-slice.sh"
DOCS = REPO_ROOT / "docs" / "example-configuration.md"


def catalogue_ids() -> list[str]:
    harnesses = json.loads(
        (REPO_ROOT / "adapters" / "harnesses.json").read_text(encoding="utf-8")
    )["harnesses"]
    return [entry["id"] for entry in harnesses]


def test_the_example_config_names_a_real_harness() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))

    assert config["harness"]["id"] in catalogue_ids(), (
        f"the example points at a harness the catalogue does not have: {config['harness']['id']}"
    )


def test_the_example_config_points_at_files_that_exist() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))

    for key in ("dependencyTreePath", "sliceBacklogPath", "sliceDetailDir"):
        assert (EXAMPLE / config[key]).exists(), f"{key} points at {config[key]}, which is absent"

    assert config["validationCommands"], "the example must show a validation command"


def test_the_example_tree_validates_with_the_repo_validator() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "validate_slice_dependency_tree.py"),
            "--tree",
            str(TREE),
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env={**os.environ, "PYTHONPATH": ""},
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_every_slice_has_a_detail_document() -> None:
    tree = json.loads(TREE.read_text(encoding="utf-8"))

    for row in tree["slices"]:
        detail = EXAMPLE / ".docs" / "slices" / f"{row['slice_id']}.md"
        assert detail.is_file(), f"{row['slice_id']} has no detail document"

        # Work that will actually be run must say how it proves itself. A gated slice is
        # waiting on a decision, so it has nothing to check yet — and must not be forced
        # to invent one.
        if row.get("automation_eligible") and not row.get("operator_gates"):
            assert "CHECK:" in detail.read_text(encoding="utf-8"), (
                f"{row['slice_id']} is automation eligible but does not name how it proves itself"
            )


def test_the_example_shows_a_gated_slice() -> None:
    """The operator-gate concept is the part people get wrong, so the example must show it."""
    tree = json.loads(TREE.read_text(encoding="utf-8"))

    gated = [row for row in tree["slices"] if row.get("operator_gates")]
    assert gated, "the example no longer demonstrates an operator-gated slice"
    for row in gated:
        assert row["state"] == "gated", f"{row['slice_id']} has gates but state={row['state']}"
        assert row["automation_eligible"] is False, (
            f"{row['slice_id']} is gated and must not be automation eligible"
        )


def test_the_wrapper_is_runnable() -> None:
    assert WRAPPER.is_file()
    assert os.access(WRAPPER, os.X_OK), "the example wrapper must be executable"
    text = WRAPPER.read_text(encoding="utf-8")
    assert "run-next" in text and "SLICE_AGENT_RUNNER" in text


def test_the_recommendations_document_links_the_example() -> None:
    docs = DOCS.read_text(encoding="utf-8")

    assert "examples/governed-workspace" in docs, "the recommendations must link the example"
    for harness_id in catalogue_ids():
        assert f"`{harness_id}`" in docs, f"{harness_id} is missing from the harness table"
