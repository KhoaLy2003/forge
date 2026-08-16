## [Unreleased]

## 0.2.0 — 2026-08-16

- Generated projects now ship a Vitest + React Testing Library test suite
  covering every component and page in the template, gated at 80% overall
  line coverage via `vite.config.ts`'s `test.coverage.thresholds` and
  enforced in the generated CI workflow (`npm run test:coverage`), with a
  coverage-summary step writing the percentage to the CI run's job summary
  regardless of pass/fail. Vitest was chosen over Jest to reuse the
  project's existing Vite transform pipeline directly. `main.tsx`'s
  bootstrap and two type-only files (`api-client/types.ts`,
  `api-client/api-client.ts`) are excluded from the gate as
  untestable/non-executable; everything else — including the
  `include_data_fetching`-conditional `nav-sidebar.tsx`/`App.tsx` branches —
  is covered by real tests, not exclusions. Verified end-to-end against
  fresh renders of both templates: `base` lands at 93.45% (71 tests),
  `minimal` at 92.67% (48 tests).
- This repo's own CI now runs `pytest --cov=forge_web.core --cov=forge_web.cli`,
  gated at 90% coverage of the generator's own Python source (not
  `templates/`). A coverage-summary step writes the per-file breakdown to
  the job summary. `main()`'s console-encoding boilerplate is excluded via
  `# pragma: no cover`; new tests were added for previously-untested CLI
  failure branches (build/typecheck/design-token/spacing-collision
  failures, and the render-exception path) to close a real gap this
  surfaced, rather than lowering the bar to hide it.
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
