import { describe, expect, it } from "vitest";

import type { DispatchSummary, RunSummary } from "@/lib/api-client";
import {
  normalizeSort,
  sortDispatches,
  sortRuns,
} from "@/lib/evidence-sort";

const runs: RunSummary[] = [
  {
    run_id: "older",
    repo_id: "drake",
    runtime: "cloud",
    status: "success",
    started_at: "2026-06-21T16:00:00Z",
  },
  {
    run_id: "newer",
    repo_id: "drake",
    runtime: "cloud",
    status: "failure",
    started_at: "2026-06-21T18:00:00Z",
  },
];

describe("normalizeSort", () => {
  it("defaults unknown values to newest", () => {
    expect(normalizeSort(undefined)).toBe("newest");
    expect(normalizeSort("bogus")).toBe("newest");
    expect(normalizeSort("oldest")).toBe("oldest");
    expect(normalizeSort("status")).toBe("status");
  });
});

describe("sortRuns", () => {
  it("orders newest first by default and oldest first on request", () => {
    expect(sortRuns(runs, "newest").map((r) => r.run_id)).toEqual([
      "newer",
      "older",
    ]);
    expect(sortRuns(runs, "oldest").map((r) => r.run_id)).toEqual([
      "older",
      "newer",
    ]);
  });

  it("orders by status alphabetically", () => {
    expect(sortRuns(runs, "status").map((r) => r.run_id)).toEqual([
      "newer", // failure
      "older", // success
    ]);
  });

  it("does not mutate the input array", () => {
    const input = [...runs];
    sortRuns(input, "oldest");
    expect(input.map((r) => r.run_id)).toEqual(["older", "newer"]);
  });
});

describe("sortDispatches", () => {
  const dispatches: DispatchSummary[] = [
    {
      dispatch_id: "d-old",
      orchestrator_run_id: "h",
      repo_id: "drake",
      worker_id: "w",
      slice_id: "S-1",
      status: "accepted",
      dispatched_at: "2026-06-21T16:00:00Z",
      retry_count: 0,
    },
    {
      dispatch_id: "d-new",
      orchestrator_run_id: "h",
      repo_id: "drake",
      worker_id: "w",
      slice_id: "S-2",
      status: "queued",
      dispatched_at: "2026-06-21T18:00:00Z",
      retry_count: 0,
    },
  ];

  it("orders by dispatched_at", () => {
    expect(sortDispatches(dispatches, "newest").map((d) => d.dispatch_id)).toEqual([
      "d-new",
      "d-old",
    ]);
    expect(sortDispatches(dispatches, "oldest").map((d) => d.dispatch_id)).toEqual([
      "d-old",
      "d-new",
    ]);
  });
});
