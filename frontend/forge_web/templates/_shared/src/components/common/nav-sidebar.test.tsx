import { describe, expect, it } from "vitest";

import { renderWithProviders, screen } from "@/test/test-utils";

import { NavSidebar } from "./nav-sidebar";

describe("NavSidebar", () => {
  it("renders the always-present nav items", () => {
    renderWithProviders(<NavSidebar />);

    expect(screen.getByText("Home")).toBeInTheDocument();
    expect(screen.getByText("Components")).toBeInTheDocument();
  });

  it("highlights the active link", () => {
    renderWithProviders(<NavSidebar />, { route: "/components" });

    expect(screen.getByText("Components").closest("a")).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByText("Home").closest("a")).not.toHaveAttribute(
      "aria-current",
      "page",
    );
  });

{% if include_data_fetching %}
  it("renders the Dashboard nav item when data fetching is enabled", () => {
    renderWithProviders(<NavSidebar />);

    expect(screen.getByText("Dashboard")).toBeInTheDocument();
  });
{% else %}
  it("does not render the Dashboard nav item when data fetching is disabled", () => {
    renderWithProviders(<NavSidebar />);

    expect(screen.queryByText("Dashboard")).toBeNull();
  });
{% endif %}
});
