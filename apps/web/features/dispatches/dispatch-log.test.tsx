import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  DispatchLogContent,
  DispatchLogEmpty,
  statusTone,
} from "@/features/dispatches/dispatch-log";
import type { DispatchSummary } from "@/lib/api-client";

const dispatches: DispatchSummary[] = [
  {
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
  },
];

describe("Dispatch log", () => {
  it("maps statuses to badge tones", () => {
    expect(statusTone("accepted")).toBe("success");
    expect(statusTone("queued")).toBe("pending");
    expect(statusTone("failed")).toBe("failed");
    expect(statusTone("unknown")).toBe("neutral");
  });

  it("renders failed dispatch errors inline without action controls", () => {
    render(<DispatchLogContent dispatches={dispatches} />);

    expect(screen.getByText("dispatch-1")).toBeInTheDocument();
    expect(screen.getByText("Webhook returned 500")).toBeInTheDocument();
    expect(
      screen.getByText("EXAMPLE_SLICE_PIPELINE_WEBHOOK_URL"),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /retry|dispatch/i })).toBeNull();
  });

  it("renders the OSS-equivalent empty state", () => {
    render(<DispatchLogEmpty />);

    expect(screen.getByText("No dispatch attempts yet.")).toBeInTheDocument();
    expect(screen.getByText(/manual webhook POST logs/)).toBeInTheDocument();
  });
});
