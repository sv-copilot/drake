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
)
python3 "$repo_root/scripts/sync_slice_pipeline_local.py" --mode install "${install_flags[@]}" >/dev/null

echo "adoption smoke: check mode reports the installed target as complete"
# check compares the target against the flags it is given, so it gets the same
# flags the install used.
if ! python3 "$repo_root/scripts/sync_slice_pipeline_local.py" --mode check "${install_flags[@]}" > "$work/check-install.txt" 2>&1; then
  echo "adoption smoke: FAILED - check mode is unhappy after a successful install" >&2
  cat "$work/check-install.txt" >&2
  exit 1
fi

for required in AGENTS.md .docs/git_workflow.md scripts/select_next_automation_slice.py scripts/slice_lifecycle.py .cursor/slice-pipeline-local.config.json; do
  if [ ! -f "$app/$required" ]; then
    echo "adoption smoke: FAILED - installer did not provide $required" >&2
    exit 1
  fi
done

echo "adoption smoke: validate the dependency tree"
python3 "$repo_root/scripts/validate_slice_dependency_tree.py" --tree "$app/.docs/slice_dependency_tree.json"

echo "adoption smoke: runner check"
if ! node "$runner" check --repo "$app" > "$work/check.txt" 2>&1; then
  cat "$work/check.txt" >&2
  exit 1
fi
grep -q "check: passed" "$work/check.txt" || { cat "$work/check.txt" >&2; exit 1; }
grep -q "selector: ok" "$work/check.txt" || { cat "$work/check.txt" >&2; exit 1; }

echo "adoption smoke: runner run-next --dry-run selects the ready slice"
if ! node "$runner" run-next --repo "$app" --local --dry-run > "$work/dryrun.txt" 2>&1; then
  cat "$work/dryrun.txt" >&2
  exit 1
fi
grep -q '"target_slice_id": "SMOKE-1"' "$work/dryrun.txt" || { cat "$work/dryrun.txt" >&2; exit 1; }
if grep -q "Traceback" "$work/dryrun.txt"; then
  echo "adoption smoke: FAILED - selector crashed" >&2
  cat "$work/dryrun.txt" >&2
  exit 1
fi

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
