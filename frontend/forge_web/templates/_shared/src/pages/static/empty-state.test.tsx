import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { EmptyState } from "@/pages/static/empty-state";

describe("EmptyState", () => {
  it("renders title, description, and the action", () => {
    render(
      <EmptyState
        title="No items"
        description="Create one to get started."
        action={<button>New</button>}
      />,
    );

    expect(screen.getByText("No items")).toBeInTheDocument();
    expect(
      screen.getByText("Create one to get started."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "New" })).toBeInTheDocument();
  });

  it("renders without an action", () => {
    render(<EmptyState title="No items" description="Create one to get started." />);

    expect(screen.getByText("No items")).toBeInTheDocument();
    expect(
      screen.getByText("Create one to get started."),
    ).toBeInTheDocument();
  });
});
