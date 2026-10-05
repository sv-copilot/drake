#!/usr/bin/env bash
#
# Adoption smoke: prove the documented adoption path actually works.
#
# Builds a throwaway product repo, installs the slice-pipeline-local bundle into
# it with the same command docs/getting-started.md gives an adopter, then drives
# the reference runner far enough to select a slice and render its task packet.
# No network, no model call, no credentials.
#
# This script exists because the documented path was broken and nothing noticed:
# the bundle referenced a template file that did not exist, the generated config
# pointed at a selector script the installer never installed, and the runner
# required two files nothing provided. Every one of those is a crash on the
# adopter's first command, and every one of them is caught here.
#
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
runner="$repo_root/tools/slice-agent-runner/dist/index.js"
python_bin="${PYTHON:-python3}"

if [ ! -f "$runner" ]; then
  echo "adoption smoke: FAILED - build the runner first:" >&2
  echo "  npm --prefix tools/slice-agent-runner ci && npm --prefix tools/slice-agent-runner run build" >&2
  exit 1
fi

work="$(mktemp -d)"
cleanup() { rm -rf "$work"; }
trap cleanup EXIT

app="$work/example-app"
mkdir -p "$app/src/example_app" "$app/tests" "$app/scripts" "$app/.docs/slices"

cat > "$app/src/example_app/__init__.py" <<'PY'
from example_app.adder import add

__all__ = ["add"]
PY

cat > "$app/src/example_app/adder.py" <<'PY'
"""Tiny domain module used to exercise the slice pipeline end to end."""


def add(left: int, right: int) -> int:
    return left + right
PY

cat > "$app/tests/test_adder.py" <<'PY'
from example_app.adder import add


def test_add() -> None:
    assert add(2, 3) == 5
PY

cat > "$app/scripts/ci_preflight.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}" python3 -m pytest tests -q
SH
chmod +x "$app/scripts/ci_preflight.sh"

cat > "$app/.docs/slice_backlog.md" <<'MD'
# Smoke App slice backlog

| Rank | Slice | State | Validation |
| --- | --- | --- | --- |
| 1 | `SMOKE-1` — prove adoption works | ready | `bash scripts/ci_preflight.sh` |
MD

cat > "$app/.docs/slice_dependency_tree.json" <<'JSON'
{
  "schema_version": 2,
  "generated_at": "2026-10-05T00:00:00Z",
  "source_backlog_path": ".docs/slice_backlog.md",
  "default_fanout_limit": 1,
  "notes": ["Adoption smoke fixture."],
  "slices": [
    {
      "slice_id": "SMOKE-1",
      "slice_number": 1,
      "group": "technical",
      "title": "Prove adoption works",
      "state": "ready",
      "status": "ready",
      "dependencies": [],
      "blocks": [],
      "operator_gates": [],
      "checkpoint": "low-risk",
      "automation_eligible": true,
      "priority": 1,
      "last_known_pr": null,
      "risk": "low",
      "effort": "small",
      "tier": "P0"
    }
  ]
}
JSON

cat > "$app/.docs/slices/SMOKE-1.md" <<'MD'
# SMOKE-1: Prove adoption works

| Field | Value |
|---|---|
| Slice # | 1 |
| State | ready |
| Tier | P0 |
| Automation eligible | true |

## Goal

The adoption path installs, validates, and selects this slice.

## Acceptance

- [ ] the fixture's own gate passes
  CHECK: bash scripts/ci_preflight.sh
MD

(
  cd "$app"
  git init -q
  git add -A
  git -c user.name=smoke -c user.email=smoke@example.invalid commit -qm "smoke fixture"
)

echo "adoption smoke: the fixture's own gate"
(cd "$app" && PYTHONPATH="$app/src" "$python_bin" -m pytest tests -q)

echo "adoption smoke: install the bundle"
install_flags=(
  --target "$app"
  --project-name "Smoke App"
  --project-id smoke-app
  --github-slug smoke-org/smoke-app
  --integration-branch dev
  --validation-commands "bash scripts/ci_preflight.sh"
  --harnesses generic
  --harness-command "bash scripts/harness_stub.sh {prompt_file}"
)
"$python_bin" "$repo_root/scripts/sync_slice_pipeline_local.py" --mode install "${install_flags[@]}" >/dev/null

echo "adoption smoke: check mode reports the installed target as complete"
# check compares the target against the flags it is given, so it gets the same
# flags the install used.
if ! "$python_bin" "$repo_root/scripts/sync_slice_pipeline_local.py" --mode check "${install_flags[@]}" > "$work/check-install.txt" 2>&1; then
  echo "adoption smoke: FAILED - check mode is unhappy after a successful install" >&2
  cat "$work/check-install.txt" >&2
  exit 1
fi

for required in AGENTS.md .docs/git_workflow.md scripts/select_next_automation_slice.py scripts/slice_lifecycle.py .drake/slice-pipeline.config.json .drake/agents/slice-implementer.md .drake/runs/.gitignore scripts/harness_stub.sh; do
  if [ ! -f "$app/$required" ]; then
    echo "adoption smoke: FAILED - installer did not provide $required" >&2
    exit 1
  fi
done

# A real adopter commits the installed bundle. Without that commit, every
# installed file is an untracked change and evidence would attribute all of them to
# the harness run instead of naming only what the run actually touched.
(
  cd "$app"
  git add -A
  git -c user.name=smoke -c user.email=smoke@example.invalid commit -qm "install slice pipeline"
)

echo "adoption smoke: validate the dependency tree"
"$python_bin" "$repo_root/scripts/validate_slice_dependency_tree.py" --tree "$app/.docs/slice_dependency_tree.json"

echo "adoption smoke: runner check"
if ! node "$runner" check --repo "$app" > "$work/check.txt" 2>&1; then
  cat "$work/check.txt" >&2
  exit 1
fi
grep -q "check: passed" "$work/check.txt" || { cat "$work/check.txt" >&2; exit 1; }
grep -q "next slice:" "$work/check.txt" || { cat "$work/check.txt" >&2; exit 1; }

echo "adoption smoke: runner run-next --dry-run selects the ready slice"
if ! node "$runner" run-next --repo "$app" --dry-run > "$work/dryrun.txt" 2>&1; then
  cat "$work/dryrun.txt" >&2
  exit 1
fi
grep -q '"target_slice_id": "SMOKE-1"' "$work/dryrun.txt" || { cat "$work/dryrun.txt" >&2; exit 1; }
if grep -q "Traceback" "$work/dryrun.txt"; then
  echo "adoption smoke: FAILED - selector crashed" >&2
  cat "$work/dryrun.txt" >&2
  exit 1
fi

echo "adoption smoke: a real harness run, no credentials, no model call"
if ! node "$runner" run-next --repo "$app" > "$work/run.txt" 2>&1; then
  echo "adoption smoke: FAILED - the documented run-next failed" >&2
  cat "$work/run.txt" >&2
  exit 1
fi
grep -q "stub harness: wrote" "$work/run.txt" || { cat "$work/run.txt" >&2; exit 1; }
run_dir="$(ls -dt "$app"/.drake/runs/*/ | head -1)"

echo "adoption smoke: the run's packet and evidence satisfy the contracts"
"$python_bin" "$repo_root/scripts/validate_run_artifacts.py" --run "$run_dir" > "$work/artifacts.txt" 2>&1 || {
  cat "$work/artifacts.txt" >&2
  exit 1
}
"$python_bin" - "$run_dir" <<'PY'
import json
import pathlib
import sys

run = pathlib.Path(sys.argv[1])
evidence = json.loads((run / "evidence.json").read_text(encoding="utf-8"))
assert evidence["status"] == "success", evidence["status"]
assert evidence["harness"]["exit_code"] == 0
assert evidence["evidence_items"], "the stub harness wrote a file, so evidence must name it"
assert any(
    ".drake/stub-harness-output.txt" in item["path"] for item in evidence["evidence_items"]
), evidence["evidence_items"]
assert (run / "task-packet.json").is_file()
print("  evidence:", evidence["status"], "| changed files:", len(evidence["evidence_items"]))
PY

echo "adoption smoke: a failing harness is recorded, not swallowed"
set +e
STUB_HARNESS_FAIL=1 node "$runner" run-next --repo "$app" > "$work/run-failed.txt" 2>&1
failed_exit=$?
set -e
if [ "$failed_exit" -ne 2 ]; then
  echo "adoption smoke: FAILED - expected exit 2 from a failing harness, got $failed_exit" >&2
  cat "$work/run-failed.txt" >&2
  exit 1
fi
failed_dir="$(ls -dt "$app"/.drake/runs/*/ | head -1)"
"$python_bin" - "$failed_dir" <<'PY'
import json
import pathlib
import sys

run = pathlib.Path(sys.argv[1])
evidence = json.loads((run / "evidence.json").read_text(encoding="utf-8"))
assert evidence["status"] == "failure", evidence["status"]
assert evidence["harness"]["exit_code"] != 0
print("  failing run recorded as:", evidence["status"])
PY

echo "adoption smoke: nothing runnable is reported, not crashed on"
cat > "$app/.docs/slice_dependency_tree.json" <<'JSON'
{
  "schema_version": 2,
  "generated_at": "2026-10-05T00:00:00Z",
  "source_backlog_path": ".docs/slice_backlog.md",
  "default_fanout_limit": 1,
  "slices": [
    {
      "slice_id": "SMOKE-1",
      "slice_number": 1,
      "group": "technical",
      "title": "Prove adoption works",
      "state": "gated",
      "status": "ready",
      "dependencies": [],
      "blocks": [],
      "operator_gates": ["operator approval"],
      "checkpoint": "low-risk",
      "automation_eligible": true,
      "priority": 1,
      "last_known_pr": null,
      "risk": "low",
      "effort": "small",
      "tier": "P0"
    }
  ]
}
JSON
# `set -e` would abort before we can read the exit code, and the exit code is the
# whole point of this scenario.
set +e
node "$runner" run-next --repo "$app" --local --dry-run > "$work/gated.txt" 2>&1
gated_exit=$?
set -e
if [ "$gated_exit" -ne 3 ]; then
  echo "adoption smoke: FAILED - expected exit 3 with nothing runnable, got $gated_exit" >&2
  cat "$work/gated.txt" >&2
  exit 1
fi
if ! grep -q "no runnable slice" "$work/gated.txt"; then
  echo "adoption smoke: FAILED - nothing runnable was not explained" >&2
  cat "$work/gated.txt" >&2
  exit 1
fi
if grep -q "Traceback" "$work/gated.txt"; then
  echo "adoption smoke: FAILED - nothing runnable printed a traceback" >&2
  cat "$work/gated.txt" >&2
  exit 1
fi

echo "adoption smoke passed"
