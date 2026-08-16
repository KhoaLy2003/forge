import { describe, expect, it } from "vitest";

import { mockClient } from "./mock-client";

describe("mockClient", () => {
  it("listItems resolves to an array containing the seeded items", async () => {
    const items = await mockClient.listItems();
    expect(items.length).toBeGreaterThanOrEqual(4);
  });

  it("getItem resolves the seeded 'Welcome kit' item", async () => {
    const item = await mockClient.getItem("1");
    expect(item.name).toBe("Welcome kit");
  });

  it("getItem rejects with a 'not found' error for an unknown id", async () => {
    await expect(mockClient.getItem("does-not-exist")).rejects.toThrow(/not found/i);
  });

  it("createItem adds a new active item, visible in a subsequent listItems", async () => {
    const created = await mockClient.createItem({ name: "New Thing" });
    expect(created.name).toBe("New Thing");
    expect(created.status).toBe("active");

    const items = await mockClient.listItems();
    expect(items.some((item) => item.id === created.id)).toBe(true);
  });

  it("updateItem updates the name and status of an existing item", async () => {
    const created = await mockClient.createItem({ name: "To Update" });
    const updated = await mockClient.updateItem(created.id, {
      name: "Renamed",
      status: "archived",
    });
    expect(updated.name).toBe("Renamed");
    expect(updated.status).toBe("archived");
  });

  it("deleteItem removes the item from a subsequent listItems", async () => {
    const created = await mockClient.createItem({ name: "To Delete" });
    const result = await mockClient.deleteItem(created.id);
    expect(result).toBeUndefined();

    const items = await mockClient.listItems();
    expect(items.some((item) => item.id === created.id)).toBe(false);
  });
});
