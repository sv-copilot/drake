import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useEvidenceUrlFilters } from "@/lib/use-evidence-url-filters";

const pushMock = vi.fn();
let pathname = "/runs";
let searchParams = new URLSearchParams();

vi.mock("next/navigation", () => ({
  usePathname: () => pathname,
  useRouter: () => ({ push: pushMock }),
  useSearchParams: () => searchParams,
}));

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
  beforeEach(() => {
    pushMock.mockClear();
    pathname = "/runs";
    searchParams = new URLSearchParams();
  });

  it("initializes from Next search params and writes updates through the router", () => {
    searchParams = new URLSearchParams("repo=drake&tab=evidence");
    render(<Harness />);

    expect(screen.getByRole("button")).toHaveTextContent("drake / all");

    fireEvent.click(screen.getByRole("button"));

    expect(pushMock).toHaveBeenCalledWith(
      "/runs?repo=example-app&tab=evidence&status=success",
      { scroll: false },
    );
    const params = new URLSearchParams(pushMock.mock.calls[0][0].split("?")[1]);
    expect(params.get("repo")).toBe("example-app");
    expect(params.get("status")).toBe("success");
    expect(params.get("slice")).toBeNull();
    expect(params.get("tab")).toBe("evidence");
  });

  it("reflects changed search params after route updates", () => {
    searchParams = new URLSearchParams("repo=drake");
    const { rerender } = render(<Harness />);

    act(() => {
      pathname = "/dispatches";
      searchParams = new URLSearchParams("repo=example-app");
      rerender(<Harness />);
    });

    expect(screen.getByRole("button")).toHaveTextContent("example-app / all");
  });
});
