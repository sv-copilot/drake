#!/usr/bin/env bash
#
# Drake CI preflight.
#
# EVERY check in this script is BLOCKING. A green run means the tree really
# validates, builds, and passes its tests. There is deliberately no
# `|| echo "(skipped)"` escape hatch: a check that cannot run is a failure, not
# a skip, because a gate that hides a broken build is worse than no gate.
#
# Runs on: a fresh clone (docs/getting-started.md step 4).
# Requires: python3 (>= 3.12) and npm (>= 10, node >= 22).
#
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

PYTHON="${PYTHON:-python3}"

# --- local virtualenv -------------------------------------------------------
# PEP 668 hosts (Debian/Ubuntu, Homebrew Python) refuse system-wide pip
# installs, so anything that needs a package uses a repo-local .venv instead of
# mutating the host interpreter.
ensure_venv() {
  if [ -x .venv/bin/python ]; then
    return 0
  fi
  echo "  (creating .venv — package installs stay out of the host interpreter)"
  if ! "$PYTHON" -m venv .venv; then
    echo "FAILED: could not create .venv. Install python3-venv for your platform." >&2
    return 1
  fi
  .venv/bin/python -m pip install --quiet --upgrade pip
}

# The gate's python tooling, provisioned deliberately. Taking whichever interpreter
# happens to have pytest importable produced two different environments depending on
# the host: on a fresh clone where the host lacked it, the venv was created later and
# used for the API tests without pytest's own dependencies, so the suite died on
# `ModuleNotFoundError: pygments` and read as a repo defect. Provision it here, once.
ensure_test_tools() {
  ensure_venv || return 1
  # Install with a clean PYTHONPATH. pip treats anything importable from the current
  # environment as already satisfied, so an inherited PYTHONPATH pointing at another
  # environment (a dev shell, a CI image, an IDE) makes pip skip installing pytest's
  # own dependencies into this venv; a later stage that replaces PYTHONPATH then
  # cannot import them, and the failure surfaces as an unrelated ModuleNotFoundError.
  env -u PYTHONPATH PYTHONNOUSERSITE=1 .venv/bin/python -m pip install --quiet pytest httpx jsonschema
  # Verify rather than assume: say "provisioning problem" here, where the cause is,
  # instead of letting it surface two stages later as a phantom repo defect.
  if ! env -u PYTHONPATH .venv/bin/python -c "import pytest, httpx, jsonschema, pygments" >/dev/null 2>&1; then
    echo "FAILED: the python tooling is incomplete in .venv" >&2
    echo "        This is an environment/provisioning problem, not a repo defect." >&2
    echo "        Re-run, or install it directly:" >&2
    echo "          .venv/bin/python -m pip install pytest httpx jsonschema" >&2
    return 1
  fi
}

echo "== Drake CI preflight =="

echo "-- python scripts compile"
"$PYTHON" -m py_compile scripts/*.py

echo "-- drake export scrub validation"
"$PYTHON" scripts/validate_drake_export.py --tree "$repo_root"

echo "-- example registry JSON"
"$PYTHON" -m json.tool .docs/examples/projects-registry.example.json >/dev/null
"$PYTHON" -m json.tool .docs/examples/slice_dependency_tree.example.json >/dev/null

echo "-- dependency tree example validation"
"$PYTHON" scripts/validate_slice_dependency_tree.py \
  --tree .docs/examples/slice_dependency_tree.example.json

echo "-- MCP environment profile validation"
"$PYTHON" scripts/validate_mcp_environment_profile.py

echo "-- validation_results schema fixtures"
"$PYTHON" scripts/validate_validation_results.py --file tests/fixtures/validation-results/sample-passed.json

echo "-- python tests"
ensure_test_tools
PYTHON="$repo_root/.venv/bin/python"
# Run with a clean PYTHONPATH too: the suite must pass on what this repo declares,
# not on packages that happen to be lying around in the caller's environment.
env -u PYTHONPATH "$PYTHON" -m pytest tests/ -q

echo "-- slice-agent-runner build"
npm --prefix tools/slice-agent-runner ci
npm --prefix tools/slice-agent-runner run typecheck
npm --prefix tools/slice-agent-runner run build

echo "-- adoption smoke (the documented getting-started path, on a throwaway repo)"
PYTHON="$PYTHON" bash scripts/adoption_smoke.sh

echo "-- run artifacts satisfy the contracts"
"$PYTHON" scripts/validate_run_artifacts.py --run tests/fixtures/automation-runs/stub-harness-run

echo "-- harness matrix smoke (catalogue, exit codes, legacy config)"
PYTHON="$PYTHON" bash scripts/harness_matrix_smoke.sh

if [ -f services/api/pyproject.toml ]; then
  echo "-- hosted API sketch validation"
  "$PYTHON" scripts/validate_hosted_api_sketch.py

  echo "-- hosted API tests"
  ensure_test_tools
  .venv/bin/python -m pip install --quiet -e "./services/api[dev]"
  PYTHONPATH="$repo_root/services/api/src" \
    .venv/bin/python -m pytest "$repo_root/services/api/tests" -q
fi

if [ -f apps/web/package.json ]; then
  echo "-- hosted web install"
  npm --prefix apps/web ci

  echo "-- hosted web lint and unit tests"
  npm --prefix apps/web test

  echo "-- hosted web production build"
  npm --prefix apps/web run build
fi

echo "ci preflight passed"
