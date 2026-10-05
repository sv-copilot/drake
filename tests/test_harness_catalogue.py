"""The harness catalogue must be one catalogue, not four approximations.

Harness ids and invocations live in the runner, the installer, the machine-readable
mirror and the docs. A harness that exists in only some of them is worse than no
harness at all: the installer rejects a valid id, or the docs describe a command the
runner will not build.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import re
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
HARNESSES_TS = REPO_ROOT / "tools" / "slice-agent-runner" / "src" / "harnesses.ts"
MIRROR = REPO_ROOT / "adapters" / "harnesses.json"
DOCS = REPO_ROOT / "docs" / "harnesses.md"


def _load_installer():
    sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        return importlib.import_module("sync_slice_pipeline_local")
    finally:
        sys.path.pop(0)


installer = _load_installer()


def runner_ids() -> list[str]:
    source = HARNESSES_TS.read_text(encoding="utf-8")
    return re.findall(r'^    id: "([a-z0-9-]+)",$', source, flags=re.MULTILINE)


def mirror_entries() -> list[dict]:
    return json.loads(MIRROR.read_text(encoding="utf-8"))["harnesses"]


def test_every_source_lists_the_same_harnesses() -> None:
    ids = runner_ids()
    assert ids, "could not parse harness ids out of harnesses.ts"

    assert ids == list(installer.HARNESS_IDS), "runner and installer disagree"
    assert ids == [entry["id"] for entry in mirror_entries()], "runner and mirror disagree"

    docs = DOCS.read_text(encoding="utf-8")
    for harness_id in ids:
        assert f"`{harness_id}`" in docs, f"{harness_id} is missing from docs/harnesses.md"


def test_no_harness_needs_a_vendor_sdk() -> None:
    """The runner drives child processes; a model SDK dependency would undo that."""
    package = json.loads(
        (REPO_ROOT / "tools" / "slice-agent-runner" / "package.json").read_text(
            encoding="utf-8"
        )
    )
    assert "@cursor/sdk" not in json.dumps(package)

    for source in (REPO_ROOT / "tools" / "slice-agent-runner" / "src").glob("*.ts"):
        text = source.read_text(encoding="utf-8")
        assert "@cursor/sdk" not in text, source


def test_every_catalogue_entry_is_complete_and_dated() -> None:
    for entry in mirror_entries():
        assert entry["docs_url"].startswith("http") or entry["docs_url"].endswith(".md")
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", entry["verified_on"]), entry["id"]
        assert entry["prompt_delivery"] in {"argv", "stdin", "file"}
        if entry["id"] == "generic":
            assert entry["binary"] is None
        else:
            assert entry["binary"], entry["id"]
            assert entry["invocation"]


def test_prompt_delivery_matches_the_invocation() -> None:
    """A harness that needs a file must be shown a file, and vice versa."""
    source = HARNESSES_TS.read_text(encoding="utf-8")
    for entry in mirror_entries():
        if entry["id"] == "generic":
            continue
        block = source.split(f'id: "{entry["id"]}"', 1)[1].split("  },", 1)[0]
        delivery = re.search(r'promptDelivery: "(\w+)"', block)
        assert delivery, entry["id"]
        assert delivery.group(1) == entry["prompt_delivery"], entry["id"]
        if entry["prompt_delivery"] == "file":
            assert "{prompt_file}" in block, entry["id"]
        else:
            assert '"{prompt}"' in block, entry["id"]
