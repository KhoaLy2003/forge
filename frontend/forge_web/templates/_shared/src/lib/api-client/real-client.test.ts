import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { realClient } from "./real-client";

function jsonResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: vi.fn(async () => body),
  };
}

describe("realClient", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
    vi.stubEnv("VITE_API_BASE_URL", "http://test-api");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it("listItems calls fetch with the items endpoint and resolves the JSON body", async () => {
    const body = [{ id: "1", name: "A", status: "active", createdAt: "2026-01-01" }];
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse(body) as unknown as Response);

    const result = await realClient.listItems();

    expect(fetch).toHaveBeenCalledWith("http://test-api/items", expect.anything());
    expect(result).toEqual(body);
  });

  it("getItem URL-encodes the id into the path", async () => {
    const body = { id: "a b", name: "A", status: "active", createdAt: "2026-01-01" };
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse(body) as unknown as Response);

    await realClient.getItem("a b");

    expect(fetch).toHaveBeenCalledWith(
      `http://test-api/items/${encodeURIComponent("a b")}`,
      expect.anything(),
    );
  });

  it("createItem sends a POST with the JSON body and Content-Type header", async () => {
    const input = { name: "New" };
    const body = { id: "1", name: "New", status: "active", createdAt: "2026-01-01" };
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse(body) as unknown as Response);

    await realClient.createItem(input);

    expect(fetch).toHaveBeenCalledWith(
      "http://test-api/items",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(input),
        headers: expect.objectContaining({ "Content-Type": "application/json" }),
      }),
    );
  });

  it("deleteItem sends a DELETE and resolves to undefined without calling .json() on 204", async () => {
    const response = jsonResponse(undefined, 204);
    vi.mocked(fetch).mockResolvedValueOnce(response as unknown as Response);

    const result = await realClient.deleteItem("1");

    expect(fetch).toHaveBeenCalledWith(
      "http://test-api/items/1",
      expect.objectContaining({ method: "DELETE" }),
    );
    expect(result).toBeUndefined();
    expect(response.json).not.toHaveBeenCalled();
  });

  it("rejects with an error containing the status code on a non-ok response", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({}, 404) as unknown as Response);

    await expect(realClient.listItems()).rejects.toThrow(/404/);
  });
});
