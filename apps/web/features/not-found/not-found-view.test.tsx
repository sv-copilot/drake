import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { NotFoundView } from "@/features/not-found/not-found-view";

describe("Not found view", () => {
  it("renders a read-only message with navigation back into the console", () => {
    render(<NotFoundView />);

    expect(
      screen.getByRole("heading", {
        name: "This page is not part of the read-only console.",
      }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Portfolio" })).toHaveAttribute(
      "href",
      "/portfolio",
    );
    expect(screen.getByRole("link", { name: "Workers" })).toHaveAttribute(
      "href",
      "/workers",
    );
    expect(screen.queryByRole("button")).toBeNull();
  });
});
