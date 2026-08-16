"""Exclude-glob manifest for the minimal template — drops the CRUD dashboard, its form,
the data hooks, and the API client; keeps the full Shadcn set and the component showcase."""

EXCLUDES: tuple[str, ...] = (
    "src/pages/dashboard/dashboard-page.tsx",
    "src/pages/dashboard/item-form.tsx",
    "src/lib/hooks/use-items.ts",
    "src/lib/api-client/*",
)
