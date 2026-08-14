# Frontend Code Generator / Project Scaffolding Tool — Plan

## Goal

Speed up the "init source code" phase for new frontend apps by generating a
ready-to-build React + TypeScript project — pre-loaded with common UI
components, a sample dashboard, mock data, static pages, and shared
utilities — instead of building it up by hand each time. Same goal as the
backend generator: faster *and* trustworthy enough that teams actually adopt
it instead of copy-pasting an old project.

## Tech Stack (generated projects)

- ReactJS
- TypeScript
- Shadcn/ui (component base)

## Tooling (the generator itself)

- Same tool family/approach as the backend generator (Python-based CLI,
  templating engine) — kept consistent so both tools share a CLI feel,
  preview/progress/validate flow, and structure.

---

## Original Idea (starting point)

Code generator including:

- **UI Components**: common, most-used components using the Shadcn library
- **Sample dashboard page**, skeleton page with navigation
- **Provide mock data** with API client call as mock
- **Static pages** like error page, etc.
- **Util classes** like format date/time, currency, etc.

Same overall goal as the backend generator: make the "init source code"
phase faster than doing it manually.

---

## Review & Improvements

### 1. Define a curated component set, not an open-ended "most-used" list

Shadcn has 50+ components — pre-generating all of them bloats every project.
Instead, define a **curated default set** covering what the dashboard +
static pages actually need: button, input, table, dialog, form, card,
dropdown, toast/sonner, sidebar/nav. Everything beyond that becomes
**opt-in via flags** (e.g. `--with-charts`, `--with-data-table`) — mirroring
the backend plan's "base + optional modules" pattern, kept consistent across
both tools.

### 2. Give the mock API client a swap-out story, not just mock data

The real risk: teams wire the whole app to mocks, and the mock→real
transition later becomes painful because it wasn't structured for it. Fix:
generate a proper **API client abstraction layer** — one `apiClient`
interface with a mock implementation and a real `fetch`/axios implementation
behind the same interface, switched by env var. "Mock now, real later"
becomes a config change instead of a rewrite — this is what actually keeps
the tool paying off past week one.

### 3. Decide the data-fetching library up front

A dashboard + mock API implies a fetching/state layer. **TanStack Query
(React Query)** is the natural default — pairs well with the mock/real
client swap above, and is close to the industry standard. Leaving this
undecided means every generated project ends up inconsistent.

### 4. Decide the routing/framework approach — highest-leverage open question

"Skeleton page with navigation" implies routing, but this needs a decision
because it's structurally a fork, not a detail:

- **Vite + React Router** (SPA) — simpler mental model, closer to your
  original scope
- **Next.js (App Router)** — file-based routing, server components, changes
  how "static pages" and data fetching even work

This should be decided before templates are built, since it changes almost
everything downstream.

### 5. Include a standard form stack

Dashboards inevitably need forms — filters, create/edit modals. Shadcn's own
docs standardize on **react-hook-form + zod**. Worth including one sample
form using this pairing so teams don't each reinvent validation patterns.

### 6. Include theming / dark mode in the base template

Shadcn is commonly paired with a theme provider (light/dark toggle via CSS
variables). Cheap to add, high visual payoff for a sample dashboard demo —
better as part of the base template than bolted on later.

### 7. Validate the generated project (parity with backend tool)

Same principle as the backend generator — don't hand back code that doesn't
actually run:

- `tsc --noEmit` — type check
- `npm run build` (Vite/Next build) — build succeeds
- optional lint pass

### 8. Be specific about static pages

"Error page, etc." should be an explicit list so template scope is clear:
404, generic error boundary / 500-equivalent, loading/skeleton state, and an
empty-state pattern (dashboards need these constantly).

---

## Refined Source Structure

```
generator/
  README.md
  CHANGELOG.md
  QUICK_REFERENCE.md
  cli.py (or cli.ts)
  core/
    config_schema           # parameter validation (single source of truth)
    tree_preview             # renders tree, prompts y/n
    progress                 # step tracker / logger
    renderer                 # templating engine
    validator                # tsc + build check
  templates/
    base/
      components/ui/         # curated shadcn set
      components/common/     # app-level shared components (nav, layout)
      pages/dashboard/
      pages/static/           # 404, error, empty states
      lib/api-client/         # mock + real, same interface
      lib/utils/              # date, currency formatters
      lib/hooks/              # react-query hooks
    modules/                  # optional: charts, data-table, auth-pages, i18n
  tests/
    test_generation.*         # generate into tmpdir, assert build + typecheck pass
```

Same rationale as the backend plan: `tests/` exists because the tool's job
is "produce working code" — it needs its own CI that generates a real
project and confirms it builds and type-checks, so template regressions
don't slip through silently.

---

## Open Questions for Review

- [ ] Vite (SPA) vs Next.js — the biggest structural fork, decide first
- [ ] React Router vs framework-native routing
- [ ] TanStack Query as the default data-fetching layer?
- [ ] react-hook-form + zod as the default form stack?
- [ ] Tailwind version pinned alongside shadcn?
- [ ] Which components are in the curated v1 set vs opt-in modules?
- [ ] Should this share a CLI/codebase with the backend generator, or stay
      a separate tool with a matching structure/flow?
