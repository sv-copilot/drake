import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  WorkerDetailContent,
  WorkerDetailNotFound,
} from "@/features/workers/worker-detail";
import type {
  DispatchSummary,
  RepoSummary,
  WorkerSummary,
} from "@/lib/api-client";

const repo: RepoSummary = {
  id: "example-app",
  github_slug: "example-org/example-app",
  integration_branch: "ai-dev",
  automation_enabled: true,
  readiness: {},
  repo_native_paths: {
    registry_project_id: "example-app",
    dependency_tree: ".docs/examples/slice_dependency_tree.example.json",
  },
  workers: [],
  slice_summary: {
    ready_count: 0,
    running_count: 0,
    blocked_count: 0,
    validated_count: 0,
  },
};

const worker: WorkerSummary = {
  worker_id: "example-app-slice-pipeline",
  adapter_type: "cursor",
  role: "slice_pipeline",
  enabled: true,
  primary: true,
  model_slug: "composer-2.5",
  credential_ref_names: ["GH_TOKEN"],
  webhook_env_names: {
    url: "EXAMPLE_SLICE_PIPELINE_WEBHOOK_URL",
  },
};

const dispatch: DispatchSummary = {
  dispatch_id: "dispatch-20260621-002",
  orchestrator_run_id: "hourly-1",
  repo_id: "example-app",
  worker_id: "example-app-slice-pipeline",
  slice_id: "RS-SMOKE-2",
  status: "queued",
  dispatched_at: "2026-06-21T17:30:06Z",
  retry_count: 0,
};

describe("Worker detail", () => {
  it("renders provenance, env names, and dispatch history without controls", () => {
    render(
      <WorkerDetailContent repo={repo} worker={worker} dispatches={[dispatch]} />,
    );

    expect(
      screen.getByRole("heading", { name: "example-app-slice-pipeline" }),
    ).toBeInTheDocument();
    expect(screen.getByText("EXAMPLE_SLICE_PIPELINE_WEBHOOK_URL")).toBeInTheDocument();
    expect(screen.getByText("GH_TOKEN")).toBeInTheDocument();
    expect(
      screen.getByRole("link", {
        name: /dispatch-20260621-002 · RS-SMOKE-2 · queued/,
      }),
    ).toHaveAttribute("href", "/dispatches/dispatch-20260621-002");
    expect(screen.getByRole("link", { name: "Open dispatch log" })).toHaveAttribute(
      "href",
      "/dispatches?repo=example-app&worker=example-app-slice-pipeline",
    );
    expect(screen.getByRole("link", { name: "Back to example-app" })).toHaveAttribute(
      "href",
      "/repos/example-app",
    );
    expect(screen.queryByText(/https?:\/\//i)).toBeNull();
    expect(
      screen.queryByRole("button", { name: /dispatch|retry|edit|enable|disable/i }),
    ).toBeNull();
  });

  it("renders an empty dispatch-history state", () => {
    render(<WorkerDetailContent repo={repo} worker={worker} dispatches={[]} />);

    expect(
      screen.getByText("No dispatches recorded for this worker."),
    ).toBeInTheDocument();
  });

  it("renders a not-found state for an unknown worker", () => {
    render(
      <WorkerDetailNotFound repoId="example-app" workerId="ghost-worker" />,
    );

    expect(
      screen.getByText("No worker ghost-worker on example-app."),
    ).toBeInTheDocument();
  });
});
