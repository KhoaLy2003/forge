import type { Item } from "./types";

export interface ApiClient {
  listItems(): Promise<Item[]>;
  getItem(id: string): Promise<Item>;
  createItem(input: { name: string }): Promise<Item>;
  updateItem(id: string, input: { name: string; status: Item["status"] }): Promise<Item>;
  deleteItem(id: string): Promise<void>;
}
