import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RelativeTime } from "@/components/relative-time";

describe("RelativeTime", () => {
  it("renders relative text while preserving the absolute ISO value", () => {
    const now = Date.parse("2026-06-21T18:00:00Z");
    render(<RelativeTime iso="2026-06-21T17:30:00Z" now={now} />);

    const node = screen.getByText("30 minutes ago");
    expect(node.tagName).toBe("TIME");
    expect(node).toHaveAttribute("dateTime", "2026-06-21T17:30:00Z");
    expect(node).toHaveAttribute("title", "2026-06-21T17:30:00Z");
  });
});
