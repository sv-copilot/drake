import { fireEvent, render, screen, within } from "@testing-library/react";
import { useState } from "react";
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
    expect(
      runFilterOptions([
        ...runs,
        {
          run_id: "run-c",
          repo_id: "drake",
          runtime: "cloud",
          status: "success",
          started_at: "2026-06-21T18:00:00Z",
        },
      ]),
    ).toEqual({
      repoIds: ["drake", "example-app"],
      sliceIds: ["HOSTED-ARCH-1", "RS-FEATURE-1"],
      statuses: ["running", "success"],
    });
  });

  it("maps run statuses to tones", () => {
    expect(statusTone("success")).toBe("success");
    expect(statusTone("running")).toBe("running");
    expect(statusTone("pending")).toBe("running");
    expect(statusTone("failure")).toBe("failed");
    expect(statusTone("partial")).toBe("failed");
    expect(statusTone("blocked")).toBe("failed");
    expect(statusTone("cancelled")).toBe("failed");
    expect(statusTone("mystery")).toBe("neutral");
  });

  it("renders run rows without dispatch controls", () => {
    render(<RunHistoryContent runs={runs} />);

    expect(screen.getByText("run-a")).toBeInTheDocument();
    expect(screen.getAllByText("HOSTED-ARCH-1")).toHaveLength(2);
    expect(screen.getByText("local_automation_runs")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "drake" })).toHaveAttribute(
      "href",
      "/repos/drake",
    );
    expect(screen.queryByRole("button", { name: /dispatch/i })).toBeNull();
  });

  it("filters through the visible status select and shows filtered empty state", () => {
    function Harness() {
      const [filters, setFilters] = useState({
        repoId: "",
        sliceId: "",
        status: "",
      });
      return (
        <RunHistoryContent
          runs={runs}
          filters={filters}
          onFiltersChange={setFilters}
        />
      );
    }

    render(<Harness />);

    fireEvent.change(screen.getByLabelText("Status"), {
      target: { value: "success" },
    });

    expect(screen.getByText("run-b")).toBeInTheDocument();
    expect(screen.queryByText("run-a")).toBeNull();

    fireEvent.change(screen.getByLabelText("Repo"), {
      target: { value: "drake" },
    });

    expect(screen.getByText("No runs match these filters.")).toBeInTheDocument();
  });

  it("encodes run links and renders fallback values for sparse runs", () => {
    render(
      <RunHistoryContent
        runs={[
          {
            run_id: "run/with spaces",
            repo_id: "drake",
            runtime: "local",
            status: "pending",
            started_at: "2026-06-21T18:00:00Z",
          },
        ]}
      />,
    );

    const row = screen.getByText("run/with spaces").closest("article");
    expect(row).not.toBeNull();
    expect(screen.getByRole("link", { name: "run/with spaces" })).toHaveAttribute(
      "href",
      "/runs/run%2Fwith%20spaces",
    );
    expect(within(row as HTMLElement).getByText("no slice")).toBeInTheDocument();
    expect(row).toHaveTextContent("local · unknown model");
    expect(within(row as HTMLElement).getByText("not uploaded")).toBeInTheDocument();
  });
});
