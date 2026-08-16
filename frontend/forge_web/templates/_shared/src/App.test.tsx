import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

{% if include_data_fetching %}
const { useItems, useDeleteItem } = vi.hoisted(() => ({
  useItems: vi.fn(),
  useDeleteItem: vi.fn(),
}));

vi.mock("@/lib/hooks/use-items", () => ({
  useItems,
  useDeleteItem,
  useCreateItem: vi.fn(),
  useUpdateItem: vi.fn(),
}));
{% endif %}

// App.tsx creates its `createBrowserRouter` router once at module-evaluation
// time, reading the initial location from `window.location` at that moment.
// To exercise a different starting route per test, push the new URL first
// and then force a fresh module evaluation (and therefore a fresh router)
// via `vi.resetModules()` + a dynamic re-import, rather than re-rendering a
// cached `App` whose router singleton would never see the new location.
async function renderAt(path: string) {
  window.history.pushState({}, "", path);
  vi.resetModules();
  const { default: App } = await import("@/App");
  return render(<App />);
}

describe("App routing", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    window.history.pushState({}, "", "/");
  });

  it("renders the landing page at /", async () => {
    await renderAt("/");

    expect(screen.getByText("Project structure")).toBeInTheDocument();
  });

  it("renders the component showcase page at /components", async () => {
    await expect(renderAt("/components")).resolves.toBeDefined();
  });

  it("renders the not-found page at /static/not-found", async () => {
    await renderAt("/static/not-found");

    expect(screen.getByText("Page not found")).toBeInTheDocument();
  });

  it("falls back to the not-found page for an unmatched route", async () => {
    await renderAt("/totally-bogus");

    expect(screen.getByText("Page not found")).toBeInTheDocument();
  });

{% if include_data_fetching %}
  it("renders the dashboard page at /dashboard", async () => {
    useItems.mockReturnValue({ data: [], isLoading: false, isError: false });
    useDeleteItem.mockReturnValue({ mutate: vi.fn() });

    await renderAt("/dashboard");

    expect(screen.getByText("Items")).toBeInTheDocument();
  });
{% else %}
  it("falls back to the not-found page at /dashboard (minimal template has no dashboard route)", async () => {
    await renderAt("/dashboard");

    expect(screen.getByText("Page not found")).toBeInTheDocument();
  });
{% endif %}
});
