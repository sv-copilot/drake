import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RunDetailContent } from "@/features/runs/run-detail";
import type { RunSummary } from "@/lib/api-client";

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
  });
});
