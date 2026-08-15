import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { AppShell } from "@/components/common/app-shell";
import { Toaster } from "@/components/ui/sonner";
import { EmptyState } from "@/pages/static/empty-state";
import LandingPage from "@/pages/landing/landing-page";
import DashboardPage from "@/pages/dashboard/dashboard-page";
import ComponentShowcasePage from "@/pages/showcase/component-showcase-page";
import ErrorPage from "@/pages/static/error-page";
import LoadingPage from "@/pages/static/loading-page";
import NotFoundPage from "@/pages/static/not-found-page";

const queryClient = new QueryClient();

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
  {
    path: "/dashboard",
    element: (
      <AppShell>
        <DashboardPage />
      </AppShell>
    ),
    errorElement: <ErrorPage />,
  },
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
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
      <Toaster />
    </QueryClientProvider>
  );
}
