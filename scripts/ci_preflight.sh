#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

echo "== Drake CI preflight =="

echo "-- python scripts compile"
python3 -m py_compile scripts/*.py

echo "-- drake export scrub validation"
python3 scripts/validate_drake_export.py --tree "$repo_root"

echo "-- example registry JSON"
python3 -m json.tool .docs/examples/projects-registry.example.json >/dev/null
python3 -m json.tool .docs/examples/slice_dependency_tree.example.json >/dev/null

echo "-- dependency tree example validation"
python3 scripts/validate_slice_dependency_tree.py \
  --tree .docs/examples/slice_dependency_tree.example.json

echo "-- MCP environment profile validation"
python3 scripts/validate_mcp_environment_profile.py

echo "-- validation_results schema fixtures"
python3 scripts/validate_validation_results.py --file tests/fixtures/validation-results/sample-passed.json

echo "-- export smoke tests"
python3 -c "import pytest" 2>/dev/null || python3 -m pip install --user pytest
python3 -m pytest tests/test_export_drake_public.py -q

echo "-- slice-agent-runner build"
npm --prefix tools/slice-agent-runner ci
npm --prefix tools/slice-agent-runner run typecheck
npm --prefix tools/slice-agent-runner run build

echo "ci preflight passed"
