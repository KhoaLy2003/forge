import type { ApiClient } from "./api-client";
import type { Item } from "./types";

function baseUrl(): string {
  return import.meta.env.VITE_API_BASE_URL;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${baseUrl()}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    throw new Error(`Request to ${path} failed with status ${response.status}`);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export const realClient: ApiClient = {
  listItems() {
    return request<Item[]>("/items");
  },

  getItem(id) {
    return request<Item>(`/items/${encodeURIComponent(id)}`);
  },

  createItem(input) {
    return request<Item>("/items", {
      method: "POST",
      body: JSON.stringify(input),
    });
  },

  updateItem(id, input) {
    return request<Item>(`/items/${encodeURIComponent(id)}`, {
      method: "PUT",
      body: JSON.stringify(input),
    });
  },

  deleteItem(id) {
    return request<void>(`/items/${encodeURIComponent(id)}`, { method: "DELETE" });
  },
};
