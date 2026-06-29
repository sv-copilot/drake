import { describe, expect, it } from "vitest";

import type { DispatchSummary, RunSummary } from "@/lib/api-client";
import { dispatchesForRun, runsForDispatch } from "@/lib/evidence-correlation";

const dispatch: DispatchSummary = {
  dispatch_id: "dispatch-1",
  orchestrator_run_id: "hourly-1",
  repo_id: "drake",
  worker_id: "drake-slice-pipeline",
  slice_id: "HOSTED-ARCH-1",
  status: "accepted",
  dispatched_at: "2026-06-21T17:30:05Z",
  retry_count: 0,
  task_packet_id: "hourly-1/15-f7a2",
};

const run: RunSummary = {
  run_id: "run-1",
  repo_id: "drake",
  slice_id: "HOSTED-ARCH-1",
  task_id: "hourly-1/15-f7a2",
  runtime: "cloud",
  status: "running",
  started_at: "2026-06-21T17:30:00Z",
};

describe("evidence correlation", () => {
  it("correlates a dispatch to runs sharing the task packet and repo", () => {
    expect(runsForDispatch([run], dispatch)).toEqual([run]);
    expect(dispatchesForRun([dispatch], run)).toEqual([dispatch]);
  });

  it("returns nothing when the task packet identifier is absent", () => {
    const dispatchNoPacket = { ...dispatch, task_packet_id: undefined };
    const runNoTask = { ...run, task_id: undefined };

    expect(runsForDispatch([run], dispatchNoPacket)).toEqual([]);
    expect(dispatchesForRun([dispatch], runNoTask)).toEqual([]);
  });

  it("excludes matches from a different repo to avoid cross-repo linking", () => {
    const otherRepoRun = { ...run, repo_id: "example-app" };
    const otherRepoDispatch = { ...dispatch, repo_id: "example-app" };

    expect(runsForDispatch([otherRepoRun], dispatch)).toEqual([]);
    expect(dispatchesForRun([otherRepoDispatch], run)).toEqual([]);
  });
});
