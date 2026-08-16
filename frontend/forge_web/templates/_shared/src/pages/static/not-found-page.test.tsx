import { describe, expect, it } from "vitest";

import { renderWithProviders, screen } from "@/test/test-utils";
import NotFoundPage from "@/pages/static/not-found-page";

describe("NotFoundPage", () => {
  it("renders the not-found message and a link back home", () => {
    renderWithProviders(<NotFoundPage />);

    expect(screen.getByText("Page not found")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to home" })).toHaveAttribute(
      "href",
      "/",
    );
  });
});
