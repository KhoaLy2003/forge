import type { ReactElement } from "react";
import { render, type RenderResult } from "@testing-library/react";
{% if include_data_fetching %}
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
{% endif %}
import { MemoryRouter } from "react-router-dom";

export function renderWithProviders(
  ui: ReactElement,
  options: { route?: string } = {},
): RenderResult {
{% if include_data_fetching %}
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[options.route ?? "/"]}>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
{% else %}
  return render(
    <MemoryRouter initialEntries={[options.route ?? "/"]}>{ui}</MemoryRouter>,
  );
{% endif %}
}

export { screen, within } from "@testing-library/react";
export { default as userEvent } from "@testing-library/user-event";
