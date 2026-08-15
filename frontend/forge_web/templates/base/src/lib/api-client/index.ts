import type { ApiClient } from "./api-client";
import { mockClient } from "./mock-client";
import { realClient } from "./real-client";

export const apiClient: ApiClient =
  import.meta.env.VITE_API_MODE === "true" ? realClient : mockClient;

export type { ApiClient } from "./api-client";
export type { Item } from "./types";
