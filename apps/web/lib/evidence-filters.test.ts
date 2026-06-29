import { describe, expect, it } from "vitest";

import {
  evidenceFiltersFromSearch,
  evidenceSearchString,
} from "@/lib/evidence-filters";

describe("evidence filter query helpers", () => {
  it("reads evidence filters from URL search params", () => {
    expect(
      evidenceFiltersFromSearch(
        "?repo=example-app&slice=SMOKE-1&status=failed&worker=example-app-slice-pipeline",
      ),
    ).toEqual({
      repoId: "example-app",
      sliceId: "SMOKE-1",
      status: "failed",
      workerId: "example-app-slice-pipeline",
    });
  });

  it("defaults the worker facet to empty when absent", () => {
    expect(evidenceFiltersFromSearch("?repo=example-app")).toEqual({
      repoId: "example-app",
      sliceId: "",
      status: "",
      workerId: "",
    });
  });

  it("writes evidence filters while preserving unrelated query params", () => {
    const search = evidenceSearchString(
      {
        repoId: "example-app",
        sliceId: "",
        status: "failed",
        workerId: "example-app-slice-pipeline",
      },
      "?tab=evidence&slice=old",
    );

    const params = new URLSearchParams(search);
    expect(params.get("tab")).toBe("evidence");
    expect(params.get("repo")).toBe("example-app");
    expect(params.get("slice")).toBeNull();
    expect(params.get("status")).toBe("failed");
    expect(params.get("worker")).toBe("example-app-slice-pipeline");
  });

  it("clears the worker param when the facet is empty", () => {
    const search = evidenceSearchString(
      { repoId: "example-app", sliceId: "", status: "" },
      "?worker=old-worker",
    );

    expect(new URLSearchParams(search).get("worker")).toBeNull();
  });
});
