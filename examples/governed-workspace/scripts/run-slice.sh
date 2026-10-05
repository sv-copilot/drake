#!/usr/bin/env bash
#
# Run the next ready slice through the harness configured for this workspace.
#
#   ./scripts/run-slice.sh                 # run it
#   ./scripts/run-slice.sh --dry-run       # show the packet, command and prompt
#   ./scripts/run-slice.sh --harness claude
#
# To verify the wiring before installing a harness, drive the stub instead:
#
#   ./scripts/run-slice.sh --harness generic \
#     --harness-command "bash scripts/harness_stub.sh {prompt_file}"
#
set -uo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
runner="${SLICE_AGENT_RUNNER:-$repo_root/tools/slice-agent-runner/dist/index.js}"

if [ ! -f "$runner" ]; then
  echo "run-slice: build the runner first:" >&2
  echo "  npm --prefix tools/slice-agent-runner ci && npm --prefix tools/slice-agent-runner run build" >&2
  exit 1
fi

exec node "$runner" run-next --repo "$repo_root" "$@"
