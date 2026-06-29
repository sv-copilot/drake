import type { DispatchSummary, RunSummary } from "@/lib/api-client";

/**
 * Read-only correlation helpers linking dispatches and runs.
 *
 * The hosted API exposes a shared task packet identifier: a dispatch's
 * `task_packet_id` matches the `task_id` of the run it produced. We require the
 * repo to match as well so packet-id collisions never link across repos.
 */

export function runsForDispatch(
  runs: RunSummary[],
  dispatch: DispatchSummary,
): RunSummary[] {
  const packetId = dispatch.task_packet_id;
  if (!packetId) {
    return [];
  }
  return runs.filter(
    (run) => run.task_id === packetId && run.repo_id === dispatch.repo_id,
  );
}

export function dispatchesForRun(
  dispatches: DispatchSummary[],
  run: RunSummary,
): DispatchSummary[] {
  const taskId = run.task_id;
  if (!taskId) {
    return [];
  }
  return dispatches.filter(
    (dispatch) =>
      dispatch.task_packet_id === taskId && dispatch.repo_id === run.repo_id,
  );
}
