import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  WorkerStatusContent,
  WorkerStatusEmpty,
  workerRows,
} from "@/features/workers/worker-status";
import type { RepoSummary } from "@/lib/api-client";

const repos: RepoSummary[] = [
  {
    id: "example-app",
    github_slug: "example-org/example-app",
    integration_branch: "ai-dev",
    automation_enabled: false,
    readiness: {},
    repo_native_paths: {
      registry_project_id: "example-app",
      dependency_tree: ".docs/examples/slice_dependency_tree.example.json",
    },
    workers: [
      {
        worker_id: "example-app-slice-pipeline",
        adapter_type: "cursor",
        role: "slice_pipeline",
        enabled: false,
        primary: true,
        model_slug: "composer-2.5",
        credential_ref_names: ["GH_TOKEN"],
        webhook_env_names: {
          url: "EXAMPLE_SLICE_PIPELINE_WEBHOOK_URL",
          token: "EXAMPLE_SLICE_PIPELINE_WEBHOOK_TOKEN",
        },
      },
    ],
    slice_summary: {
      ready_count: 1,
      running_count: 0,
      blocked_count: 0,
      validated_count: 0,
    },
  },
];

describe("Worker status", () => {
  it("flattens workers by repo", () => {
    expect(workerRows(repos)).toHaveLength(1);
    expect(workerRows(repos)[0].worker.worker_id).toBe(
      "example-app-slice-pipeline",
    );
  });

  it("renders worker env var names without controls", () => {
    render(<WorkerStatusContent repos={repos} />);

    expect(screen.getByText("example-app-slice-pipeline")).toBeInTheDocument();
    expect(screen.getByText("cursor")).toBeInTheDocument();
    expect(screen.getByText("Primary")).toBeInTheDocument();
    expect(screen.getByText("Disabled")).toBeInTheDocument();
    expect(screen.getByText("GH_TOKEN")).toBeInTheDocument();
    expect(
      screen.getByText("EXAMPLE_SLICE_PIPELINE_WEBHOOK_URL"),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /enable|disable/i })).toBeNull();
  });

  it("renders an empty state when no workers are declared", () => {
    render(<WorkerStatusEmpty />);

    expect(screen.getByText("No workers configured.")).toBeInTheDocument();
  });
});
