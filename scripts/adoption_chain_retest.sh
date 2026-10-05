#!/usr/bin/env bash
#
# Adoption chain retest — rehearse the path a stranger takes, against a published tag.
#
# The gate and the smokes prove the repository works. This proves the *chain* works:
# clone the released artifact, run its gate, then walk the documented adoption path
# in a throwaway product repo and check every promise the docs make.
#
# Two phases, because a full run is longer than a foreground command:
#
#   env -u PYTHONPATH bash scripts/adoption_chain_retest.sh <tag> gate
#   #   cold clone + the gate (and the smokes) on it
#   RETEST_WORK=<dir from the line above> RETEST_CLONE=<dir> \
#     env -u PYTHONPATH bash scripts/adoption_chain_retest.sh <tag> chain
#   #   documented install flow, one install per harness, the run chain (exit 0/2/3),
#   #   the upgrade path, and a pre-0.2 config
#
# `env -u PYTHONPATH` reproduces a stranger's shell. An inherited PYTHONPATH makes pip
# treat packages from another environment as already satisfied, so the repo-local venv
# can end up incomplete and the failure surfaces in an unrelated stage.
#
# No credentials, no model call, no vendor CLI: the only harness executed is the stub.
# Every claim printed comes from an exit code or a file on disk.
#
# Stages:
#   0  published release + cold clone of the tag
#   1  the gate, on the fresh clone (its first documented command)
#   2  the documented install flow, verbatim: check -> install -> check
#   3  install variants, one per harness, plus a multi-harness install
#   4  the run chain: exit 0 + contract-valid artifacts, exit 2, exit 3
#   5  upgrade path: managed files refresh, adopter files survive
#   6  pre-0.2 config still loads
#
set -uo pipefail

python_bin="${PYTHON:-python3}"
tag="${1:-$(gh release view --json tagName -q .tagName 2>/dev/null || echo v0.2.1)}"
phase="${2:-all}"          # all | gate | chain
work="${RETEST_WORK:-$(mktemp -d)}"
if [ "$phase" = "chain" ]; then
  # The chain phase needs a repository to install into and drive. Default to the tree
  # this script lives in, so CI can rehearse the chain on every push without cloning a
  # tag first; the gate phase always clones a published tag.
  clone="${RETEST_CLONE:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
else
  clone="${RETEST_CLONE:-$work/drake}"
fi
passed=0
failed=0

report() { # report <ok|fail> <label> [detail]
  if [ "$1" = "ok" ]; then
    passed=$((passed + 1)); printf '  ok   %s\n' "$2"
  else
    failed=$((failed + 1)); printf '  FAIL %s\n' "$2"; [ -n "${3:-}" ] && printf '       %s\n' "$3"
  fi
}

echo "phase: $phase   tag: $tag   work: $work"
if [ "$phase" != "chain" ]; then
echo "=== stage 0: the published artifact ==="
if command -v gh >/dev/null 2>&1; then
  gh release view "$tag" --json tagName,name,isDraft,publishedAt \
    -q '"release \(.tagName) — \(.name) — draft=\(.isDraft) — published \(.publishedAt)"' 2>/dev/null \
  || echo "no published release metadata for $tag (gh unavailable or release not created yet)"
fi
git clone -q --branch "$tag" --depth 1 https://github.com/sv-copilot/drake.git "$clone" 2>&1 | tail -2
if [ -d "$clone/.git" ]; then
  report ok "cold clone of tag $tag ($(git -C "$clone" log --oneline -1 --format=%h))"
else
  report fail "cold clone of tag $tag"; exit 1
fi
[ -f "$clone/tools/slice-agent-runner/package.json" ] && report ok "runner source present" || report fail "runner source present"
if grep -rq "@cursor/sdk" "$clone/tools/slice-agent-runner/src" 2>/dev/null; then
  report fail "runner source is free of the vendor SDK"
else
  report ok "runner source is free of the vendor SDK"
fi

echo
echo "=== stage 1: the gate, as a stranger runs it first ==="
( cd "$clone" && bash scripts/ci_preflight.sh ) > "$work/gate.txt" 2>&1
gate_exit=$?
stages=$(grep -c '^-- ' "$work/gate.txt")
if [ "$gate_exit" -eq 0 ] && grep -q "ci preflight passed" "$work/gate.txt"; then
  report ok "ci_preflight.sh passes ($stages stages)"
else
  report fail "ci_preflight.sh passes" "exit $gate_exit"; tail -20 "$work/gate.txt"
fi
# Count-agnostic on purpose: this assertion used to hardcode "14 passed" and broke the moment a
# scenario was added, failing the verification of a perfectly good release. Assert the floor and
# zero failures, never the exact number.
matrix_summary="$(grep -oE 'harness matrix: [0-9]+ passed, [0-9]+ failed' "$work/gate.txt" | tail -1)"
matrix_passed="$(printf '%s' "$matrix_summary" | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+')"
matrix_failed="$(printf '%s' "$matrix_summary" | grep -oE '[0-9]+ failed' | grep -oE '[0-9]+')"
if [ -n "$matrix_passed" ] && [ "$matrix_failed" = "0" ] && [ "$matrix_passed" -ge 14 ]; then
  report ok "harness matrix smoke inside the gate: ${matrix_passed} passed, 0 failed"
else
  report fail "harness matrix smoke inside the gate" "${matrix_summary:-no summary line in the gate output}"
fi
grep -q "adoption smoke passed" "$work/gate.txt" \
  && report ok "adoption smoke passes inside the gate" \
  || report fail "adoption smoke passes inside the gate"
if [ -z "$(git -C "$clone" status --porcelain)" ]; then
  report ok "the gate leaves the clone's tracked tree clean"
else
  report fail "the gate leaves the clone's tracked tree clean" "$(git -C "$clone" status --porcelain | head -3)"
fi
fi  # end phase != chain

runner="$clone/tools/slice-agent-runner/dist/index.js"
[ -f "$runner" ] && report ok "the runner is built at $runner" || { report fail "the runner is built"; exit 1; }

if [ "$phase" = "gate" ]; then
  echo
  echo "gate phase complete: $passed passed, $failed failed"
  echo "RESUME_WITH: RETEST_WORK=$work RETEST_CLONE=$clone bash $0 $tag chain"
  exit "$failed"
fi

install_flags=(--project-name "Retest App" --project-id retest-app --github-slug retest-org/retest-app
  --validation-commands "bash scripts/ci_preflight.sh")

echo
echo "=== stage 2: the documented install flow (check -> install -> check) ==="
app="$work/retest-app"
mkdir -p "$app"
set +e
"$python_bin" "$clone/scripts/sync_slice_pipeline_local.py" --target "$app" --mode check "${install_flags[@]}" --harnesses generic > "$work/pre-check.txt" 2>&1
pre_exit=$?
set +e
[ "$pre_exit" -eq 1 ] && report ok "check before install reports the missing bundle (exit 1)" \
  || report fail "check before install reports the missing bundle" "exit $pre_exit"

set +e
"$python_bin" "$clone/scripts/sync_slice_pipeline_local.py" --target "$app" --mode install "${install_flags[@]}" \
  --harnesses generic --harness-command "bash scripts/harness_stub.sh {prompt_file}" > "$work/install.txt" 2>&1
install_exit=$?
"$python_bin" "$clone/scripts/sync_slice_pipeline_local.py" --target "$app" --mode check "${install_flags[@]}" --harnesses generic > "$work/post-check.txt" 2>&1
post_exit=$?
set +e
[ "$install_exit" -eq 0 ] && report ok "install exits 0" || { report fail "install exits 0" "exit $install_exit"; tail -5 "$work/install.txt"; }
[ "$post_exit" -eq 0 ] && report ok "check after install reports the target complete (exit 0)" \
  || { report fail "check after install reports the target complete" "exit $post_exit"; tail -5 "$work/post-check.txt"; }
stale_count=$(grep -c "^stale" "$work/post-check.txt" || true)
[ "$stale_count" -eq 0 ] && report ok "no file is reported stale right after a fresh install" \
  || report fail "no file is reported stale right after a fresh install" "$stale_count stale"
missing_required=""
for required in AGENTS.md .drake/slice-pipeline.config.json .drake/agents/slice-implementer.md \
                .drake/runs/.gitignore scripts/harness_stub.sh scripts/select_next_automation_slice.py; do
  [ -e "$app/$required" ] || missing_required="$missing_required $required"
done
[ -z "$missing_required" ] && report ok "the installed bundle contains every runner-required file" \
  || report fail "the installed bundle contains every runner-required file" "missing:$missing_required"

echo
echo "=== stage 3: install variants (one per harness, then a multi-harness install) ==="
check_variant() { # check_variant <id> <expect claude|cursor|both>
  local id="$1" expect="$2"
  local dir="$work/variant-$id"
  mkdir -p "$dir"
  "$python_bin" "$clone/scripts/sync_slice_pipeline_local.py" --target "$dir" --mode install "${install_flags[@]}" \
    --harnesses "$id" >/dev/null 2>&1
  local primary
  primary=$("$python_bin" -c "import json;print(json.load(open('$dir/.drake/slice-pipeline.config.json'))['harness']['id'])")
  [ "$primary" = "$id" ] || { report fail "install for $id records it as the primary harness" "got $primary"; return; }

  case "$id" in
    claude)
      [ -f "$dir/CLAUDE.md" ] && [ -f "$dir/.claude/agents/slice-implementer.md" ] \
        && [ ! -d "$dir/.cursor" ] && report ok "claude install: CLAUDE.md + .claude/agents, no .cursor" \
        || report fail "claude install: CLAUDE.md + .claude/agents, no .cursor" ;;
    cursor)
      [ -d "$dir/.cursor/agents" ] && [ -f "$dir/.cursor/hooks.json" ] && [ ! -d "$dir/.claude" ] \
        && report ok "cursor install: .cursor agents + hooks, no .claude" \
        || report fail "cursor install: .cursor agents + hooks, no .claude" ;;
    codex)
      [ -f "$dir/AGENTS.md" ] && [ ! -d "$dir/.cursor" ] && [ ! -d "$dir/.claude" ] \
        && report ok "codex install: AGENTS.md only" \
        || report fail "codex install: AGENTS.md only" ;;
    aider)
      [ -f "$dir/AGENTS.md" ] && [ ! -d "$dir/.cursor" ] && [ ! -d "$dir/.claude" ] \
        && report ok "aider install: AGENTS.md only" \
        || report fail "aider install: AGENTS.md only" ;;
  esac

  # check behaviour: a harness whose binary is absent must fail loudly and by name.
  set +e
  node "$runner" check --repo "$dir" > "$work/variant-$id-check.txt" 2>&1
  local check_exit=$?
  set +e
  if [ "$id" = "generic" ]; then
    [ "$check_exit" -eq 1 ] && grep -q "needs harness.command" "$work/variant-$id-check.txt" \
      && report ok "generic install without a command: check blocks and says why" \
      || report fail "generic install without a command: check blocks and says why" "exit $check_exit"
  elif command -v "$id" >/dev/null 2>&1; then
    report ok "$id check (binary present)"
  else
    [ "$check_exit" -eq 1 ] && grep -q "not found on PATH" "$work/variant-$id-check.txt" \
      && report ok "$id install without the binary: check blocks and says why" \
      || report fail "$id install without the binary: check blocks and says why" "exit $check_exit"
  fi
}
for id in claude codex cursor aider generic; do check_variant "$id" "$id"; done

multi="$work/variant-multi"
mkdir -p "$multi"
"$python_bin" "$clone/scripts/sync_slice_pipeline_local.py" --target "$multi" --mode install "${install_flags[@]}" \
  --harnesses claude,cursor,codex >/dev/null 2>&1
if [ -f "$multi/CLAUDE.md" ] && [ -d "$multi/.cursor/agents" ] && [ -f "$multi/AGENTS.md" ]; then
  primary=$("$python_bin" -c "import json;print(json.load(open('$multi/.drake/slice-pipeline.config.json'))['harness']['id'])")
  [ "$primary" = "claude" ] && report ok "multi-harness install writes every selected view (primary=first id)" \
    || report fail "multi-harness install writes every selected view" "primary=$primary"
else
  report fail "multi-harness install writes every selected view"
fi
if "$python_bin" "$clone/scripts/sync_slice_pipeline_local.py" --target "$multi" --mode install "${install_flags[@]}" \
     --harnesses claude,nonsense > "$work/bad-harness.txt" 2>&1; then
  report fail "an unknown harness id is rejected by the installer"
else
  grep -q "unknown harness" "$work/bad-harness.txt" \
    && report ok "an unknown harness id is rejected by the installer" \
    || report fail "an unknown harness id is rejected by the installer" "no explanation"
fi

echo
echo "=== stage 4: the run chain on the installed target ==="
( cd "$app" && git init -q && git add -A && git -c user.name=retest -c user.email=retest@example.invalid commit -qm "install bundle" )
# The fixture tree the installer places is a placeholder; give the selector a ready slice.
"$python_bin" - "$app" <<'PY'
import json, pathlib, sys
tree = pathlib.Path(sys.argv[1]) / ".docs/slice_dependency_tree.json"
data = json.loads(tree.read_text())
data["slices"][0]["status"] = "ready"
data["slices"][0]["automation_eligible"] = True
tree.write_text(json.dumps(data, indent=2))
PY
( cd "$app" && git add -A && git -c user.name=retest -c user.email=retest@example.invalid commit -qm "ready slice" )

set +e
node "$runner" check --repo "$app" > "$work/run-check.txt" 2>&1
check_exit=$?
set +e
[ "$check_exit" -eq 0 ] && grep -q "check: passed" "$work/run-check.txt" \
  && report ok "runner check passes on the installed target" \
  || { report fail "runner check passes on the installed target" "exit $check_exit"; cat "$work/run-check.txt"; }

set +e
node "$runner" run-next --repo "$app" --dry-run > "$work/dry.txt" 2>&1
dry_exit=$?
set +e
[ "$dry_exit" -eq 0 ] && grep -q '"target_slice_id"' "$work/dry.txt" \
  && report ok "dry run renders the task packet without launching anything" \
  || report fail "dry run renders the task packet without launching anything" "exit $dry_exit"

set +e
node "$runner" run-next --repo "$app" > "$work/run.txt" 2>&1
run_exit=$?
set +e
run_dir="$(ls -dt "$app"/.drake/runs/*/ 2>/dev/null | head -1)"
if [ "$run_exit" -eq 0 ] && [ -n "$run_dir" ] && grep -q "stub harness: wrote" "$work/run.txt"; then
  report ok "a real run through the stub harness exits 0"
else
  report fail "a real run through the stub harness exits 0" "exit $run_exit"; tail -6 "$work/run.txt"
fi
if [ -n "$run_dir" ] && "$python_bin" "$clone/scripts/validate_run_artifacts.py" --run "$run_dir" > "$work/artifacts.txt" 2>&1; then
  report ok "the run's packet and evidence satisfy the published schemas"
else
  report fail "the run's packet and evidence satisfy the published schemas" "$(tail -3 "${work}/artifacts.txt" 2>/dev/null)"
fi
if [ -n "$run_dir" ]; then
  "$python_bin" - "$run_dir" <<'PY' && report ok "evidence names the file the harness changed" || report fail "evidence names the file the harness changed"
import json, pathlib, sys
run = pathlib.Path(sys.argv[1])
ev = json.loads((run / "evidence.json").read_text())
assert ev["status"] == "success", ev["status"]
assert ev["harness"]["exit_code"] == 0
assert any("stub-harness-output.txt" in i["path"] for i in ev["evidence_items"]), ev["evidence_items"]
assert (run / "task-packet.json").is_file() and (run / "prompt.txt").is_file()
PY
else
  report fail "evidence names the file the harness changed"
fi

set +e
STUB_HARNESS_FAIL=1 node "$runner" run-next --repo "$app" > "$work/run-fail.txt" 2>&1
fail_exit=$?
set +e
fail_dir="$(ls -dt "$app"/.drake/runs/*/ 2>/dev/null | head -1)"
if [ "$fail_exit" -eq 2 ] && [ -n "$fail_dir" ] && "$python_bin" -c "
import json,pathlib,sys
ev=json.loads((pathlib.Path('$fail_dir')/'evidence.json').read_text())
sys.exit(0 if ev['status']=='failure' and ev['harness']['exit_code']!=0 else 1)"; then
  report ok "a failing harness exits 2 and records failure evidence"
else
  report fail "a failing harness exits 2 and records failure evidence" "exit $fail_exit"
fi

"$python_bin" - "$app" <<'PY'
import json, pathlib, sys
tree = pathlib.Path(sys.argv[1]) / ".docs/slice_dependency_tree.json"
data = json.loads(tree.read_text())
for row in data["slices"]:
    row["status"] = "done"
tree.write_text(json.dumps(data, indent=2))
PY
set +e
node "$runner" run-next --repo "$app" > "$work/run-none.txt" 2>&1
none_exit=$?
set +e
[ "$none_exit" -eq 3 ] && grep -q "no runnable slice" "$work/run-none.txt" \
  && report ok "nothing runnable exits 3 with an explanation" \
  || report fail "nothing runnable exits 3 with an explanation" "exit $none_exit"

echo
echo "=== stage 5: upgrade path (re-install over an existing install) ==="
selector="$app/scripts/select_next_automation_slice.py"
printf '# stale local copy\n' > "$selector"
printf '# my own contract\n' > "$app/AGENTS.md"
"$python_bin" "$clone/scripts/sync_slice_pipeline_local.py" --target "$app" --mode install "${install_flags[@]}" \
  --harnesses generic --harness-command "bash scripts/harness_stub.sh {prompt_file}" > "$work/reinstall.txt" 2>&1
# install exits 2 when it skipped a file it did not own, which is the documented
# behaviour for a repo where the adopter has edited AGENTS.md.
if diff -q "$selector" "$clone/scripts/select_next_automation_slice.py" >/dev/null 2>&1; then
  report ok "re-install refreshes framework-owned tooling"
else
  report fail "re-install refreshes framework-owned tooling" "the stale selector survived"
fi
if [ "$(cat "$app/AGENTS.md")" = "# my own contract" ]; then
  report ok "re-install leaves adopter-owned files alone"
else
  report fail "re-install leaves adopter-owned files alone" "$(head -1 "$app/AGENTS.md")"
fi

echo
echo "=== stage 6: a pre-0.2 config still loads ==="
legacy="$work/legacy"
mkdir -p "$legacy"
"$python_bin" "$clone/scripts/sync_slice_pipeline_local.py" --target "$legacy" --mode install "${install_flags[@]}" \
  --harnesses cursor >/dev/null 2>&1
mv "$legacy/.drake/slice-pipeline.config.json" "$legacy/.cursor/slice-pipeline-local.config.json"
"$python_bin" - "$legacy" <<'PY'
import json, pathlib, sys
path = pathlib.Path(sys.argv[1]) / ".cursor/slice-pipeline-local.config.json"
data = json.loads(path.read_text()); data.pop("harness", None)
path.write_text(json.dumps(data, indent=2))
PY
node "$runner" check --repo "$legacy" > "$work/legacy.txt" 2>&1
if grep -q "pre-0.2 location" "$work/legacy.txt" && grep -q 'defaulting to "cursor"' "$work/legacy.txt"; then
  report ok "the old config location still loads, with a warning naming the new one"
else
  report fail "the old config location still loads, with a warning naming the new one"
fi

echo
echo "adoption chain retest: $passed passed, $failed failed"
echo "artifacts kept in $work"
[ "$failed" -eq 0 ]
