import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  RunHistoryContent,
  filterRuns,
  runFilterOptions,
  statusTone,
} from "@/features/runs/run-history";
import type { RunSummary } from "@/lib/api-client";

const runs: RunSummary[] = [
  {
    run_id: "run-a",
    repo_id: "drake",
    slice_id: "HOSTED-ARCH-1",
    task_id: "hourly-1/15",
    runtime: "cloud",
    status: "running",
    started_at: "2026-06-21T17:30:00Z",
    model_slug: "composer-2.5",
    artifact_source: "local_automation_runs",
  },
  {
    run_id: "run-b",
    repo_id: "example-app",
    slice_id: "RS-FEATURE-1",
    task_id: "hourly-2/4",
    runtime: "cloud",
    status: "success",
    started_at: "2026-06-21T16:00:00Z",
    evidence_status: "success",
    pr_url: "https://github.com/example-org/example-app/pull/1",
  },
];

describe("Run history", () => {
  it("filters by repo, slice, and status", () => {
    expect(filterRuns(runs, { repoId: "drake", sliceId: "", status: "" })).toEqual([
      runs[0],
    ]);
    expect(
      filterRuns(runs, {
        repoId: "",
        sliceId: "RS-FEATURE-1",
        status: "success",
      }),
    ).toEqual([runs[1]]);
  });

  it("builds unique filter options", () => {
    expect(runFilterOptions(runs)).toEqual({
      repoIds: ["drake", "example-app"],
      sliceIds: ["HOSTED-ARCH-1", "RS-FEATURE-1"],
      statuses: ["running", "success"],
    });
  });

  it("maps run statuses to tones", () => {
    expect(statusTone("success")).toBe("success");
    expect(statusTone("running")).toBe("running");
    expect(statusTone("failure")).toBe("failed");
  });

  it("renders run rows without dispatch controls", () => {
    render(<RunHistoryContent runs={runs} />);

    expect(screen.getByText("run-a")).toBeInTheDocument();
    expect(screen.getAllByText("HOSTED-ARCH-1")).toHaveLength(2);
    expect(screen.getByText("local_automation_runs")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /dispatch/i })).toBeNull();
  });
});
