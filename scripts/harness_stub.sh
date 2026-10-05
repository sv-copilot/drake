#!/usr/bin/env bash
# A harness that does nothing clever.
#
# It exists so an adopter can prove the wiring works — selection, task packet,
# prompt rendering, harness invocation, evidence capture — without credentials,
# a network call, or a model. Point the runner at it:
#
#   slice-agent-runner run-next --repo . \
#     --harness generic --harness-command "bash scripts/harness_stub.sh {prompt_file}"
#
# It records what it received in .drake/stub-harness-output.txt and exits 0.
# Set STUB_HARNESS_FAIL=1 to make it exit non-zero, so you can watch the runner
# record a failed run instead.
set -euo pipefail

prompt_source="${1:-}"
if [[ -n "$prompt_source" && -f "$prompt_source" ]]; then
  prompt="$(cat "$prompt_source")"
else
  prompt="${prompt_source}"
fi

mkdir -p .drake
{
  echo "stub harness ran at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "prompt bytes: ${#prompt}"
  echo "working directory: $(pwd)"
} > .drake/stub-harness-output.txt

echo "stub harness: wrote .drake/stub-harness-output.txt (${#prompt} prompt bytes)"

if [[ "${STUB_HARNESS_FAIL:-0}" == "1" ]]; then
  echo "stub harness: failing because STUB_HARNESS_FAIL=1" >&2
  exit 3
fi

exit 0
