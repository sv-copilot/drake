#!/usr/bin/env bash
#
# Run one slice on a schedule.
#
#   scripts/slice-cron.sh --repo /path/to/your-repo                 # one slice, if one is ready
#   scripts/slice-cron.sh --repo . -- --dry-run                     # anything after -- goes to the runner
#
# Designed to be the thing cron and systemd timers call:
#
#   * single-flight: a lock means a slow harness run cannot overlap the next tick
#   * one log per run under .drake/logs/, plus the run artifacts under .drake/runs/
#   * the runner's exit code is propagated unchanged, so monitoring can tell
#     "nothing to do" (3) from "the harness failed" (2) from "misconfigured" (1)
#
# Exit codes: 0 ran · 1 configuration/startup error · 2 harness ran but failed · 3 nothing runnable.
#
set -uo pipefail

repo=""
runner=""
log_dir=""
runner_args=()

usage() {
  cat <<'TXT'
usage: slice-cron.sh --repo <path> [--runner <path>] [--log-dir <path>] [-- <runner args>]

  --repo <path>      repository holding .drake/slice-pipeline.config.json (required)
  --runner <path>    the slice-agent-runner CLI (default: <repo>/tools/slice-agent-runner/dist/index.js
                     or $SLICE_AGENT_RUNNER)
  --log-dir <path>   where per-run logs go (default: <repo>/.drake/logs)
  --                 everything after this is passed to the runner, e.g. --dry-run

exit codes: 0 ran · 1 configuration or startup error · 2 harness ran but failed · 3 nothing runnable
TXT
}

while [ $# -gt 0 ]; do
  case "$1" in
    --repo) repo="${2:-}"; shift 2 ;;
    --runner) runner="${2:-}"; shift 2 ;;
    --log-dir) log_dir="${2:-}"; shift 2 ;;
    --help|-h) usage; exit 0 ;;
    --) shift; runner_args=("$@"); break ;;
    *) echo "slice-cron: unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [ -z "$repo" ]; then
  echo "slice-cron: --repo is required" >&2
  usage >&2
  exit 2
fi
if [ ! -d "$repo" ]; then
  echo "slice-cron: no such repository: $repo" >&2
  exit 2
fi
repo="$(cd "$repo" && pwd)"

runner="${runner:-${SLICE_AGENT_RUNNER:-$repo/tools/slice-agent-runner/dist/index.js}}"
if [ ! -f "$runner" ]; then
  echo "slice-cron: runner not found: $runner" >&2
  echo "  build it with: npm --prefix tools/slice-agent-runner ci && npm --prefix tools/slice-agent-runner run build" >&2
  echo "  or point --runner at wherever you keep it" >&2
  exit 1
fi

log_dir="${log_dir:-$repo/.drake/logs}"
mkdir -p "$log_dir"

# Single-flight lock. mkdir is atomic everywhere, so this needs no flock and works on a
# machine with nothing installed beyond the base utilities.
lock="$repo/.drake/.slice-cron.lock"
mkdir -p "$repo/.drake"
if ! mkdir "$lock" 2>/dev/null; then
  echo "slice-cron: a previous run still holds $lock; skipping this tick (exit 0)"
  exit 0
fi
trap 'rmdir "$lock" 2>/dev/null || true' EXIT

log="$log_dir/$(date -u +%Y-%m-%dT%H-%M-%SZ).log"
node "$runner" run-next --repo "$repo" ${runner_args[@]+"${runner_args[@]}"} > "$log" 2>&1
status=$?

{
  printf 'slice-cron: %s exit=%s log=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$status" "$log"
  case "$status" in
    0) echo "slice-cron: a slice ran; evidence is under .drake/runs/" ;;
    1) echo "slice-cron: configuration or startup error - the run never started (fix before the next tick)" ;;
    2) echo "slice-cron: the harness ran but failed - inspect the evidence record and $log" ;;
    3) echo "slice-cron: nothing runnable (normal; do not alert on this)" ;;
    *) echo "slice-cron: unexpected exit code $status" ;;
  esac
} | tee -a "$log"

exit "$status"
