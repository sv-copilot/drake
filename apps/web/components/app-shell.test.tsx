import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AppShell } from "@/components/app-shell";

vi.mock("next/navigation", () => ({
  usePathname: () => "/slices",
}));

describe("AppShell", () => {
  it("renders the hosted operations navigation without dispatch controls", () => {
    render(
      <AppShell>
        <h2>Portfolio content</h2>
      </AppShell>,
    );

    expect(screen.getAllByText("Hosted operations")).toHaveLength(2);
    expect(screen.getByRole("link", { name: /Portfolio/ })).toHaveAttribute(
      "href",
      "/portfolio",
    );
    expect(screen.getByRole("link", { name: /Slices/ })).toHaveAttribute(
      "href",
      "/slices",
    );
    expect(screen.getByRole("link", { name: /Slices/ })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("link", { name: /Runs/ })).toHaveAttribute(
      "href",
      "/runs",
    );
    expect(screen.getByRole("link", { name: /Sync/ })).toHaveAttribute(
      "href",
      "/sync",
    );
    expect(screen.getByRole("link", { name: /Workers/ })).toHaveAttribute(
      "href",
      "/workers",
    );
    expect(screen.getByRole("link", { name: /Dispatches/ })).toHaveAttribute(
      "href",
      "/dispatches",
    );
    expect(screen.queryByRole("button", { name: /dispatch/i })).toBeNull();
  });
});
