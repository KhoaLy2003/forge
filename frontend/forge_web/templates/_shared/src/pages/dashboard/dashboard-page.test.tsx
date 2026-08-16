import { describe, expect, it, vi } from "vitest";

import { renderWithProviders, screen, userEvent } from "@/test/test-utils";
import type { Item } from "@/lib/api-client";

const { useItems, useDeleteItem, useCreateItem, useUpdateItem } = vi.hoisted(() => ({
  useItems: vi.fn(),
  useDeleteItem: vi.fn(),
  useCreateItem: vi.fn(),
  useUpdateItem: vi.fn(),
}));

vi.mock("@/lib/hooks/use-items", () => ({
  useItems,
  useDeleteItem,
  useCreateItem,
  useUpdateItem,
}));

import DashboardPage from "@/pages/dashboard/dashboard-page";

const fixtureItem: Item = {
  id: "1",
  name: "Welcome kit",
  status: "active",
  createdAt: "2026-01-05T10:00:00.000Z",
};

describe("DashboardPage", () => {
  it("renders loading skeletons while loading", () => {
    useItems.mockReturnValue({ data: undefined, isLoading: true, isError: false });
    useDeleteItem.mockReturnValue({ mutate: vi.fn() });

    const { container } = renderWithProviders(<DashboardPage />);

    expect(container.querySelectorAll(".animate-pulse").length).toBeGreaterThan(0);
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("renders the empty state when there are no items", () => {
    useItems.mockReturnValue({ data: [], isLoading: false, isError: false });
    useDeleteItem.mockReturnValue({ mutate: vi.fn() });

    renderWithProviders(<DashboardPage />);

    expect(screen.getByText("No items yet")).toBeInTheDocument();
  });

  it("renders items in the table and opens the create dialog", async () => {
    useItems.mockReturnValue({ data: [fixtureItem], isLoading: false, isError: false });
    useDeleteItem.mockReturnValue({ mutate: vi.fn() });
    useCreateItem.mockReturnValue({ mutateAsync: vi.fn(), isPending: false });
    useUpdateItem.mockReturnValue({ mutateAsync: vi.fn(), isPending: false });

    renderWithProviders(<DashboardPage />);

    expect(screen.getByText("Welcome kit")).toBeInTheDocument();

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /new item/i }));

    expect(await screen.findByText("New item")).toBeInTheDocument();
  });

  it("renders an ErrorPage when the query errors", () => {
    useItems.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error("boom"),
    });
    useDeleteItem.mockReturnValue({ mutate: vi.fn() });

    renderWithProviders(<DashboardPage />);

    expect(screen.getByText("boom")).toBeInTheDocument();
  });
});
