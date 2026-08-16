import { createElement, type ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    listItems: vi.fn(),
    getItem: vi.fn(),
    createItem: vi.fn(),
    updateItem: vi.fn(),
    deleteItem: vi.fn(),
  },
}));

import { apiClient } from "@/lib/api-client";
import { useCreateItem, useDeleteItem, useItems, useUpdateItem } from "./use-items";

function wrapper({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return createElement(QueryClientProvider, { client: queryClient }, children);
}

describe("useItems", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("resolves to the data returned by apiClient.listItems", async () => {
    const fixture = [{ id: "1", name: "A", status: "active" as const, createdAt: "2026-01-01" }];
    vi.mocked(apiClient.listItems).mockResolvedValueOnce(fixture);

    const { result } = renderHook(() => useItems(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(fixture);
  });
});

describe("useCreateItem", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls apiClient.createItem with the mutate input", async () => {
    const created = { id: "1", name: "X", status: "active" as const, createdAt: "2026-01-01" };
    vi.mocked(apiClient.createItem).mockResolvedValueOnce(created);

    const { result } = renderHook(() => useCreateItem(), { wrapper });

    result.current.mutate({ name: "X" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.createItem).toHaveBeenCalledWith({ name: "X" });
  });
});

describe("useUpdateItem", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls apiClient.updateItem with the mutate input", async () => {
    const updated = { id: "1", name: "Renamed", status: "archived" as const, createdAt: "2026-01-01" };
    vi.mocked(apiClient.updateItem).mockResolvedValueOnce(updated);

    const { result } = renderHook(() => useUpdateItem(), { wrapper });

    result.current.mutate({ id: "1", input: { name: "Renamed", status: "archived" } });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.updateItem).toHaveBeenCalledWith("1", { name: "Renamed", status: "archived" });
  });
});

describe("useDeleteItem", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls apiClient.deleteItem with the mutate input", async () => {
    vi.mocked(apiClient.deleteItem).mockResolvedValueOnce(undefined);

    const { result } = renderHook(() => useDeleteItem(), { wrapper });

    result.current.mutate("1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.deleteItem).toHaveBeenCalledWith("1");
  });
});
