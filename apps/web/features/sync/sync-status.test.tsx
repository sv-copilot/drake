import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  SyncStatusContent,
  SyncStatusLoading,
  sourceMode,
} from "@/features/sync/sync-status";
import type { SyncStatusSummary } from "@/lib/api-client";

const emptyStatus: SyncStatusSummary = {
  status: "empty",
  last_synced_at: undefined,
  stale_after_seconds: 300,
  is_stale: true,
  project_count: 0,
  dependency_tree_count: 0,
  files: [],
};

const syncedStatus: SyncStatusSummary = {
  status: "ok",
  last_synced_at: "2026-06-29T18:00:00Z",
  stale_after_seconds: 300,
  is_stale: false,
  project_count: 1,
  dependency_tree_count: 1,
  files: [
    {
      repo: "example-org/example-portfolio",
      ref: "ai-dev",
      path: ".docs/projects-registry.json",
      sha: "abc123",
      source: "github_contents",
    },
  ],
};

describe("Sync status", () => {
  it("detects source modes", () => {
    expect(sourceMode(emptyStatus)).toBe("empty");
    expect(
      sourceMode({
        ...syncedStatus,
        files: [{ ...syncedStatus.files[0], source: "example_fixture" }],
      }),
    ).toBe("fixture fallback");
    expect(sourceMode(syncedStatus)).toBe("synced cache");
  });

  it("renders synced cache details without secrets", () => {
    render(<SyncStatusContent status={syncedStatus} />);

    expect(screen.getByText("Registry cache and source file freshness.")).toBeInTheDocument();
    expect(screen.getByText("synced cache")).toBeInTheDocument();
    expect(screen.getByText("Fresh")).toBeInTheDocument();
    expect(screen.getByText(".docs/projects-registry.json")).toBeInTheDocument();
    expect(screen.getByText("abc123")).toBeInTheDocument();
    expect(screen.queryByText(/https?:\/\//i)).toBeNull();
  });

  it("renders empty and loading states", () => {
    render(<SyncStatusContent status={emptyStatus} />);

    expect(screen.getAllByText("empty")).toHaveLength(2);
    expect(screen.getByText(/Last synced:\s+not synced yet/)).toBeInTheDocument();
    expect(screen.getByText(/No files cached yet/)).toBeInTheDocument();

    render(<SyncStatusLoading />);
    expect(screen.getByLabelText("Loading sync status")).toBeInTheDocument();
  });
});
