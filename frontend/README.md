# Forge Web

Forge Web scaffolds a ready-to-build React + TypeScript + Vite + Shadcn/ui
dashboard from a single template, so starting a new frontend app is faster
than copying an old project by hand.

## What it generates

- React 18, TypeScript, Vite (SPA), React Router, Tailwind v4, Shadcn/ui
- A curated Shadcn component set (button, input, card, table, data-table,
  tabs, select, dialog, alert-dialog, dropdown-menu, toast, form, avatar,
  badge, skeleton) — every value themed from `docs/DESIGN.md`'s design
  tokens via `src/styles/theme.css`, never hardcoded
- A sample CRUD dashboard (`/`) wired end-to-end through a mock/real API
  client switched by `VITE_API_MODE`, as a pattern to copy for real features
- A component showcase page (`/components`) rendering every primitive with
  mock data, so you can see the whole design system at a glance
- Static pages: 404, error, loading, empty-state
- TanStack Query hooks, react-hook-form + zod forms, date/currency
  formatters
- A generated `.env` (pre-filled from your answers) alongside a documented
  `.env.example`
- A GitHub Actions CI workflow (`.github/workflows/ci.yml`): `npm install &&
  npm run build` (typecheck + build), CodeQL, a Trivy filesystem scan, PR
  dependency review, and zizmor workflow linting — the dependency-review job
  needs Dependabot/vulnerability alerts enabled on your GitHub repo first

## Install

Run from the repo root:

```bash
py -m venv .venv
.venv\Scripts\pip install -e "./frontend[dev]"
```

## Usage

```bash
.venv\Scripts\forge-web new
```

Run without flags to be walked through an interactive wizard (project name,
target path, API base URL). Any flag you pass skips its prompt:

```bash
.venv\Scripts\forge-web new --name my-dashboard --path C:\projects --api-base-url http://localhost:8080/api
```

Forge Web shows a preview of the file tree it's about to write and asks for
confirmation before touching disk. After generation it runs a structural
check, `npm install && npm run build`, `tsc --noEmit`, and a check that no
hardcoded color/pixel values leaked outside `theme.css` — then reports next
steps.

See [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for command details.

## Development

Run from the repo root:

```bash
.venv\Scripts\pytest frontend/tests -v
```

`npm` must be on PATH for `frontend/tests/test_generation.py` and the
validator's build/typecheck checks to pass — both shell out to `npm`/`npx`
against a generated project.

The design spec and implementation plan live under
`../docs/superpowers/specs/` and `../docs/superpowers/plans/`.
