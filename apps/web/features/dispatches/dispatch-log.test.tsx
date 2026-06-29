import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it } from "vitest";

import {
  DispatchLogContent,
  DispatchLogEmpty,
  dispatchFilterOptions,
  filterDispatches,
  statusTone,
} from "@/features/dispatches/dispatch-log";
import type { EvidenceFilters } from "@/lib/evidence-filters";
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
  {
    dispatch_id: "dispatch-2",
    orchestrator_run_id: "hourly-2",
    repo_id: "drake",
    worker_id: "drake-slice-pipeline",
    slice_id: "HOSTED-ARCH-1",
    adapter_type: "cursor",
    status: "accepted",
    dispatched_at: "2026-06-21T18:30:05Z",
    webhook_url_env_name: "EXAMPLE_PORTFOLIO_WEBHOOK_URL",
    chain_back: true,
    retry_count: 0,
    task_packet_id: "hourly-2/1",
  },
];

describe("Dispatch log", () => {
  it("filters dispatches and builds unique filter options", () => {
    expect(
      filterDispatches(dispatches, {
        repoId: "example-app",
        sliceId: "",
        status: "failed",
      }),
    ).toEqual([dispatches[0]]);
    expect(dispatchFilterOptions(dispatches)).toEqual({
      repoIds: ["drake", "example-app"],
      sliceIds: ["HOSTED-ARCH-1", "SMOKE-1"],
      workerIds: ["drake-slice-pipeline", "example-app-slice-pipeline"],
      statuses: ["accepted", "failed"],
    });
  });

  it("filters dispatches by worker", () => {
    expect(
      filterDispatches(dispatches, {
        repoId: "",
        sliceId: "",
        status: "",
        workerId: "drake-slice-pipeline",
      }),
    ).toEqual([dispatches[1]]);
  });

  it("maps statuses to badge tones", () => {
    expect(statusTone("accepted")).toBe("success");
    expect(statusTone("completed")).toBe("success");
    expect(statusTone("queued")).toBe("pending");
    expect(statusTone("dispatched")).toBe("pending");
    expect(statusTone("retrying")).toBe("pending");
    expect(statusTone("failed")).toBe("failed");
    expect(statusTone("cancelled")).toBe("failed");
    expect(statusTone("unknown")).toBe("neutral");
  });

  it("renders failed dispatch errors inline without action controls", () => {
    render(<DispatchLogContent dispatches={dispatches} />);

    expect(screen.getByText("dispatch-1")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "dispatch-1" })).toHaveAttribute(
      "href",
      "/dispatches/dispatch-1",
    );
    expect(screen.getByRole("link", { name: "example-app" })).toHaveAttribute(
      "href",
      "/repos/example-app",
    );
    expect(screen.getByText("Webhook returned 500")).toBeInTheDocument();
    expect(
      screen.getByText("EXAMPLE_SLICE_PIPELINE_WEBHOOK_URL"),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /retry|dispatch/i })).toBeNull();
  });

  it("renders missing webhook env as not declared and avoids webhook values", () => {
    render(
      <DispatchLogContent
        dispatches={[
          {
            ...dispatches[0],
            dispatch_id: "dispatch-2",
            webhook_url_env_name: undefined,
            error_summary: undefined,
          },
        ]}
      />,
    );

    expect(screen.getByText("not declared")).toBeInTheDocument();
    expect(screen.getByText("Env var name only")).toBeInTheDocument();
    expect(screen.queryByText(/https?:\/\//i)).toBeNull();
    expect(screen.queryByRole("button", { name: /retry|dispatch|edit/i })).toBeNull();
  });

  it("filters through visible selects and shows filtered empty state", () => {
    function Harness() {
      const [filters, setFilters] = useState<EvidenceFilters>({
        repoId: "",
        sliceId: "",
        status: "",
      });
      return (
        <DispatchLogContent
          dispatches={dispatches}
          filters={filters}
          onFiltersChange={setFilters}
        />
      );
    }

    render(<Harness />);

    fireEvent.change(screen.getByLabelText("Repo"), {
      target: { value: "drake" },
    });

    expect(screen.getByText("dispatch-2")).toBeInTheDocument();
    expect(screen.queryByText("dispatch-1")).toBeNull();

    fireEvent.change(screen.getByLabelText("Status"), {
      target: { value: "failed" },
    });

    expect(screen.getByText("No dispatches match these filters.")).toBeInTheDocument();
  });

  it("filters through the visible worker select", () => {
    function Harness() {
      const [filters, setFilters] = useState<EvidenceFilters>({
        repoId: "",
        sliceId: "",
        status: "",
        workerId: "",
      });
      return (
        <DispatchLogContent
          dispatches={dispatches}
          filters={filters}
          onFiltersChange={setFilters}
        />
      );
    }

    render(<Harness />);

    fireEvent.change(screen.getByLabelText("Worker"), {
      target: { value: "drake-slice-pipeline" },
    });

    expect(screen.getByText("dispatch-2")).toBeInTheDocument();
    expect(screen.queryByText("dispatch-1")).toBeNull();
  });

  it("renders the OSS-equivalent empty state", () => {
    render(<DispatchLogEmpty />);

    expect(screen.getByText("No dispatch attempts yet.")).toBeInTheDocument();
    expect(screen.getByText(/manual webhook POST logs/)).toBeInTheDocument();
  });
});
