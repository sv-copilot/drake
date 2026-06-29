import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  RepoDetailContent,
  RepoDetailError,
  RepoDetailLoading,
} from "@/features/repos/repo-detail";
import type { RepoSummary } from "@/lib/api-client";

const repo: RepoSummary = {
  id: "example-app",
  github_slug: "example-org/example-app",
  integration_branch: "ai-dev",
  automation_enabled: false,
  priority: 1,
  readiness: {
    bootstrap_alignment: true,
    ci_green: true,
    smoke_slice_ready: true,
    worker_manual_test: false,
  },
  repo_native_paths: {
    registry_project_id: "example-app",
    slice_backlog: ".docs/slice_backlog.example.md",
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
        dispatch: "EXAMPLE_SLICE_PIPELINE_WEBHOOK_URL",
      },
    },
  ],
  slice_summary: {
    ready_count: 1,
    running_count: 0,
    blocked_count: 0,
    validated_count: 0,
  },
};

describe("Repo detail", () => {
  it("renders readiness, workers, sources, and read-only evidence links", () => {
    render(<RepoDetailContent repo={repo} />);

    expect(
      screen.getByRole("heading", { name: "example-app" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Automation off")).toBeInTheDocument();
    expect(screen.getByText("worker manual test")).toBeInTheDocument();
    expect(screen.getByText("example-app-slice-pipeline")).toBeInTheDocument();
    expect(screen.getByText("EXAMPLE_SLICE_PIPELINE_WEBHOOK_URL")).toBeInTheDocument();
    expect(screen.getByText("GH_TOKEN")).toBeInTheDocument();
    expect(
      screen.getByText(".docs/examples/slice_dependency_tree.example.json"),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open slice board" })).toHaveAttribute(
      "href",
      "/repos/example-app/slices",
    );
    expect(screen.getByRole("link", { name: "Run history" })).toHaveAttribute(
      "href",
      "/runs?repo=example-app",
    );
    expect(screen.getByRole("link", { name: "Dispatch log" })).toHaveAttribute(
      "href",
      "/dispatches?repo=example-app",
    );
    expect(screen.getByRole("link", { name: "Workers" })).toHaveAttribute(
      "href",
      "/workers?repo=example-app",
    );
    expect(screen.queryByText(/https?:\/\//i)).toBeNull();
    expect(screen.queryByRole("button", { name: /dispatch|edit|enable/i })).toBeNull();
  });

  it("renders loading and error states", () => {
    render(<RepoDetailLoading />);
    expect(screen.getByLabelText("Loading repo detail")).toBeInTheDocument();

    render(<RepoDetailError repoId="missing" />);
    expect(screen.getByText("Could not load missing.")).toBeInTheDocument();
  });
});
