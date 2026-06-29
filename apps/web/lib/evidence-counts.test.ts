import { describe, expect, it } from "vitest";

import type { DispatchSummary, RunSummary } from "@/lib/api-client";
import {
  EMPTY_EVIDENCE_COUNT,
  countForRepo,
  repoEvidenceCounts,
} from "@/lib/evidence-counts";

const runs: RunSummary[] = [
  {
    run_id: "run-1",
    repo_id: "drake",
    runtime: "cloud",
    status: "running",
    started_at: "2026-06-21T17:30:00Z",
  },
  {
    run_id: "run-2",
    repo_id: "example-app",
    runtime: "cloud",
    status: "success",
    started_at: "2026-06-21T16:00:00Z",
  },
];

const dispatches: DispatchSummary[] = [
  {
    dispatch_id: "dispatch-1",
    orchestrator_run_id: "hourly-1",
    repo_id: "drake",
    worker_id: "drake-slice-pipeline",
    slice_id: "HOSTED-ARCH-1",
    status: "accepted",
    dispatched_at: "2026-06-21T17:30:05Z",
    retry_count: 0,
  },
  {
    dispatch_id: "dispatch-2",
    orchestrator_run_id: "hourly-1",
    repo_id: "drake",
    worker_id: "drake-slice-pipeline",
    slice_id: "HOSTED-ARCH-2",
    status: "queued",
    dispatched_at: "2026-06-21T17:31:05Z",
    retry_count: 0,
  },
];

describe("repo evidence counts", () => {
  it("aggregates run and dispatch counts per repo", () => {
    const counts = repoEvidenceCounts(runs, dispatches);

    expect(counts.drake).toEqual({ runs: 1, dispatches: 2 });
    expect(counts["example-app"]).toEqual({ runs: 1, dispatches: 0 });
  });

  it("returns an empty count for repos with no evidence", () => {
    const counts = repoEvidenceCounts(runs, dispatches);

    expect(countForRepo(counts, "unknown")).toEqual(EMPTY_EVIDENCE_COUNT);
  });
});
