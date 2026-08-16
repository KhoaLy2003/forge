# Frontend Generated-Project Coverage Gate — Design

## Goal

`forge-web`'s generated project template currently ships zero test runner and
zero tests — its CI workflow only runs `npm install && npm run build`. This
adds a real test suite (Vitest + React Testing Library) covering the
template's existing surface, plus a coverage gate wired into the generated
CI workflow, mirroring the JaCoCo gate already shipped for `forge`'s
generated backend template (`docs/superpowers/specs/2026-08-16-multi-template-support-design.md`
and the coverage-gate work that followed it) — but calibrated to a
lower threshold since this is a from-scratch suite, not an
already-well-tested codebase gaining a check.

## Tooling & configuration

- **Vitest** (test runner) + `@testing-library/react` + `@testing-library/jest-dom`
  (component testing) + `@vitest/coverage-v8` (coverage), with
  `environment: "jsdom"`. Vitest reuses the project's existing Vite
  transform pipeline directly — no separate Babel/ts-jest configuration
  needed, unlike Jest in a Vite project.
- Config lives in a `test:` block added to the template's existing
  `vite.config.ts`, or a sibling `vitest.config.ts` if `vite.config.ts`'s
  existing `{% if %}` conditionals make embedding awkward (decided at
  implementation time, whichever renders cleaner).
- Tests are **colocated**: `Component.test.tsx` next to `Component.tsx` (the
  standard Vitest/RTL convention). This also means a test file is
  automatically excluded by `minimal`'s manifest whenever its source file
  is, via the same exclude-glob mechanism already built for the multi-template
  feature — no separate bookkeeping needed for which tests apply to which
  template.
- `real-client.ts`'s `fetch` calls are mocked via `vi.stubGlobal("fetch", vi.fn())`
  in its test file — no MSW or other mocking library added as a template
  dependency, keeping the generated project's footprint small.
- `package.json` gains two scripts: `"test": "vitest run"` (fast inner loop,
  no coverage) and `"test:coverage": "vitest run --coverage"` (enforces the
  threshold below; used by CI).

## Coverage scope & threshold

- **80% line coverage**, gated via Vitest's `coverage.thresholds.lines`
  config (a failing threshold exits non-zero, same enforcement mechanism as
  JaCoCo's `check` goal on the backend side). Lower than backend's 90%
  because this is an entirely new suite being built from a 0% baseline,
  not an existing well-tested codebase gaining a check.
- **Aggregate, not per-file** — matches the backend gate's `BUNDLE`-level
  check rather than a per-file minimum, so no single thin file blocks the
  build.
- **Excluded from the coverage config** (`test.coverage.exclude`, alongside
  Vitest's own sensible defaults):
  - `src/main.tsx` — pure bootstrap (`ReactDOM.createRoot(...).render(...)`),
    the frontend equivalent of backend's excluded `main()`.
  - `**/*.d.ts` (e.g. `vite-env.d.ts`) — type declarations only, never
    executed.
  - `src/lib/api-client/types.ts` — pure TS interfaces, zero runtime
    statements; excluded explicitly for clarity even though v8 wouldn't
    count it either way.
- Everything else counts: all 16 Shadcn components, `App.tsx`,
  `nav-sidebar.tsx`, `app-shell.tsx`, the dashboard/item-form/hooks/api-client
  (present in `base` only), the showcase and static pages, and
  `lib/utils.ts`/`format.ts`.
- `minimal`'s smaller file surface (no dashboard/hooks/api-client) shrinks
  its own coverage denominator to match automatically, via the existing
  manifest-exclude mechanism — no special-casing required in the Vitest
  config itself.

## Test-writing plan

Tests are written at a depth proportionate to each file's actual logic,
not uniformly exhaustive — this is a starter template, not a production
app being audited.

**Real interaction tests** (files with actual behavior to exercise):
- `dialog.tsx` / `alert-dialog.tsx` — open/close, dismissal
- `dropdown-menu.tsx` — open + item selection
- `select.tsx` — open + option selection
- `tabs.tsx` — switching the active tab
- `data-table.tsx` — sorting/pagination (whatever the component actually
  implements)
- `form.tsx` — validation error display, via a small probe form (mirroring
  the backend `GlobalExceptionHandlerTest`'s probe-controller pattern)
- `button.tsx` — click handler invocation, disabled state
- `input.tsx` / `label.tsx` — value change, label association
- `use-items.ts` — query/mutation hooks against a mocked `apiClient`
- `mock-client.ts` / `real-client.ts` — each `ApiClient` method
- `item-form.tsx` / `dashboard-page.tsx` — create/edit/delete flows
- `App.tsx` — routing renders the correct page per path
- `nav-sidebar.tsx` — active-link highlighting, and the
  `include_data_fetching` conditional itself (Dashboard link present/absent
  per template — a direct regression test for the dead-link bug fixed
  earlier in the multi-template work)

**Render-smoke + key-prop tests** (presentational, little/no branching):
`badge.tsx`, `skeleton.tsx`, `avatar.tsx`, `card.tsx`, `table.tsx`,
`sonner.tsx`, `app-shell.tsx`, all four static pages
(`not-found-page.tsx`/`error-page.tsx`/`loading-page.tsx`/`empty-state.tsx`),
`component-showcase-page.tsx`, `landing-page.tsx` — render without
crashing, assert key text/props reflect inputs.

**Pure-function unit tests** (no rendering): `lib/utils.ts` (`cn`
class-merging), `lib/utils/format.ts` (date/currency formatters).

## CI wiring

- `templates/_shared/.github/workflows/ci.yml`'s `build` job gains a step
  after `npm install`: `npm run test:coverage` — runs the suite and enforces
  the 80% gate in one command.
- A `Coverage summary` step (`if: always()`, so the number is visible even
  on failure) parses `coverage/coverage-summary.json` (produced by adding
  the `json-summary` reporter alongside `text`/`html`) and appends a
  markdown line to `$GITHUB_STEP_SUMMARY` — reading `total.lines.pct`,
  mirroring the `awk`-over-`jacoco.csv` step already shipped for backend.

## Verification plan (before merging)

Same discipline as the backend JaCoCo gate: render both `base` and `minimal`
into a real temp directory, run `npm run test:coverage` for real, and only
lock in 80% (or adjust it) once actual numbers are seen — not assumed. If
the first honest run lands meaningfully below 80%, close real gaps with
more tests before shipping, the same way backend's gap
(`GlobalExceptionHandler`/`ExampleController`/`ExampleServiceImpl`) was
closed rather than the threshold lowered further or tests padded.

## Out of scope

- MSW or any other HTTP-mocking library as a template dependency.
- Visual regression / screenshot testing.
- Accessibility-audit tooling (e.g. `axe-core`) — RTL's queries already bias
  toward accessible markup, but a dedicated a11y check is a separate,
  unaddressed concern.
- Per-file coverage minimums — aggregate only, matching the backend
  precedent.
