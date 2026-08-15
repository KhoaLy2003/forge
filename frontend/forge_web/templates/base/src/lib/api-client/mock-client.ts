import type { ApiClient } from "./api-client";
import type { Item } from "./types";

const LATENCY_MS = 300;

function delay<T>(value: T): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), LATENCY_MS));
}

let items: Item[] = [
  {
    id: "1",
    name: "Welcome kit",
    status: "active",
    createdAt: "2026-01-05T10:00:00.000Z",
  },
  {
    id: "2",
    name: "Q1 onboarding checklist",
    status: "active",
    createdAt: "2026-02-12T09:30:00.000Z",
  },
  {
    id: "3",
    name: "Legacy migration notes",
    status: "archived",
    createdAt: "2025-11-20T14:15:00.000Z",
  },
  {
    id: "4",
    name: "Design token audit",
    status: "active",
    createdAt: "2026-03-01T08:00:00.000Z",
  },
];

function nextId(): string {
  return String(Math.max(0, ...items.map((item) => Number(item.id))) + 1);
}

export const mockClient: ApiClient = {
  async listItems() {
    return delay([...items]);
  },

  async getItem(id) {
    const item = items.find((candidate) => candidate.id === id);
    if (!item) {
      throw new Error(`Item ${id} not found`);
    }
    return delay(item);
  },

  async createItem(input) {
    const item: Item = {
      id: nextId(),
      name: input.name,
      status: "active",
      createdAt: new Date().toISOString(),
    };
    items = [item, ...items];
    return delay(item);
  },

  async updateItem(id, input) {
    const index = items.findIndex((candidate) => candidate.id === id);
    if (index === -1) {
      throw new Error(`Item ${id} not found`);
    }
    const updated: Item = { ...items[index], name: input.name, status: input.status };
    items = [...items.slice(0, index), updated, ...items.slice(index + 1)];
    return delay(updated);
  },

  async deleteItem(id) {
    items = items.filter((candidate) => candidate.id !== id);
    return delay(undefined);
  },
};
