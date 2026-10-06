#!/usr/bin/env bash
#
# Harness matrix smoke: the runner's behaviour across the catalogue, offline.
#
# Every scenario here is a promise the docs make: the right command per harness, a
# clear error when a harness cannot run, the documented exit codes 0/1/2/3, and
# evidence that validates against the contracts. No model call, no credentials, no
# network: the only harness actually executed is the stub.
#
set -uo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
runner="$repo_root/tools/slice-agent-runner/dist/index.js"
stub="bash scripts/harness_stub.sh {prompt_file}"
python_bin="${PYTHON:-python3}"

if [ ! -f "$runner" ]; then
  echo "harness matrix: FAILED - build the runner first (npm --prefix tools/slice-agent-runner run build)" >&2
  exit 1
fi

work="$(mktemp -d)"
cleanup() { rm -rf "$work"; }
trap cleanup EXIT

passed=0
failed=0

report() { # report <ok|fail> <label> [detail] [output-file]
  if [ "$1" = "ok" ]; then
    passed=$((passed + 1))
    printf '  ok   %s\n' "$2"
  else
    failed=$((failed + 1))
    printf '  FAIL %s\n' "$2"
    if [ -n "${3:-}" ]; then printf '       %s\n' "$3"; fi
    if [ -n "${4:-}" ] && [ -f "${4:-}" ]; then
      sed 's/^/       /' "$4" | head -5
    fi
  fi
}

target="$work/repo"
mkdir -p "$target"
"$python_bin" "$repo_root/scripts/sync_slice_pipeline_local.py" --target "$target" --mode install \
  --project-name "Matrix App" --project-id matrix-app --github-slug matrix-org/matrix-app \
  --validation-commands "bash scripts/ci_preflight.sh" \
  --harnesses generic --harness-command "$stub" >/dev/null 2>&1
(cd "$target" && git init -q && git add -A && git -c user.name=matrix -c user.email=matrix@example.invalid commit -qm fixture)

echo "harness matrix: catalogue"
out="$work/harnesses.txt"
node "$runner" harnesses > "$out" 2>&1
missing=""
for id in claude codex cursor aider generic; do
  grep -q "^$id  —" "$out" || missing="$missing $id"
done
if [ -z "$missing" ]; then
  report ok "harnesses lists every catalogue id"
else
  report fail "harnesses lists every catalogue id" "missing:$missing" "$out"
fi

echo "harness matrix: rendered commands (dry run, no model configured)"
for pair in "claude:-p" "codex:exec --sandbox workspace-write" "cursor:-p --force" "aider:--message-file"; do
  id="${pair%%:*}"
  expect="${pair#*:}"
  out="$work/dry-$id.txt"
  node "$runner" run-next --repo "$target" --harness "$id" --dry-run > "$out" 2>&1
  status=$?
  if [ "$status" -ne 0 ]; then
    report fail "dry run renders the $id command" "exit $status" "$out"
  elif ! grep -qF -- "$expect" "$out"; then
    report fail "dry run renders the $id command" "expected '$expect'" "$out"
  elif grep -q -- '--model' "$out"; then
    report fail "dry run omits --model when none is configured ($id)" "" "$out"
  else
    report ok "dry run renders the $id command without a model flag"
  fi
done

out="$work/dry-model.txt"
node "$runner" run-next --repo "$target" --harness claude --model sonnet --dry-run > "$out" 2>&1
if grep -q -- "--model sonnet" "$out"; then
  report ok "a configured model is passed through"
else
  report fail "a configured model is passed through" "" "$out"
fi

echo "harness matrix: failures are explained, not crashed on"
# A repository configured for a different harness, so "generic" really has no
# command to fall back on.
nocommand="$work/nocommand"
mkdir -p "$nocommand"
"$python_bin" "$repo_root/scripts/sync_slice_pipeline_local.py" --target "$nocommand" --mode install \
  --project-name "No Command App" --project-id no-command-app --github-slug nc-org/nc-app \
  --harnesses codex >/dev/null 2>&1
out="$work/generic-missing.txt"
node "$runner" run-next --repo "$nocommand" --harness generic --dry-run > "$out" 2>&1
status=$?
if [ "$status" -eq 1 ] && grep -qi "needs a command" "$out" && ! grep -q "Traceback" "$out"; then
  report ok "generic without a command fails with an explanation"
else
  report fail "generic without a command fails with an explanation" "exit $status" "$out"
fi

out="$work/unknown.txt"
node "$runner" check --repo "$target" --harness nonsense > "$out" 2>&1
status=$?
if [ "$status" -eq 1 ] && grep -qi "unknown harness" "$out"; then
  report ok "an unknown harness id is rejected by name"
else
  report fail "an unknown harness id is rejected by name" "exit $status" "$out"
fi

out="$work/absent-binary.txt"
node "$runner" check --repo "$target" --harness claude > "$out" 2>&1
status=$?
if command -v claude >/dev/null 2>&1; then
  report ok "check with claude installed (binary present, nothing to prove)"
elif [ "$status" -eq 1 ] && grep -q "not found on PATH" "$out"; then
  report ok "an absent harness binary is a blocking check failure"
else
  report fail "an absent harness binary is a blocking check failure" "exit $status" "$out"
fi

out="$work/removed-flag.txt"
node "$runner" run-next --repo "$target" --cloud > "$out" 2>&1
status=$?
if [ "$status" -eq 1 ] && grep -q "docs/harnesses.md" "$out"; then
  report ok "removed SDK-only flags fail with a reason"
else
  report fail "removed SDK-only flags fail with a reason" "exit $status" "$out"
fi

echo "harness matrix: real runs through the stub harness"
out="$work/run.txt"
node "$runner" run-next --repo "$target" > "$out" 2>&1
status=$?
run_dir="$(ls -dt "$target"/.drake/runs/*/ 2>/dev/null | head -1)"
if [ "$status" -eq 0 ] && [ -n "$run_dir" ] && \
   "$python_bin" "$repo_root/scripts/validate_run_artifacts.py" --run "$run_dir" >/dev/null 2>&1; then
  report ok "a run leaves contract-valid artifacts (exit 0)"
else
  report fail "a run leaves contract-valid artifacts (exit 0)" "exit $status" "$out"
fi

out="$work/run-failed.txt"
STUB_HARNESS_FAIL=1 node "$runner" run-next --repo "$target" > "$out" 2>&1
status=$?
failed_dir="$(ls -dt "$target"/.drake/runs/*/ 2>/dev/null | head -1)"
if [ "$status" -eq 2 ] && "$python_bin" -c "
import json, pathlib, sys
evidence = json.loads((pathlib.Path('$failed_dir') / 'evidence.json').read_text())
sys.exit(0 if evidence['status'] == 'failure' and evidence['harness']['exit_code'] != 0 else 1)"; then
  report ok "a failing harness exits 2 and records failure evidence"
else
  report fail "a failing harness exits 2 and records failure evidence" "exit $status" "$out"
fi

echo "harness matrix: scheduling (what cron and systemd timers call)"
out="$work/cron.txt"
"$repo_root/scripts/slice-cron.sh" --repo "$target" --runner "$runner" > "$out" 2>&1
cron_status=$?
if [ "$cron_status" -eq 0 ] && grep -q "a slice ran" "$out"; then
  report ok "slice-cron runs a slice and reports exit 0"
else
  report fail "slice-cron runs a slice and reports exit 0" "exit $cron_status" "$out"
fi

if ls "$target"/.drake/logs/*.log >/dev/null 2>&1; then
  report ok "slice-cron writes one log per run under .drake/logs/"
else
  report fail "slice-cron writes one log per run under .drake/logs/"
fi

mkdir -p "$target/.drake/.slice-cron.lock"
out="$work/cron-locked.txt"
"$repo_root/scripts/slice-cron.sh" --repo "$target" --runner "$runner" > "$out" 2>&1
locked_status=$?
rmdir "$target/.drake/.slice-cron.lock" 2>/dev/null || true
if [ "$locked_status" -eq 0 ] && grep -q "skipping this tick" "$out"; then
  report ok "slice-cron refuses to overlap a run already in flight"
else
  report fail "slice-cron refuses to overlap a run already in flight" "exit $locked_status" "$out"
fi

out="$work/none.txt"
"$python_bin" - "$target" <<'PY'
import json
import pathlib
import sys

tree = pathlib.Path(sys.argv[1]) / ".docs/slice_dependency_tree.json"
data = json.loads(tree.read_text())
for row in data["slices"]:
    # Set BOTH: the selector decides runnability from `state`. This scenario used to set only
    # `status` and relied on the loader deriving state from it, which worked only while the
    # placeholder tree had no explicit state field.
    row["state"] = "done"
    row["status"] = "done"
tree.write_text(json.dumps(data, indent=2))
PY
node "$runner" run-next --repo "$target" > "$out" 2>&1
status=$?
if [ "$status" -eq 3 ] && grep -q "no runnable slice" "$out"; then
  report ok "nothing runnable exits 3 with an explanation"
else
  report fail "nothing runnable exits 3 with an explanation" "exit $status" "$out"
fi

out="$work/cron-none.txt"
"$repo_root/scripts/slice-cron.sh" --repo "$target" --runner "$runner" > "$out" 2>&1
cron_none_status=$?
if [ "$cron_none_status" -eq 3 ] && grep -q "nothing runnable (normal" "$out"; then
  report ok "slice-cron reports nothing runnable as exit 3, not a failure"
else
  report fail "slice-cron reports nothing runnable as exit 3, not a failure" "exit $cron_none_status" "$out"
fi

echo "harness matrix: legacy config from the pre-0.2 layout"
legacy="$work/legacy"
mkdir -p "$legacy"
"$python_bin" "$repo_root/scripts/sync_slice_pipeline_local.py" --target "$legacy" --mode install \
  --project-name "Legacy App" --project-id legacy-app --github-slug legacy-org/legacy-app \
  --harnesses cursor >/dev/null 2>&1
mv "$legacy/.drake/slice-pipeline.config.json" "$legacy/.cursor/slice-pipeline-local.config.json"
"$python_bin" - "$legacy" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1]) / ".cursor/slice-pipeline-local.config.json"
data = json.loads(path.read_text())
data.pop("harness", None)
path.write_text(json.dumps(data, indent=2))
PY
out="$work/legacy.txt"
node "$runner" check --repo "$legacy" > "$out" 2>&1
if grep -q "pre-0.2 location" "$out" && grep -q 'defaulting to "cursor"' "$out"; then
  report ok "a pre-0.2 config still loads, with a warning"
else
  report fail "a pre-0.2 config still loads, with a warning" "" "$out"
fi

echo
echo "harness matrix: $passed passed, $failed failed"
[ "$failed" -eq 0 ]
