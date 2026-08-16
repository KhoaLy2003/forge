import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { Skeleton } from "./skeleton";

describe("Skeleton", () => {
  it("renders", () => {
    render(<Skeleton className="h-4 w-4" data-testid="sk" />);
    expect(screen.getByTestId("sk")).toBeInTheDocument();
  });
});
