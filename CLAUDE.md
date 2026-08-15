# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

This repo is a monorepo of two independent scaffolding CLIs that share the same wizard → preview → render → validate philosophy, each generating a ready-to-build project instead of a bare skeleton:

- **`backend/`** — Forge: a Python CLI (Typer-based) that scaffolds a Java + Spring Boot 4 + PostgreSQL project from a single Jinja2 template. Running `forge new` generates a complete, compiling Maven project.
- **`frontend/`** — Forge Web: a Python CLI (Typer-based) that scaffolds a React + TypeScript + Vite + Tailwind v4 + Shadcn/ui project from a single Jinja2 template. Running `forge-web new` generates a complete, buildable dashboard app.

Shared, repo-wide docs (design tokens, specs, plans) live under `docs/`. Each package keeps its own README, QUICK_REFERENCE, and CHANGELOG.

## Commands

```bash
# Setup (one venv, both packages installed editable)
py -m venv .venv
.venv\Scripts\pip install -e "./backend[dev]"
.venv\Scripts\pip install -e "./frontend[dev]"   # once frontend/ exists

# Run the CLIs
.venv\Scripts\forge new
.venv\Scripts\forge new --name my-service --path C:\projects --group-id com.example --artifact-id my-service

# Tests
.venv\Scripts\pytest backend/tests -v
.venv\Scripts\pytest backend/tests/test_renderer.py -v      # single file
.venv\Scripts\pytest backend/tests/test_renderer.py::test_name -v   # single test
```

`mvn` must be on PATH for `backend/tests/test_generation.py` and the validator's compile check to pass — both actually shell out to Maven against a generated project. (`frontend/`'s equivalent test will require `npm` on PATH once built.)

## Architecture — `backend/` (Forge)

The pipeline in `backend/cli.py`'s `new` command is the whole system: **wizard → preview → render → validate**, each stage a separate module in `backend/core/`.

1. **`core/wizard.py`** (`collect_params`) — fills in whatever CLI flags were omitted by prompting interactively, reprompting on validation failure. Returns a `ForgeConfig`.
2. **`core/config_schema.py`** (`ForgeConfig`) — the single source of truth for parameter validation (project name, group id, artifact id regexes) and for every derived value used in templates (`base_package`, `package_path`, `app_class_name`). `template_context()` is what the renderer receives — if a template needs a new variable, add it here.
3. **`core/renderer.py`** (`resolve_tree` / `render_tree`) — a custom Jinja2 tree renderer. Both file/directory **names** and file **contents** are templated (e.g. `templates/base-layered/src/main/java/{{ package_path }}/{{ app_class_name }}Application.java`). `resolve_tree` computes the output path list without writing (used for the preview); `render_tree` does the actual write and raises `TargetExistsError` if the target directory exists.
4. **`core/tree_preview.py`** — renders the resolved path list as a box-drawing tree and asks `[y/N]` before anything is written.
5. **`core/validator.py`** — post-generation checks: `check_structure` (expected files present) then `run_compile` (real `mvn compile` subprocess, 300s timeout). Both return a `ValidationResult`.
6. **`core/progress.py`** — trivial `[n/total]` step printer used between stages.

`cli.py` wires these together and owns `EXPECTED_STRUCTURAL_PATHS` (what the structural check verifies) and `TEMPLATE_DIR` (currently the single `templates/base-layered` template — no template-selection concept yet). On any write or validation failure, it offers to delete the partially-generated folder; it never merges or overwrites an existing target directory.

### The template itself

`templates/base-layered/` is a full Spring Boot project, not fragments — Java 21, Spring Boot 4, Liquibase migrations, docker-compose for local Postgres, and one example entity (`Example`) wired end-to-end through `controller/service/repository/entity` as a reference for full CRUD. Jinja2 placeholders appear in both paths (`{{ package_path }}`, `{{ app_class_name }}`) and file contents. Because `jinja2.StrictUndefined` is used, every variable referenced in the template must exist in `ForgeConfig.template_context()`.

### Testing approach

`tests/test_generation.py` is an end-to-end test: it builds a real `ForgeConfig`, renders the actual template into a tmp dir, and runs both validator checks including a real `mvn compile`. Other test files unit-test each `core/` module in isolation. When changing `config_schema.py`'s derived properties or the template's variable usage, both layers need to stay in sync — the strict Jinja2 undefined check will fail fast if they don't.

## Architecture — `frontend/` (Forge Web)

Mirrors the same wizard → preview → render → validate pipeline and `core/` module shape as `backend/`, generating a Vite + React + TypeScript + Shadcn project instead — no code is shared between the two packages, but the module names/responsibilities intentionally match. Unlike `backend/` (which installs bare top-level `cli`/`core` modules), everything here lives under a namespaced `forge_web` package — `forge_web/cli.py`, `forge_web/core/*.py`, `forge_web/templates/base/` — specifically so both packages can be `pip install -e`'d editable into the *same* venv without one's `import cli`/`import core` shadowing the other's (this bit a real user before the rename: `forge-web`'s console script was silently resolving to `backend/cli.py`, so `--api-base-url` didn't exist). If `backend/` is ever restructured, keep this asymmetry — never give either package a bare top-level module name again.

1. **`forge_web/core/config_schema.py`** (`ForgeWebConfig`) — validates `project_name`/`target_path`/`api_base_url` and derives `app_display_name`. `template_context()` returns exactly `{project_name, app_display_name, api_base_url}`.
2. **`forge_web/core/renderer.py`** — the same custom Jinja2 tree renderer as `backend/core/renderer.py`'s (`resolve_tree`/`render_tree`, `TargetExistsError`).
3. **`forge_web/core/validator.py`** — `check_structure`, `run_build` (`npm install && npm run build`), `run_typecheck` (`npx tsc --noEmit`), and `check_no_hardcoded_design_values` (a grep-based check, scoped to `target_dir/src`, that fails if any hex color literal appears outside `styles/theme.css`).
4. **`forge_web/cli.py`** — wires the pipeline together; after a successful render it also copies the rendered `.env.example` to `.env` so the generated project is immediately runnable with the user's actual answers baked in.

### The template itself

`forge_web/templates/base/` is a full Vite + React + TypeScript + Tailwind v4 + Shadcn/ui project: a curated component set (button, input, card, table, data-table, tabs, select, dialog, alert-dialog, dropdown-menu, toast, form, avatar, badge, skeleton), a sample CRUD dashboard (`/`) and component showcase (`/components`) wired end-to-end, static pages (404/error/loading/empty-state), and a mock/real API client switched by `VITE_API_MODE`. Every color/typography/spacing/radius/shadow value in the template is a CSS custom property in `styles/theme.css`, transcribed from `docs/DESIGN.md`'s prose/tables (that doc currently has no machine-readable front matter — read its Colors/Typography/Layout/Elevation sections directly). Because Jinja2's `{{ }}` delimiters collide with JSX's double-curly inline-object-literal props (e.g. `style={{ ... }}`, `toastOptions={{ ... }}`), any new template file using that JSX pattern must wrap the literal in `{% raw %}...{% endraw %}` — see `components/ui/form.tsx` and `sonner.tsx` for examples.

### Testing approach

`tests/test_generation.py` is the end-to-end test: it builds a real `ForgeWebConfig`, renders the actual template into a tmp dir, and runs `npm install`, `npm run build`, `npx tsc --noEmit`, and the design-token check for real — this requires `npm`/`npx` on PATH (no Docker needed, unlike `backend/`'s Maven-based checks). Other test files unit-test each `forge_web/core/` module in isolation.

## Design docs

Design specs and implementation plans for both packages live under `docs/superpowers/specs/` and `docs/superpowers/plans/`. `docs/DESIGN.md` holds the shared design-token system (colors, typography, spacing, elevation) that `frontend/`'s generated theme is seeded from.
