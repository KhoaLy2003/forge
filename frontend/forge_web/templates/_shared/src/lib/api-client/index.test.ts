import { afterEach, describe, expect, it, vi } from "vitest";

describe("apiClient", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it("resolves to the mock client when VITE_API_MODE is not \"true\"", async () => {
    vi.stubEnv("VITE_API_MODE", "false");
    const { apiClient } = await import("./index");
    const { mockClient } = await import("./mock-client");
    expect(apiClient).toBe(mockClient);
  });

  it("resolves to the real client when VITE_API_MODE is \"true\"", async () => {
    vi.stubEnv("VITE_API_MODE", "true");
    const { apiClient } = await import("./index");
    const { realClient } = await import("./real-client");
    expect(apiClient).toBe(realClient);
  });
});
