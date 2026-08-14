# Forge Web — React Frontend Project Scaffolding Tool — Design

## Goal

Speed up the "init source code" phase for new frontend apps by generating a
ready-to-build React + TypeScript project — pre-loaded with a curated set of
Shadcn UI components, a sample dashboard, mock data, static pages, and
shared utilities — instead of building it up by hand each time. Same goal
as Forge (the backend generator): faster *and* trustworthy enough that
teams actually adopt it instead of copy-pasting an old project.

## Name

**Forge Web** (working name; CLI entry point `forge-web`).

## Tech Stack (generated projects)

- React 18 + TypeScript
- Vite (SPA), React Router
- Tailwind v4 (CSS-first config, no `tailwind.config.js`)
- Shadcn/ui (component base)
- TanStack Query (data fetching / server state)
- react-hook-form + zod (forms/validation)
- npm (package manager assumed by the generator's validator and by
  generated `package.json` scripts)

## Tooling (the generator itself)

- Python CLI, same tool family/approach as Forge (the backend generator) —
  kept consistent so both tools share a CLI feel, preview/progress/validate
  flow, and directory structure, but Forge Web is a **separate package in
  this repo** (`forge-web/`), not a subcommand of the existing `forge` CLI
  and not a separate repo. No code is shared between the two — Java
  package-path logic and npm/tsc validation are different enough problems —
  but module names and responsibilities intentionally mirror Forge's
  `core/` layout so anyone familiar with one codebase can navigate the
  other immediately.

## Architecture

Forge Web follows the same four-stage pipeline as Forge:

1. **Wizard** (`core/config_schema.py` + a wizard module) — collects
   project name, target path, and any generator-level choices (theme
   defaults, initial API base URL) not already given as CLI flags.
   `ForgeWebConfig` is the single source of truth for validation and for
   every derived value the templates need (`template_context()`).
2. **Preview** (`core/tree_preview.py`) — same box-drawing tree preview and
   `[y/N]` confirmation as Forge, showing the resolved output paths before
   anything is written.
3. **Render** (`core/renderer.py`) — same `resolve_tree` / `render_tree`
   custom Jinja2 tree-templating approach as Forge: both file/directory
   names and file contents are templated; `render_tree` refuses to write
   into an existing target directory (`TargetExistsError`), never merges
   or overwrites.
4. **Validate** (`core/validator.py`) — post-generation checks, same
   `ValidationResult` shape as Forge's validator:
   - `check_structure` — expected files present
   - `run_compile`-equivalent: `npm install && npm run build`, plus
     `tsc --noEmit` for a standalone type-check signal

On any write or validation failure, the CLI offers to delete the
partially-generated folder — same behavior as Forge, never a silent
partial state left behind.

## Directory Structure

```
forge-web/
  cli.py
  core/
    config_schema.py     # project name/path validation, template_context()
    renderer.py            # resolve_tree / render_tree (Jinja2 tree templating)
    tree_preview.py         # box-drawing preview, y/N prompt
    validator.py             # npm install / npm run build / tsc --noEmit
    progress.py               # [n/total] step printer
  templates/
    base/
      src/
        components/ui/         # curated Shadcn set (see Component Set below)
        components/common/     # nav shell, layout, theme toggle
        pages/dashboard/         # sample dashboard page
        pages/static/             # 404, error boundary, loading skeleton, empty state
        lib/api-client/            # interface + mock impl + fetch impl (env-switched)
        lib/hooks/                   # TanStack Query hooks wrapping api-client
        lib/utils/                     # date/currency formatters
        styles/theme.css                 # single source of truth for all design tokens
      .env.example
      package.json, tsconfig.json, vite.config.ts
  tests/
    test_generation.py     # generate into tmpdir, run npm install + build + tsc --noEmit
```

## Component Set (v1, curated — broader default)

Pre-generated in `components/ui/`: button, input, label, card, table,
dialog, dropdown-menu, sonner (toast), form, sidebar/nav, avatar,
data-table (TanStack Table), tabs, select, badge, skeleton, alert-dialog.

Everything beyond this set is **opt-in via flags** (e.g. `--with-charts`,
`--with-auth-pages`), mirroring Forge's "base + optional modules" pattern.
No opt-in modules are designed in v1 — the flag mechanism is noted as a
future extension point, not built now.

## Static Pages (explicit v1 scope)

404, generic error boundary (500-equivalent), loading/skeleton state,
empty-state pattern.

## Theming — Design Tokens from `docs/DESIGN.md`

The project's `docs/DESIGN.md` (a Notion-style design-token analysis:
colors, typography scale, spacing, radius, elevation, component chrome) is
baked in as the **default theme**, not an opt-in preset.

### Single source of truth

`templates/base/src/styles/theme.css` holds every visual token as a
Tailwind v4 `@theme` CSS-custom-property block, seeded from
`DESIGN.md`'s front-matter values at template-authoring time (this file
lives in the generator's template tree; it is not read from `DESIGN.md` at
generation runtime). This is the **only** place token values are defined.

- **Light mode**: exact `DESIGN.md` values — warm canvas `#f6f5f4`, ink
  `#000000`, primary blue `#0075de`, full typography/spacing/radius scale,
  sticker accent colors (purple/pink/orange/teal/green/sky) available as
  decorative-only utility classes, never structural fills.
- **Dark mode**: auto-derived by inverting the neutral ramp (`canvas`
  ↔`ink`, `surface` darkened, `hairline` lightened-on-dark) while brand
  colors (primary blue, sticker accents) stay fixed — the same
  "polarity-flip" pattern `DESIGN.md` itself documents for
  `ex-pricing-tier-featured`. A theme toggle (`components/common/`) ships
  in the base template.
- Shadcn component primitives (`button.tsx`, `card.tsx`, etc.) are
  configured to reference these theme variables/utility classes instead of
  Shadcn's stock zinc/neutral defaults — pill `rounded-full` for marketing
  CTAs vs. tighter `rounded-md` for utility/nav buttons, hairline + soft
  layered-shadow elevation instead of heavy drop-shadows, per `DESIGN.md`'s
  Do's/Don'ts.

### Hard rule: no hardcoded design values in templates

No component, page, or utility file under `templates/base/` may hardcode a
hex/rgb color or a raw pixel value for anything the token system covers
(color, radius, spacing, font size/weight/line-height, shadow). Every such
value is consumed through the CSS variables (`var(--color-primary)`) or
the Tailwind utility classes generated from them (`bg-primary`,
`rounded-full`, `text-body-md`). This is what makes "user edits
`theme.css` post-generation, the whole app updates" true.

Shadcn's own primitives already follow this convention. The discipline
mainly applies to the custom dashboard/pages/common components scaffolded
on top of them.

**Enforcement**: `tests/test_generation.py` includes a grep-based check
over the generated `.tsx`/`.css` output that fails the test if a stray hex
literal or raw pixel value appears outside `styles/theme.css`.

## Environment Variables — Configuration Principle

Any generated-project value that varies by environment or deployment goes
through `.env` / `import.meta.env`, never gets baked into the JS bundle at
generation time. `.env.example` ships in the template documenting each
one; `config_schema.py` seeds the initial `.env` from the wizard's
answers, but the running app always reads from `import.meta.env` at
runtime.

v1 concrete instances:

- `VITE_API_MODE` (`mock` | `real`) — selects the `api-client`
  implementation (see Mock/Real API Client below).
- `VITE_API_BASE_URL` — the real API client's fetch target.
- `VITE_APP_NAME` — app name/title wherever it appears in nav/footer, so
  it can change post-generation without regenerating the project.

Future env-var candidates are evaluated against this same principle as the
template grows (this is a standing convention, not a one-time list).

## Mock/Real API Client

`lib/api-client/` exposes one `ApiClient` interface with two
implementations — a mock (in-memory/fixture data) and a real
`fetch`-based implementation — selected at runtime by `VITE_API_MODE`.
TanStack Query hooks in `lib/hooks/` consume the interface, not either
implementation directly, so switching from mock to real data is a `.env`
change, not a rewrite.

## Forms

One sample form (e.g. a create/edit modal on the dashboard) built with
react-hook-form + zod, matching Shadcn's own documented pattern, so teams
have a working reference instead of each reinventing validation wiring.

## Testing

`tests/test_generation.py` is the end-to-end guarantee, same role as
Forge's `test_generation.py`: builds a real `ForgeWebConfig`, renders the
actual template into a tmp dir, and runs:

- `npm install`
- `npm run build`
- `tsc --noEmit`
- the hardcoded-design-value grep check described above

`npm` must be on PATH for this test to pass, the same way Forge's tests
require `mvn` on PATH. Other modules (`config_schema`, `renderer`,
`tree_preview`, `validator`) are unit-tested in isolation, matching
Forge's test split.

## Explicitly Out of Scope (v1)

- Next.js / server-side rendering (Vite SPA only, decided as the
  structural fork up front)
- Opt-in component modules (charts, auth pages, i18n) — flag mechanism
  noted as future work, not implemented
- Multi-entity/schema-driven page generation — the sample dashboard and
  static pages are the reference pattern, same philosophy as Forge's
  single example entity
- Named/multiple theme presets — v1 ships exactly one baked-in theme
  (from `DESIGN.md`); a `--theme` flag system is a future option
- pnpm/yarn support — npm only in v1
