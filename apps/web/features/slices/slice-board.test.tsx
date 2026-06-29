import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  SliceBoardContent,
  groupSlices,
  hasUnresolvedGates,
  stateTone,
} from "@/features/slices/slice-board";
import type { RepoSummary, SliceSummary } from "@/lib/api-client";

const repo: RepoSummary = {
  id: "example-app",
  github_slug: "example-org/example-app",
  integration_branch: "ai-dev",
  automation_enabled: false,
  readiness: {},
  repo_native_paths: {
    registry_project_id: "example-app",
    dependency_tree: ".docs/examples/slice_dependency_tree.example.json",
  },
  workers: [],
  slice_summary: {
    ready_count: 1,
    running_count: 0,
    blocked_count: 0,
    validated_count: 0,
  },
};

const readySlice: SliceSummary = {
  slice_id: "READY-1",
  slice_number: 1,
  title: "Ready slice",
  state: "ready",
  repo_id: "example-app",
  github_slug: "example-org/example-app",
  automation_eligible: true,
  operator_gates: [],
  dependencies: [],
  repo_native_path: ".docs/slices/READY-1.md",
};

const gatedSlice: SliceSummary = {
  slice_id: "GATED-1",
  slice_number: 2,
  title: "Gated slice",
  state: "gated",
  repo_id: "example-app",
  github_slug: "example-org/example-app",
  automation_eligible: false,
  operator_gates: ["cross_repo"],
  dependencies: [1],
  repo_native_path: ".docs/slices/GATED-1.md",
};

describe("slice board gate highlighting", () => {
  it("marks gated slices as requiring operator attention", () => {
    expect(hasUnresolvedGates(gatedSlice)).toBe(true);
    expect(stateTone(gatedSlice)).toBe("gate");
    expect(hasUnresolvedGates(readySlice)).toBe(false);
    expect(stateTone(readySlice)).toBe("ready");
  });

  it("groups slices by lifecycle state", () => {
    const unknownSlice = {
      ...readySlice,
      slice_id: "UNKNOWN-1",
      state: "paused",
    };
    const grouped = groupSlices([readySlice, gatedSlice, unknownSlice]);

    expect(grouped.ready).toEqual([readySlice]);
    expect(grouped.gated).toEqual([gatedSlice]);
    expect(grouped.blocked).toEqual([unknownSlice]);
  });

  it("renders a detail panel with repo-native GitHub link", () => {
    render(<SliceBoardContent repo={repo} slices={[gatedSlice, readySlice]} />);

    expect(screen.getAllByText("GATED-1")).toHaveLength(2);
    expect(screen.getByText("Operator gates")).toBeInTheDocument();
    expect(screen.getByText("cross_repo")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open in GitHub" })).toHaveAttribute(
      "href",
      "https://github.com/example-org/example-app/blob/ai-dev/.docs/slices/GATED-1.md",
    );
    expect(screen.queryByRole("button", { name: /dispatch/i })).toBeNull();
  });

  it("updates detail selection and renders no-gate/no-dependency fallbacks", () => {
    render(<SliceBoardContent repo={repo} slices={[gatedSlice, readySlice]} />);

    fireEvent.click(screen.getByRole("button", { name: /READY-1/ }));

    expect(screen.getAllByText("READY-1")).toHaveLength(2);
    expect(screen.getByText("No unresolved operator gates.")).toBeInTheDocument();
    expect(screen.getByText("none")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open in GitHub" })).toHaveAttribute(
      "href",
      "https://github.com/example-org/example-app/blob/ai-dev/.docs/slices/READY-1.md",
    );
    expect(screen.queryByRole("button", { name: /approve|promote|dispatch/i })).toBeNull();
  });
});
