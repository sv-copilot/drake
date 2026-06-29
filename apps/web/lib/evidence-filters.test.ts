import { describe, expect, it } from "vitest";

import {
  evidenceFiltersFromSearch,
  evidenceSearchString,
} from "@/lib/evidence-filters";

describe("evidence filter query helpers", () => {
  it("reads evidence filters from URL search params", () => {
    expect(evidenceFiltersFromSearch("?repo=example-app&slice=SMOKE-1&status=failed")).toEqual({
      repoId: "example-app",
      sliceId: "SMOKE-1",
      status: "failed",
    });
  });

  it("writes evidence filters while preserving unrelated query params", () => {
    const search = evidenceSearchString(
      {
        repoId: "example-app",
        sliceId: "",
        status: "failed",
      },
      "?tab=evidence&slice=old",
    );

    const params = new URLSearchParams(search);
    expect(params.get("tab")).toBe("evidence");
    expect(params.get("repo")).toBe("example-app");
    expect(params.get("slice")).toBeNull();
    expect(params.get("status")).toBe("failed");
  });
});
