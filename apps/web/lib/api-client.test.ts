import { afterEach, describe, expect, it, vi } from "vitest";

import {
  apiGet,
  apiUrl,
  fetchDispatch,
  fetchRepo,
  fetchRepoSlices,
  fetchRun,
  getApiBaseUrl,
} from "@/lib/api-client";

describe("api client", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("uses the configured API base URL and Accept header", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "https://api.example.test");
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ ok: true }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await apiGet("/health");

    expect(getApiBaseUrl()).toBe("https://api.example.test");
    expect(fetchMock).toHaveBeenCalledWith("https://api.example.test/health", {
      headers: expect.any(Headers),
    });
    expect(fetchMock.mock.calls[0][1].headers.get("Accept")).toBe(
      "application/json",
    );
  });

  it("throws on non-OK responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 503,
      }),
    );

    await expect(apiGet("/health")).rejects.toThrow(
      "API request failed: 503 /health",
    );
  });

  it("normalizes base URLs, paths, and request headers", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "https://api.example.test///");
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ ok: true }),
    });
    vi.stubGlobal("fetch", fetchMock);

    expect(apiUrl("health")).toBe("https://api.example.test/health");
    await apiGet("health", {
      headers: new Headers({
        "x-trace-id": "trace-1",
      }),
    });

    expect(fetchMock).toHaveBeenCalledWith("https://api.example.test/health", {
      headers: expect.any(Headers),
    });
    expect(fetchMock.mock.calls[0][1].headers.get("Accept")).toBe(
      "application/json",
    );
    expect(fetchMock.mock.calls[0][1].headers.get("x-trace-id")).toBe("trace-1");
  });

  it("encodes path identifiers before requesting resource details", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "https://api.example.test");
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({}),
    });
    vi.stubGlobal("fetch", fetchMock);

    await fetchRepo("org/repo");
    await fetchRepoSlices("org/repo");
    await fetchRun("2026/06/21 run");
    await fetchDispatch("dispatch/run 1");

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "https://api.example.test/api/v1/repos/org%2Frepo",
      expect.any(Object),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "https://api.example.test/api/v1/repos/org%2Frepo/slices",
      expect.any(Object),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      "https://api.example.test/api/v1/runs/2026%2F06%2F21%20run",
      expect.any(Object),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      4,
      "https://api.example.test/api/v1/dispatches/dispatch%2Frun%201",
      expect.any(Object),
    );
  });
});
