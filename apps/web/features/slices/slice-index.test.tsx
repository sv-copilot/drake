import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  SliceIndexContent,
  SliceIndexEmpty,
  SliceIndexLoading,
  sliceTotals,
} from "@/features/slices/slice-index";
import type { RepoSummary } from "@/lib/api-client";

const repos: RepoSummary[] = [
  {
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
      ready_count: 2,
      running_count: 1,
      blocked_count: 0,
      validated_count: 3,
    },
  },
  {
    id: "blocked-app",
    github_slug: "example-org/blocked-app",
    integration_branch: "ai-dev",
    automation_enabled: true,
    readiness: {},
    repo_native_paths: {
      registry_project_id: "blocked-app",
      dependency_tree: ".docs/blocked-tree.json",
    },
    workers: [],
    slice_summary: {
      ready_count: 0,
      running_count: 0,
      blocked_count: 1,
      validated_count: 0,
    },
  },
];

describe("Slice index", () => {
  it("totals repo slice summaries", () => {
    expect(sliceTotals(repos)).toEqual({
      ready_count: 2,
      running_count: 1,
      blocked_count: 1,
      validated_count: 3,
    });
  });

  it("renders repo slice board links and source paths without mutation controls", () => {
    render(<SliceIndexContent repos={repos} />);

    expect(screen.getByText("Dependency states before unattended work.")).toBeInTheDocument();
    expect(screen.getByText("example-app")).toBeInTheDocument();
    expect(screen.getByText("blocked-app")).toBeInTheDocument();
    expect(screen.getByText("Needs review")).toBeInTheDocument();
    expect(
      screen.getByText(".docs/examples/slice_dependency_tree.example.json"),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "example-app" })).toHaveAttribute(
      "href",
      "/repos/example-app/slices",
    );
    expect(screen.getAllByRole("link", { name: "Open slice board" })[1]).toHaveAttribute(
      "href",
      "/repos/blocked-app/slices",
    );
    expect(screen.queryByRole("button", { name: /dispatch|approve/i })).toBeNull();
  });

  it("renders loading and empty states", () => {
    render(<SliceIndexLoading />);
    expect(screen.getByLabelText("Loading slice index")).toBeInTheDocument();

    render(<SliceIndexEmpty />);
    expect(screen.getByText("No repo slice boards yet.")).toBeInTheDocument();
  });
});
