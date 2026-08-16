import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";

import { Toaster } from "./sonner";

describe("Toaster", () => {
  it("renders without throwing", () => {
    expect(() => render(<Toaster />)).not.toThrow();
  });
});
