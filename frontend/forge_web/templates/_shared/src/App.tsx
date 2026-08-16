import { createBrowserRouter, RouterProvider } from "react-router-dom";
{% if include_data_fetching %}
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
{% endif %}

import { AppShell } from "@/components/common/app-shell";
import { Toaster } from "@/components/ui/sonner";
import { EmptyState } from "@/pages/static/empty-state";
import LandingPage from "@/pages/landing/landing-page";
{% if include_data_fetching %}
import DashboardPage from "@/pages/dashboard/dashboard-page";
{% endif %}
import ComponentShowcasePage from "@/pages/showcase/component-showcase-page";
import ErrorPage from "@/pages/static/error-page";
import LoadingPage from "@/pages/static/loading-page";
import NotFoundPage from "@/pages/static/not-found-page";

{% if include_data_fetching %}
const queryClient = new QueryClient();
{% endif %}

const router = createBrowserRouter([
  {
    path: "/",
    element: (
      <AppShell>
        <LandingPage />
      </AppShell>
    ),
    errorElement: <ErrorPage />,
  },
{% if include_data_fetching %}
  {
    path: "/dashboard",
    element: (
      <AppShell>
        <DashboardPage />
      </AppShell>
    ),
    errorElement: <ErrorPage />,
  },
{% endif %}
  {
    path: "/components",
    element: (
      <AppShell>
        <ComponentShowcasePage />
      </AppShell>
    ),
    errorElement: <ErrorPage />,
  },
  {
    path: "/static/not-found",
    element: <NotFoundPage />,
  },
  {
    path: "/static/error",
    element: (
      <ErrorPage message="Something broke on purpose, for preview." />
    ),
  },
  {
    path: "/static/loading",
    element: <LoadingPage />,
  },
  {
    path: "/static/empty-state",
    element: (
      <AppShell>
        <div className="max-w-[36rem]">
          <EmptyState
            title="No items yet"
            description="Create your first item to get started."
          />
        </div>
      </AppShell>
    ),
  },
  {
    path: "*",
    element: <NotFoundPage />,
  },
]);

export default function App() {
  return (
{% if include_data_fetching %}
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
      <Toaster />
    </QueryClientProvider>
{% else %}
    <>
      <RouterProvider router={router} />
      <Toaster />
    </>
{% endif %}
  );
}
