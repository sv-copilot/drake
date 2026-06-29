import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useSortUrlParam } from "@/lib/use-sort-url-param";

const pushMock = vi.fn();
let pathname = "/runs";
let searchParams = new URLSearchParams();

vi.mock("next/navigation", () => ({
  usePathname: () => pathname,
  useRouter: () => ({ push: pushMock }),
  useSearchParams: () => searchParams,
}));

function Harness({ next }: { next: "oldest" | "newest" }) {
  const [sort, setSort] = useSortUrlParam();
  return (
    <button type="button" onClick={() => setSort(next)}>
      {sort}
    </button>
  );
}

describe("useSortUrlParam", () => {
  beforeEach(() => {
    pushMock.mockClear();
    pathname = "/runs";
    searchParams = new URLSearchParams();
  });

  it("reads the sort param and writes non-default values while preserving others", () => {
    searchParams = new URLSearchParams("repo=drake");
    render(<Harness next="oldest" />);

    expect(screen.getByRole("button")).toHaveTextContent("newest");

    fireEvent.click(screen.getByRole("button"));

    expect(pushMock).toHaveBeenCalledWith("/runs?repo=drake&sort=oldest", {
      scroll: false,
    });
  });

  it("removes the sort param when resetting to the default", () => {
    searchParams = new URLSearchParams("repo=drake&sort=oldest");
    render(<Harness next="newest" />);

    expect(screen.getByRole("button")).toHaveTextContent("oldest");

    fireEvent.click(screen.getByRole("button"));

    expect(pushMock).toHaveBeenCalledWith("/runs?repo=drake", { scroll: false });
  });
});
