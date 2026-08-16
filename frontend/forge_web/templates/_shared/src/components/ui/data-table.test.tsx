import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import type { ColumnDef } from "@tanstack/react-table";

import { DataTable } from "./data-table";

interface Fixture {
  id: string;
  name: string;
}

const columns: ColumnDef<Fixture, string>[] = [
  {
    accessorKey: "name",
    header: "Name",
  },
];

describe("DataTable", () => {
  it("renders header and row cell text for populated data", () => {
    const data: Fixture[] = [
      { id: "1", name: "First Item" },
      { id: "2", name: "Second Item" },
    ];

    render(<DataTable columns={columns} data={data} />);

    expect(screen.getByText("Name")).toBeInTheDocument();
    expect(screen.getByText("First Item")).toBeInTheDocument();
    expect(screen.getByText("Second Item")).toBeInTheDocument();
  });

  it("renders the empty state when data is empty", () => {
    render(<DataTable columns={columns} data={[]} />);

    expect(screen.getByText("No results.")).toBeInTheDocument();
  });
});
