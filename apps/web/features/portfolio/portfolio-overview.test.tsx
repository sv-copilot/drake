import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  PortfolioEmpty,
  PortfolioLoading,
  PortfolioOverviewContent,
} from "@/features/portfolio/portfolio-overview";
import type { PortfolioSummary, RepoSummary } from "@/lib/api-client";

const portfolio: PortfolioSummary = {
  global_fanout_limit: 1,
  same_repo_max_when_others_idle: 1,
  repo_count: 1,
  automation_enabled_count: 0,
  ready_slice_count: 1,
  running_slice_count: 0,
};

const repos: RepoSummary[] = [
  {
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
      sdk_dry_run: true,
      automation_safe: true,
    },
    repo_native_paths: {
      registry_project_id: "example-app",
      slice_backlog: ".docs/slice_backlog.example.md",
      dependency_tree: ".docs/examples/slice_dependency_tree.example.json",
      agent_automations: ".docs/agent_automations.example.md",
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

describe("Portfolio overview states", () => {
  it("renders a loading skeleton", () => {
    render(<PortfolioLoading />);

    expect(screen.getByLabelText("Loading portfolio")).toBeInTheDocument();
  });

  it("renders an empty state without inventing repos", () => {
    render(<PortfolioEmpty />);

    expect(screen.getByText("No registered repos yet.")).toBeInTheDocument();
    expect(screen.queryByText("example-app")).toBeNull();
  });

  it("renders repo readiness and repo-native source details", () => {
    render(<PortfolioOverviewContent portfolio={portfolio} repos={repos} />);

    expect(screen.getByText("Registered repos")).toBeInTheDocument();
    expect(screen.getByText("example-app")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "example-app" })).toHaveAttribute(
      "href",
      "/repos/example-app",
    );
    expect(screen.getByText("example-org/example-app · ai-dev")).toBeInTheDocument();
    expect(screen.getByText("Automation off")).toBeInTheDocument();
    expect(
      screen.getByText(".docs/examples/slice_dependency_tree.example.json"),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /dispatch/i })).toBeNull();
  });

  it("surfaces per-repo evidence counts with repo-scoped quick links", () => {
    render(
      <PortfolioOverviewContent
        portfolio={portfolio}
        repos={repos}
        evidenceCounts={{ "example-app": { runs: 3, dispatches: 2 } }}
      />,
    );

    expect(screen.getByRole("link", { name: "Runs (3)" })).toHaveAttribute(
      "href",
      "/runs?repo=example-app",
    );
    expect(
      screen.getByRole("link", { name: "Dispatches (2)" }),
    ).toHaveAttribute("href", "/dispatches?repo=example-app");
  });

  it("defaults evidence counts to zero when no run/dispatch data is loaded", () => {
    render(<PortfolioOverviewContent portfolio={portfolio} repos={repos} />);

    expect(screen.getByRole("link", { name: "Runs (0)" })).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Dispatches (0)" }),
    ).toBeInTheDocument();
  });
});
