import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ErrorView } from "@/features/errors/error-view";

describe("Error view", () => {
  it("renders a read-only recovery panel and invokes reset", () => {
    const reset = vi.fn();
    render(<ErrorView reset={reset} />);

    expect(
      screen.getByRole("heading", {
        name: "The read-only console hit an unexpected error.",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Back to portfolio" }),
    ).toHaveAttribute("href", "/portfolio");

    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(reset).toHaveBeenCalledTimes(1);

    expect(
      screen.queryByRole("button", { name: /dispatch|retry|edit|rerun/i }),
    ).toBeNull();
  });

  it("omits the reset action when no handler is provided", () => {
    render(<ErrorView />);

    expect(
      screen.queryByRole("button", { name: "Try again" }),
    ).toBeNull();
  });
});
