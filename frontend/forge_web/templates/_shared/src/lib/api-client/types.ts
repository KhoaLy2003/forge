export interface Item {
  id: string;
  name: string;
  status: "active" | "archived";
  createdAt: string;
}
