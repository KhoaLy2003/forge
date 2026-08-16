import { describe, expect, it } from "vitest";

import { renderWithProviders, screen } from "@/test/test-utils";

import { AppShell } from "./app-shell";

describe("AppShell", () => {
  it("renders children alongside the nav sidebar", () => {
    renderWithProviders(
      <AppShell>
        <p>Page content</p>
      </AppShell>,
    );

    expect(screen.getByText("Page content")).toBeInTheDocument();
    expect(screen.getByText("Home")).toBeInTheDocument();
  });
});
