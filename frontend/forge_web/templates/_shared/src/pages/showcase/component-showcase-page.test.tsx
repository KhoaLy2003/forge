import { describe, expect, it } from "vitest";

import { renderWithProviders } from "@/test/test-utils";

import ComponentShowcasePage from "./component-showcase-page";

describe("ComponentShowcasePage", () => {
  it("renders without throwing", () => {
    expect(() =>
      renderWithProviders(<ComponentShowcasePage />),
    ).not.toThrow();
  });
});
