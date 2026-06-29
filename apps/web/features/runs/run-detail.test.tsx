import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RunDetailContent } from "@/features/runs/run-detail";
import type { DispatchSummary, RunSummary } from "@/lib/api-client";

describe("Run detail", () => {
  it("renders provenance and external PR link", () => {
    const run: RunSummary = {
      run_id: "run-1",
      repo_id: "example-app",
      slice_id: "RS-FEATURE-1",
      task_id: "hourly-2/4",
      runtime: "cloud",
      status: "success",
      started_at: "2026-06-21T16:00:00Z",
      completed_at: "2026-06-21T16:15:00Z",
      model_slug: "composer-2.5",
      artifact_source: "local_automation_runs",
      repo_native_artifact_path: ".cursor/automation-runs/run-1.json",
      evidence_status: "success",
      pr_url: "https://github.com/example-org/example-app/pull/1",
      handoff_path: ".docs/handoffs/run-1.md",
    };

    render(<RunDetailContent run={run} />);

    expect(screen.getByRole("heading", { name: "run-1" })).toBeInTheDocument();
    expect(screen.getByText(".cursor/automation-runs/run-1.json")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open PR" })).toHaveAttribute(
      "href",
      run.pr_url,
    );
    expect(
      screen.getByRole("link", { name: "Repository: example-app" }),
    ).toHaveAttribute("href", "/repos/example-app");
    expect(
      screen.getByRole("link", { name: "Slice board: RS-FEATURE-1" }),
    ).toHaveAttribute("href", "/repos/example-app/slices");
    expect(
      screen.getByRole("link", { name: "Dispatches for this slice" }),
    ).toHaveAttribute("href", "/dispatches?repo=example-app&slice=RS-FEATURE-1");
    expect(screen.getByText("No correlated dispatches.")).toBeInTheDocument();
  });

  it("links correlated dispatches by shared task packet", () => {
    const run: RunSummary = {
      run_id: "run-3",
      repo_id: "drake",
      slice_id: "HOSTED-ARCH-1",
      task_id: "hourly-1/15",
      runtime: "cloud",
      status: "running",
      started_at: "2026-06-21T17:30:00Z",
    };
    const dispatch: DispatchSummary = {
      dispatch_id: "dispatch-9",
      orchestrator_run_id: "hourly-1",
      repo_id: "drake",
      worker_id: "drake-slice-pipeline",
      slice_id: "HOSTED-ARCH-1",
      status: "accepted",
      dispatched_at: "2026-06-21T17:30:05Z",
      retry_count: 0,
      task_packet_id: "hourly-1/15",
    };

    render(<RunDetailContent run={run} relatedDispatches={[dispatch]} />);

    expect(
      screen.getByRole("link", { name: "dispatch-9 · accepted" }),
    ).toHaveAttribute("href", "/dispatches/dispatch-9");
    expect(
      screen.queryByRole("button", { name: /dispatch|retry|edit|rerun/i }),
    ).toBeNull();
  });

  it("renders sparse runs as read-only provenance without mutation controls", () => {
    const run: RunSummary = {
      run_id: "run-2",
      repo_id: "drake",
      runtime: "local",
      status: "pending",
      started_at: "2026-06-21T18:00:00Z",
    };

    render(<RunDetailContent run={run} />);

    expect(
      screen.getByRole("link", { name: "Repository: drake" }),
    ).toHaveAttribute("href", "/repos/drake");
    expect(screen.getByText("unknown")).toBeInTheDocument();
    expect(screen.getAllByText("pending")).toHaveLength(2);
    expect(screen.getAllByText("not declared")).toHaveLength(3);
    expect(screen.getByText("not uploaded")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Open PR" })).toBeNull();
    expect(screen.queryByRole("button", { name: /dispatch|retry|edit|rerun/i })).toBeNull();
  });
});
