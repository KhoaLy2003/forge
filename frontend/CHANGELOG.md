# Changelog

## [Unreleased]

- Added a `--template` flag (`base` [default] / `minimal`) plus the registry
  mechanism behind it: `templates/base/` was split into `templates/_shared/`
  (the file tree) and per-template `manifest.py` exclude-glob manifests,
  discovered by a new `core/templates.py`. `minimal` drops the sample CRUD
  dashboard, its API client, and TanStack Query hooks while keeping the full
  Shadcn component set and the `/components` showcase page; `package.json`,
  `App.tsx`, and `nav-sidebar.tsx` gained `{% if include_data_fetching %}`
  conditionals for the content/wiring that must differ even though those
  files themselves are shared. `--template` is deliberately not part of the
  interactive wizard and always defaults to `base`, so existing
  non-interactive, flag-complete invocations are unaffected.
- Generated projects now ship a GitHub Actions CI workflow
  (`.github/workflows/ci.yml`): `npm install && npm run build` (typecheck +
  build; no separate test step, since the scaffold has no test runner
  configured), CodeQL (`javascript-typescript`), a Trivy filesystem scan run
  after `npm install` (so it resolves exact versions via
  `package-lock.json`), PR-only dependency review, and zizmor linting of the
  workflow file itself — all actions pinned to commit hashes with
  `persist-credentials: false`
- The generated README notes the one-time setup step (enabling
  Dependabot/vulnerability alerts) the `dependency-review` job requires on
  the user's own GitHub repo
- `EXPECTED_STRUCTURAL_PATHS` updated to include the new workflow file

## 0.1.0 — 2026-08-15

Initial release.

- `forge-web new` command: interactive wizard (project name, target path,
  API base URL), tree preview with confirmation, Jinja2-based rendering,
  structural + build/typecheck validation
- Single `base` template: Vite (SPA), React 18, TypeScript, React Router,
  Tailwind v4, Shadcn/ui
- A curated Shadcn component set (button, input, card, table, data-table,
  tabs, select, dialog, alert-dialog, dropdown-menu, toast, form, avatar,
  badge, skeleton), themed entirely from `docs/DESIGN.md`'s design tokens
  via `src/styles/theme.css`
- A sample CRUD dashboard (`/`) wired end-to-end through a mock/real API
  client switched by `VITE_API_MODE`, plus a component showcase page
  (`/components`) rendering every primitive with mock data
- Static 404, error, loading, and empty-state pages
- TanStack Query hooks, react-hook-form + zod forms, date/currency
  formatters
- A generated `.env` (pre-filled from wizard answers) alongside a
  documented `.env.example`
- Post-generation validation: structural check, `npm install && npm run
  build`, `npx tsc --noEmit`, and a check that no hardcoded color/pixel
  values leaked outside `theme.css`
- Abort-before-write if the target directory already exists (no merge or
  overwrite in this version)
