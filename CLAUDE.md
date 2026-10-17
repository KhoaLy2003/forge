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
5. **`core/validator.py`** — post-generation checks, each returning a `ValidationResult`: `check_structure` (expected files present), `check_observability` (Docker-free static check of the monitoring files: they exist and parse, and every metric used by alerts/dashboard is in the registry in `core/observability_metrics.py`; skipped when `include_monitoring` is false) and `run_compile` (real `mvn test-compile`, 300s timeout). `run_tests(target_dir, filter)` runs a filtered `mvn test` and is used by the end-to-end tests.
6. **`core/progress.py`** — trivial `[n/total]` step printer used between stages.

`cli.py` wires these together and owns `EXPECTED_STRUCTURAL_PATHS` (what the structural check verifies) and `--template` (which registered template to render, default `base-layered`). On any write or validation failure, it offers to delete the partially-generated folder; it never merges or overwrites an existing target directory.

### Templates and the `--template` flag

`templates/_shared/` holds the full reference project's file tree (content described below); `templates/<name>/manifest.py` files register each selectable template as an `EXCLUDES: tuple[str, ...]` glob list, applied on top of `_shared`. `core/templates.py`'s `discover_templates()` builds the `{name: excludes}` registry `cli.py` and `ForgeConfig` both read; `filter_excluded_paths()` filters `EXPECTED_STRUCTURAL_PATHS`/`expected_structural_paths()` the same way the renderer filters the file tree. Two templates are registered today:

- `base-layered` (default) — the full reference project, `EXCLUDES = ()`.
- `minimal` — drops Liquibase migrations and the Testcontainers-backed repository test; keeps the `example` CRUD slice and MapStruct. A handful of files shared by both templates (`pom.xml`, `application.yml`) have Jinja2 `{% if use_liquibase %}` conditionals for the content that must differ even though the file itself isn't excluded — `use_liquibase` is a `ForgeConfig` property derived from `template` (`self.template != "minimal"`) and exposed via `template_context()`.

Adding a new template: create `templates/<name>/manifest.py` with an `EXCLUDES` tuple (glob patterns matched against the unrendered `_shared`-relative path, `fnmatch` semantics — a single `*` already spans `/`). If the template needs shared-file *content* to differ (not just presence), add a boolean to `template_context()` and wrap the relevant lines in `{% if %}`, following the `use_liquibase` example. `--template` intentionally has a hardcoded default (not `None`) and is not wizard-prompted, unlike every other `forge new` flag — see `backend/core/wizard.py`'s `FIELD_PROMPTS` (which omits `template`) and the commit history around 2026-08-16 for why: an earlier version defaulted to `None` and always fell through to a wizard prompt when omitted, which silently broke any fully-flag-complete non-interactive invocation (CI, scripts) that predated the `--template` flag's existence.

### Entities, `forge.yaml` and `--from`

Entity-driven generation lets users describe their own entities (fields, relations) instead of getting the `Example` slice. One model (`EntitySpec`), two ways to fill it: `forge new --from forge.yaml` and the wizard's entity step (which can save the result as `forge.yaml`). Entities require the `base-layered` template; `ForgeConfig` rejects `minimal` + entities.

Core modules (one purpose each):

- **`core/entity_spec.py`** — pydantic input models (`ProjectFile`, `EntitySpec`, `FieldSpec`, `RelationSpec`; `extra="forbid"`) and `load_forge_yaml(path)`, which injects each entity's `name` from its mapping key and raises `ValueError` naming the file and the key path of every problem.
- **`core/type_map.py`** — the single type table (`string/int/long/decimal/boolean/date/instant/uuid/enum` -> Java type, SQL type, imports, Bean Validation, sample values). Nothing else holds per-type logic.
- **`core/entity_rules.py`** — `validate_names`, `validate_relations`, `topological_order` (required to-one edges; required cycles are errors) and `resolve_model`, which builds the template-ready dataclasses.
- **`core/entity_model.py`** — those resolved dataclasses (`Model`, `ResolvedEntity`, `JoinTable`, ...); templates only read these.

`ForgeConfig(entities=...)` validates the set (all messages together, `Invalid entity model:` prefix) and exposes `has_entities`, `entities`, `join_tables`, `fk_constraints`, `changelog_start`, `changelog_files` through `template_context()`. With entities, the `Example` slice is dropped by `core/templates.py`'s `dynamic_excludes`.

Rendering fans out: `render_tree`/`resolve_tree` take `entities_dir` (`templates/_entity/`, rendered once per entity with an extra `entity` variable) and `join_dir` (`templates/_join/`, rendered once per many-to-many join table with `join_table`). The final Liquibase constraints file (deferred foreign keys) is a single `_shared` file whose name comes from the `constraints_changelog_file` context key; the master changelog is a loop over `changelog_files`. A rendered-path collision raises `ValueError`.

`forge.yaml` format: optional `project_name`, `target_path`, `group_id`, `artifact_id`, `template` plus `entities: {Name: {table?, fields: {name: {type, length|text|precision/scale|values, required, unique, default}}, relations: {name: {type, target, required, inverse|mappedBy, cascade, orphanRemoval}}}}`. Field types: `string`, `int`, `long`, `decimal` (precision/scale required), `boolean`, `date`, `instant`, `uuid`, `enum` (values required). Relation types: `many-to-one` (owning: FK + `LAZY` `@ManyToOne`), `one-to-many` (unidirectional by default, FK on the child; bidirectional only with `mappedBy`, or `inverse:` on the many-to-one), `many-to-many` (declared on one side, which owns the join table), `one-to-one` (many-to-one with a unique FK). FKs are indexed and `ON DELETE RESTRICT`; all associations are `LAZY`. Validation rules: entity names PascalCase and singular, not Java-reserved or clashing with generated classes; field/relation names camelCase and not colliding with `BaseEntity` members (`id`, `version`, `createdAt`, `updatedAt`, `deletedAt`); derived table names that are reserved SQL words (`Order`, `User`, ...) are rejected with a `table:` suggestion; relation targets must exist; `mappedBy` must name the target's owning many-to-one.

`--from` precedence, per parameter: **explicit CLI flag > value in the file > wizard prompt**. Because `--template` has a hardcoded default, "was the flag given" is read from Click's parameter source (`ctx.get_parameter_source("template") == COMMANDLINE`), never from the value, so a file `template:` beats the default but loses to an explicit `--template` (even `--template base-layered`). A missing/invalid file prints the error (with the path) and exits 1 before anything is written.

The wizard's entity step (`wizard.collect_entities`) runs **only** when the wizard actually prompted for one of the four project parameters (`wizard.needs_prompt(overrides)`), the template is `base-layered`, and `--from` supplied no entities. A flag-complete or `--from`-complete invocation must never get a new prompt (same reason as the `--template` default; regression tests in `tests/test_cli_from.py`). After a successful generation, `forge new` offers "Save the model as forge.yaml?" and `wizard.save_forge_yaml` writes `<generated project>/forge.yaml` (same format `load_forge_yaml` reads; round-trip tested).

Docker: nothing in Forge's own test suite needs it. Only the generated `*RepositoryTest` classes use Testcontainers, and they run only in the generated project's CI (Forge compiles them with `mvn test-compile`).

### Observability and notifications in the template

Both are part of `base-layered`; `minimal` keeps only the logging baseline. `ForgeConfig.include_monitoring` (`template != "minimal"`) gates the metrics endpoint, `observability/` stack files, runbook and the CI `observability-config` job; `use_liquibase` gates the notification module (`notification/`, migration `002`), which is also excluded from `minimal` by glob. Logging uses Spring Boot's ECS structured logging in the `prod` profile with a `request_id` MDC key, `RequestLogFilter`, `JobContext` and `SensitiveDataCustomizer`. The notification module is decoupled from any user model through the `RecipientDirectory`, `CurrentRecipientProvider` and `ChannelSender` interfaces (consumers use `ObjectProvider` with an inline `NONE` fallback rather than `@ConditionalOnMissingBean`, which is unreliable outside auto-configurations). Migration numbers are fixed: `001` Example (dropped when entities exist), `002` notifications, entity files from `003`.

Generated-project tests that need PostgreSQL (`NotificationQueriesTest`, every `*RepositoryTest`) use Testcontainers and run only in the generated project's CI. To exercise that SQL locally without Docker, in a scratch copy of a rendered project add `io.zonky.test:embedded-postgres` (+ the platform `embedded-postgres-binaries-*` artifact) as test dependencies and replace the `BEGIN-CONTAINER`/`END-CONTAINER` block in `NotificationQueriesTest` with an `EmbeddedPostgres.builder().start()` that feeds `spring.datasource.*`; the generated project's `spotless:check` (google-java-format) also gates `mvn verify`, so template output must stay formatted.

### The template itself

`templates/_shared/` is a full Spring Boot project, not fragments — Java 21, Spring Boot 4, Liquibase migrations, docker-compose for local Postgres, and one example entity (`Example`) wired end-to-end through `controller/service/repository/entity` as a reference for full CRUD. Jinja2 placeholders appear in both paths (`{{ package_path }}`, `{{ app_class_name }}`) and file contents. Because `jinja2.StrictUndefined` is used, every variable referenced in the template must exist in `ForgeConfig.template_context()`.

### Testing approach

`tests/test_generation.py` is an end-to-end test: it builds a real `ForgeConfig`, renders the actual template into a tmp dir, and runs both validator checks including a real `mvn compile`. Other test files unit-test each `core/` module in isolation. When changing `config_schema.py`'s derived properties or the template's variable usage, both layers need to stay in sync — the strict Jinja2 undefined check will fail fast if they don't.

## Architecture — `frontend/` (Forge Web)

Mirrors the same wizard → preview → render → validate pipeline and `core/` module shape as `backend/`, generating a Vite + React + TypeScript + Shadcn project instead — no code is shared between the two packages, but the module names/responsibilities intentionally match. Unlike `backend/` (which installs bare top-level `cli`/`core` modules), everything here lives under a namespaced `forge_web` package — `forge_web/cli.py`, `forge_web/core/*.py`, `forge_web/templates/base/` — specifically so both packages can be `pip install -e`'d editable into the *same* venv without one's `import cli`/`import core` shadowing the other's (this bit a real user before the rename: `forge-web`'s console script was silently resolving to `backend/cli.py`, so `--api-base-url` didn't exist). If `backend/` is ever restructured, keep this asymmetry — never give either package a bare top-level module name again.

1. **`forge_web/core/config_schema.py`** (`ForgeWebConfig`) — validates `project_name`/`target_path`/`api_base_url`/`template` and derives `app_display_name`. `template_context()` returns `{project_name, app_display_name, api_base_url, template, include_data_fetching}`.
2. **`forge_web/core/renderer.py`** — the same custom Jinja2 tree renderer as `backend/core/renderer.py`'s (`resolve_tree`/`render_tree`, `TargetExistsError`), including the `excluded` glob-filter parameter described below.
3. **`forge_web/core/templates.py`** — the same template registry mechanism as `backend/core/templates.py`'s: `discover_templates()`, `filter_excluded_paths()`, `SHARED_DIR`/`TEMPLATES_DIR`.
4. **`forge_web/core/validator.py`** — `check_structure`, `run_build` (`npm install && npm run build`), `run_typecheck` (`npx tsc --noEmit`), and `check_no_hardcoded_design_values` (a grep-based check, scoped to `target_dir/src`, that fails if any hex color literal appears outside `styles/theme.css`).
5. **`forge_web/cli.py`** — wires the pipeline together; after a successful render it also copies the rendered `.env.example` to `.env` so the generated project is immediately runnable with the user's actual answers baked in.

### Templates and the `--template` flag

Same `_shared` + per-template `manifest.py` mechanism as `backend/` (see that section above for the general pattern). `forge_web/templates/_shared/` holds the reference project; two templates are registered:

- `base` (default) — the full reference project, `EXCLUDES = ()`.
- `minimal` — drops the sample CRUD dashboard (`pages/dashboard/dashboard-page.tsx`, `item-form.tsx`), the `use-items.ts` TanStack Query hooks, and the mock/real API client (`lib/api-client/*`). Keeps the full Shadcn component set and the `/components` showcase page — which is why `react-hook-form` and `@tanstack/react-table` stay unconditional in `package.json` even for `minimal` (the showcase page's live demo uses both directly; only `@tanstack/react-query`, `zod`, and `@hookform/resolvers` are wrapped in `{% if include_data_fetching %}`). `App.tsx` (a shared file) has the TanStack Query import/client, the `DashboardPage` import/route, and the `QueryClientProvider` wrapper (swapped for a `<>...</>` fragment in the `else` branch, required for valid single-root JSX) all conditional on the same flag; `nav-sidebar.tsx`'s `/dashboard` nav item and its now-possibly-unused `LayoutGrid` icon import are conditional too (the `tsconfig.json`'s `noUnusedLocals: true` means an unconditional unused import would fail `minimal`'s typecheck, not just look untidy).

`include_data_fetching` is a `ForgeWebConfig` property derived from `template` (`self.template != "minimal"`). Like `backend/`, `--template` has a hardcoded default and is not wizard-prompted — see the backend section above for why.

### The template itself

`forge_web/templates/_shared/` is a full Vite + React + TypeScript + Tailwind v4 + Shadcn/ui project: a curated component set (button, input, card, table, data-table, tabs, select, dialog, alert-dialog, dropdown-menu, toast, form, avatar, badge, skeleton), a sample CRUD dashboard (`/`) and component showcase (`/components`) wired end-to-end, static pages (404/error/loading/empty-state), and a mock/real API client switched by `VITE_API_MODE`. Every color/typography/spacing/radius/shadow value in the template is a CSS custom property in `styles/theme.css`, transcribed from `docs/DESIGN.md`'s prose/tables (that doc currently has no machine-readable front matter — read its Colors/Typography/Layout/Elevation sections directly). Because Jinja2's `{{ }}` delimiters collide with JSX's double-curly inline-object-literal props (e.g. `style={{ ... }}`, `toastOptions={{ ... }}`), any new template file using that JSX pattern must wrap the literal in `{% raw %}...{% endraw %}` — see `components/ui/form.tsx` and `sonner.tsx` for examples.

### Testing approach

`tests/test_generation.py` is the end-to-end test: it builds a real `ForgeWebConfig`, renders the actual template into a tmp dir, and runs `npm install`, `npm run build`, `npx tsc --noEmit`, and the design-token check for real — this requires `npm`/`npx` on PATH (no Docker needed, unlike `backend/`'s Maven-based checks). Other test files unit-test each `forge_web/core/` module in isolation.

## Design docs

Design specs and implementation plans for both packages live under `docs/superpowers/specs/` and `docs/superpowers/plans/`. `docs/DESIGN.md` holds the shared design-token system (colors, typography, spacing, elevation) that `frontend/`'s generated theme is seeded from.
