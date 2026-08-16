import { describe, expect, it } from "vitest";

import { renderWithProviders } from "@/test/test-utils";
import LoadingPage from "@/pages/static/loading-page";

describe("LoadingPage", () => {
  it("renders skeleton placeholders without throwing", () => {
    const { container } = renderWithProviders(<LoadingPage />);

    expect(container.querySelectorAll(".animate-pulse").length).toBeGreaterThan(0);
  });
});
