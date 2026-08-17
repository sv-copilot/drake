import { describe, expect, it } from "vitest";

import { formatRelativeTime } from "@/lib/format-time";

const NOW = Date.parse("2026-06-21T18:00:00Z");

describe("formatRelativeTime", () => {
  it("describes sub-minute gaps as just now", () => {
    expect(formatRelativeTime("2026-06-21T17:59:30Z", NOW)).toBe("just now");
  });

  it("describes minute, hour, and day gaps", () => {
    expect(formatRelativeTime("2026-06-21T17:30:00Z", NOW)).toBe("30 minutes ago");
    expect(formatRelativeTime("2026-06-21T15:00:00Z", NOW)).toBe("3 hours ago");
    expect(formatRelativeTime("2026-06-19T18:00:00Z", NOW)).toBe("2 days ago");
  });

  it("uses singular units and coarser buckets", () => {
    expect(formatRelativeTime("2026-06-21T16:59:00Z", NOW)).toBe("1 hour ago");
    expect(formatRelativeTime("2026-05-28T18:00:00Z", NOW)).toBe("3 weeks ago");
    expect(formatRelativeTime("2026-05-12T18:00:00Z", NOW)).toBe("1 month ago");
    expect(formatRelativeTime("2025-06-21T18:00:00Z", NOW)).toBe("1 year ago");
  });

  it("describes future timestamps", () => {
    expect(formatRelativeTime("2026-06-21T20:00:00Z", NOW)).toBe("in 2 hours");
  });

  it("returns the original value when it is not a parseable date", () => {
    expect(formatRelativeTime("handoff-path-B", NOW)).toBe("handoff-path-B");
  });
});
