#!/usr/bin/env bash
#
# The from-scratch path, run inside the clean room.
#
# Every command here is a command a new user runs, in the order the README gives them.
# Nothing is preinstalled: the room has base utilities plus the toolchains the
# prerequisites section names, and no caches, no global npm packages, no site-packages.
#
set -uo pipefail

room="${1:?usage: cleanroom-run.sh <room-dir>}"
tag="${2:-v0.2.5}"
export HOME="$room/home"
export PATH="$room/bin"          # allowlist: nothing outside the room is reachable
unset PYTHONPATH PYTHONHOME VIRTUAL_ENV
export npm_config_cache="$room/home/.npm"      # start with an empty npm cache
export PIP_CACHE_DIR="$room/home/.pip"

# a fresh run directory per invocation: a re-used one makes "install" skip files and
# invalidates the before-install steps
work="$room/work/run-$(date +%s)"
mkdir -p "$work"
cd "$work" || exit 1

step() { printf '\n=== %s\n' "$1"; }
have() { printf '  %-9s %s\n' "$1" "$(command -v "$1" 2>/dev/null || echo ABSENT)"; }

step "0. what this machine has"
have git; have curl; have tar; have xz
have node; have npm; have python3
echo "  node    $(node --version 2>/dev/null)"
echo "  npm     $(npm --version 2>/dev/null)"
echo "  python  $(python3 --version 2>/dev/null)"
echo "  git     $(git --version 2>/dev/null)"
echo "  npm cache: $npm_config_cache ($(ls -A "$npm_config_cache" 2>/dev/null | wc -l) entries)"
echo "  pip cache: $PIP_CACHE_DIR ($(ls -A "$PIP_CACHE_DIR" 2>/dev/null | wc -l) entries)"
python3 -c "import jsonschema" 2>/dev/null && echo "  jsonschema: PRESENT (host leak!)" || echo "  jsonschema: absent, as it should be"

step "1. get Drake ($tag)"
start=$(date +%s)
if [ -n "${DRAKE_SOURCE:-}" ]; then
  # iteration mode: test a working tree instead of a published tag. Build outputs,
  # node_modules and venvs are excluded, so the room still starts from source only.
  drake="$work/drake-src-$(date +%s)"
  mkdir -p "$drake"
  ( cd "$DRAKE_SOURCE" && tar \
      --exclude=./node_modules --exclude=./.venv --exclude=./.next \
      --exclude=./dist --exclude=./__pycache__ --exclude=./.git \
      -cf - . ) | tar -xf - -C "$drake" || { echo "copy failed"; exit 1; }
  echo "  copied working tree in $(( $(date +%s) - start ))s"
else
  drake="$work/drake"
  git clone -q --branch "$tag" --depth 1 https://github.com/sv-copilot/drake.git "$drake" \
    || { echo "clone failed"; exit 1; }
  echo "  cloned in $(( $(date +%s) - start ))s: $(git -C "$drake" log --oneline -1)"
fi

step "2. the project's own gate"
start=$(date +%s)
cd "$drake" || exit 1
if bash scripts/ci_preflight.sh > "$work/gate.log" 2>&1; then
  echo "  ci_preflight.sh: PASSED in $(( $(date +%s) - start ))s"
else
  echo "  ci_preflight.sh: FAILED after $(( $(date +%s) - start ))s"
  tail -25 "$work/gate.log"
  exit 1
fi
grep -E "^-- |^ci preflight" "$work/gate.log" | sed 's/^/    /'
grep -E "adoption chain retest:|harness matrix: [0-9]+ passed|[0-9]+ passed in" "$work/gate.log" | tail -4 | sed 's/^/    /'

step "3. a product repository: install the pipeline"
mkdir -p "$work/my-product" && cd "$work/my-product" || exit 1
python3 "$drake/scripts/sync_slice_pipeline_local.py" \
  --target . --mode install \
  --project-name "My Product" --project-id my-product \
  --github-slug my-org/my-product \
  --validation-commands "bash scripts/ci_preflight.sh" \
  --harnesses cline > "$work/install.log" 2>&1 || { tail -20 "$work/install.log"; exit 1; }
echo "  files written: $(grep -cE '^(created|updated|ok)' "$work/install.log")"
ls -1 AGENTS.md .drake/slice-pipeline.config.json .drake/agents/slice-implementer.md 2>/dev/null | sed 's/^/    /'

step "4. the recommended configuration (copy the example)"
cp -r "$drake/examples/governed-workspace/.docs" . 2>/dev/null
cp "$drake/examples/governed-workspace/README.md" EXAMPLE-CONFIG.md
echo "  copied the example tree, backlog and slice documents"
"$drake/.venv/bin/python" "$drake/scripts/validate_slice_dependency_tree.py" --tree .docs/slice_dependency_tree.json | sed 's/^/    /'

( cd "$work/my-product" && git init -q && git add -A \
  && git -c user.name=clean-room -c user.email=clean-room@example.invalid commit -qm "install the slice pipeline" )
echo "  committed the installed bundle (a real adopter tracks it)"

step "5. fill in the config"
python3 - <<'PY'
import json, pathlib
cfg = pathlib.Path(".drake/slice-pipeline.config.json")
data = json.loads(cfg.read_text())
data["githubSlug"] = "my-org/my-product"
data["projectName"] = "My Product"
data["projectId"] = "my-product"
cfg.write_text(json.dumps(data, indent=2) + "\n")
print("  config points at", data["harness"]["id"], "with", len(data["validationCommands"]), "validation command(s)")
PY

step "6. build the runner"
cd "$drake/tools/slice-agent-runner" || exit 1
npm ci --silent > "$work/npmci.log" 2>&1 || { tail -20 "$work/npmci.log"; exit 1; }
npm run build > "$work/npmbuild.log" 2>&1 || { tail -20 "$work/npmbuild.log"; exit 1; }
echo "  runner built: $(ls dist/index.js 2>/dev/null || echo missing)"
export SLICE_AGENT_RUNNER="$drake/tools/slice-agent-runner/dist/index.js"

step "7. check the target (the harness is not installed yet - it must say so)"
cd "$work/my-product" || exit 1
node "$SLICE_AGENT_RUNNER" check --repo . > "$work/check.log" 2>&1
echo "  exit: $?"
grep -E "harness:|binary:|check:|\[fail\]" "$work/check.log" | sed 's/^/    /'

step "8. verify the wiring with the stub harness (no model, no credentials)"
node "$SLICE_AGENT_RUNNER" run-next --repo . --dry-run > "$work/dryrun.log" 2>&1
echo "  dry run exit: $? (renders the packet; launches nothing)"
node "$SLICE_AGENT_RUNNER" run-next --repo . \
  --harness generic --harness-command "bash scripts/harness_stub.sh {prompt_file}" > "$work/run.log" 2>&1
echo "  run exit: $?"
grep -E "harness:|exit:|evidence:" "$work/run.log" | sed 's/^/    /'
run_dir="$(ls -dt .drake/runs/*/ 2>/dev/null | head -1)"
"$drake/.venv/bin/python" "$drake/scripts/validate_run_artifacts.py" --run "$run_dir" | sed 's/^/    /'
python3 - "$run_dir" <<'PY'
import json, pathlib, sys
run = pathlib.Path(sys.argv[1])
evidence = json.loads((run / "evidence.json").read_text())
print("    evidence:", evidence["status"], "| changed files:", [i["path"] for i in evidence["evidence_items"]])
PY

step "9. install Cline and run a real slice"
echo "  (skipped in this room: 'npm i -g cline' needs credentials via 'cline auth')"
echo "  the command a user runs here is:"
echo "    npm i -g cline && cline auth"
echo "    node \"\$SLICE_AGENT_RUNNER\" run-next --repo .    # the configured harness"

step "done"
echo "  clean room: $room"
echo "  artifacts:  $work/my-product/.drake/runs/"
