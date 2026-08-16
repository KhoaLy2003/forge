import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { Badge } from "./badge";

describe("Badge", () => {
  it("renders its children text", () => {
    render(<Badge>Active</Badge>);
    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("renders with the primary variant without throwing", () => {
    render(<Badge variant="primary">X</Badge>);
    expect(screen.getByText("X")).toBeInTheDocument();
  });

  it("renders with the outline variant without throwing", () => {
    render(<Badge variant="outline">Y</Badge>);
    expect(screen.getByText("Y")).toBeInTheDocument();
  });
});
