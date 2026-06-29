import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { useEvidenceUrlFilters } from "@/lib/use-evidence-url-filters";

function Harness() {
  const [filters, setFilters] = useEvidenceUrlFilters();

  return (
    <button
      type="button"
      onClick={() =>
        setFilters({
          repoId: "example-app",
          sliceId: "",
          status: "success",
        })
      }
    >
      {filters.repoId || "all"} / {filters.status || "all"}
    </button>
  );
}

describe("useEvidenceUrlFilters", () => {
  afterEach(() => {
    window.history.pushState(null, "", "/");
  });

  it("initializes from URL search and writes updates back to the URL", () => {
    window.history.pushState(null, "", "/runs?repo=drake&tab=evidence");
    render(<Harness />);

    expect(screen.getByRole("button")).toHaveTextContent("drake / all");

    fireEvent.click(screen.getByRole("button"));

    const params = new URLSearchParams(window.location.search);
    expect(params.get("repo")).toBe("example-app");
    expect(params.get("status")).toBe("success");
    expect(params.get("slice")).toBeNull();
    expect(params.get("tab")).toBe("evidence");
  });

  it("updates state on browser popstate", () => {
    window.history.pushState(null, "", "/dispatches?repo=drake");
    render(<Harness />);

    act(() => {
      window.history.pushState(null, "", "/dispatches?repo=example-app");
      window.dispatchEvent(new PopStateEvent("popstate"));
    });

    expect(screen.getByRole("button")).toHaveTextContent("example-app / all");
  });
});
