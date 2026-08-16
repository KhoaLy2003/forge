import { describe, expect, it, vi } from "vitest";
import { waitFor } from "@testing-library/react";

import { renderWithProviders, screen, userEvent } from "@/test/test-utils";
import type { Item } from "@/lib/api-client";

const { useCreateItem, useUpdateItem } = vi.hoisted(() => ({
  useCreateItem: vi.fn(),
  useUpdateItem: vi.fn(),
}));

vi.mock("@/lib/hooks/use-items", () => ({
  useCreateItem,
  useUpdateItem,
  useItems: vi.fn(),
  useDeleteItem: vi.fn(),
}));

import { ItemForm } from "@/pages/dashboard/item-form";

const fixtureItem: Item = {
  id: "1",
  name: "Welcome kit",
  status: "active",
  createdAt: "2026-01-05T10:00:00.000Z",
};

describe("ItemForm", () => {
  it("submits a create request with the typed name", async () => {
    const mutateAsync = vi.fn().mockResolvedValue(undefined);
    useCreateItem.mockReturnValue({ mutateAsync, isPending: false });
    useUpdateItem.mockReturnValue({ mutateAsync: vi.fn(), isPending: false });
    const onSuccess = vi.fn();

    renderWithProviders(<ItemForm onSuccess={onSuccess} />);

    expect(screen.getByRole("button", { name: "Create item" })).toBeInTheDocument();

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Name"), "New Thing");
    await user.click(screen.getByRole("button", { name: "Create item" }));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith({ name: "New Thing" });
    });
    expect(onSuccess).toHaveBeenCalled();
  });

  it("renders in edit mode with pre-filled values", () => {
    useCreateItem.mockReturnValue({ mutateAsync: vi.fn(), isPending: false });
    useUpdateItem.mockReturnValue({ mutateAsync: vi.fn(), isPending: false });

    renderWithProviders(<ItemForm item={fixtureItem} onSuccess={vi.fn()} />);

    expect(screen.getByRole("button", { name: "Save changes" })).toBeInTheDocument();
    expect(screen.getByLabelText("Name")).toHaveValue(fixtureItem.name);
  });
});
