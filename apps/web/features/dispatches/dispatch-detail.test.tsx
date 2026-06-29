import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  DispatchDetailContent,
  DispatchDetailError,
  DispatchDetailLoading,
} from "@/features/dispatches/dispatch-detail";
import type { DispatchSummary, RunSummary } from "@/lib/api-client";

const dispatch: DispatchSummary = {
  dispatch_id: "dispatch-1",
  orchestrator_run_id: "hourly-1",
  repo_id: "example-app",
  worker_id: "example-app-slice-pipeline",
  slice_id: "SMOKE-1",
  adapter_type: "cursor",
  status: "failed",
  dispatched_at: "2026-06-21T17:30:05Z",
  webhook_url_env_name: "EXAMPLE_SLICE_PIPELINE_WEBHOOK_URL",
  chain_back: true,
  retry_count: 1,
  task_packet_id: "hourly-1/1",
  error_summary: "Webhook returned 500",
};

describe("Dispatch detail", () => {
  it("renders dispatch provenance without webhook values or action controls", () => {
    render(<DispatchDetailContent dispatch={dispatch} />);

    expect(screen.getByText("dispatch-1")).toBeInTheDocument();
    expect(screen.getByText("example-app")).toBeInTheDocument();
    expect(screen.getByText("SMOKE-1")).toBeInTheDocument();
    expect(screen.getByText("EXAMPLE_SLICE_PIPELINE_WEBHOOK_URL")).toBeInTheDocument();
    expect(screen.getByText("Webhook returned 500")).toBeInTheDocument();
    expect(screen.queryByText(/https?:\/\//i)).toBeNull();
    expect(screen.queryByRole("button", { name: /retry|dispatch|edit/i })).toBeNull();

    expect(screen.getByRole("link", { name: "example-app" })).toHaveAttribute(
      "href",
      "/repos/example-app",
    );
    expect(screen.getByRole("link", { name: "SMOKE-1" })).toHaveAttribute(
      "href",
      "/repos/example-app/slices",
    );
    expect(screen.getByText("No correlated runs.")).toBeInTheDocument();
  });

  it("links correlated runs by shared task packet", () => {
    const run: RunSummary = {
      run_id: "run-7",
      repo_id: "example-app",
      slice_id: "SMOKE-1",
      task_id: "hourly-1/1",
      runtime: "cloud",
      status: "success",
      started_at: "2026-06-21T17:30:00Z",
    };

    render(<DispatchDetailContent dispatch={dispatch} relatedRuns={[run]} />);

    expect(
      screen.getByRole("link", { name: "run-7 · success" }),
    ).toHaveAttribute("href", "/runs/run-7");
  });

  it("renders loading and error states", () => {
    render(<DispatchDetailLoading />);
    expect(screen.getByLabelText("Loading dispatch detail")).toBeInTheDocument();

    render(<DispatchDetailError dispatchId="missing" />);
    expect(screen.getByText("Could not load missing.")).toBeInTheDocument();
  });
});
