import { describe, expect, it } from "vitest";

import { renderWithProviders, screen } from "@/test/test-utils";

import LandingPage from "./landing-page";

describe("LandingPage", () => {
  it("renders the project structure and static pages sections", () => {
    renderWithProviders(<LandingPage />);

    expect(
      screen.getByRole("heading", { name: "Project structure" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Static pages" }),
    ).toBeInTheDocument();
  });
});
