# Multi-Template Support (Forge + Forge Web) — Design

## Goal

Both `forge` (backend) and `forge-web` (frontend) currently render exactly
one hardcoded template each (`backend/templates/base-layered`,
`frontend/forge_web/templates/base`). This adds a `--template` flag to each
CLI plus a second, lighter template per package (`minimal`), so a
contributor or user can opt into a smaller generated project without either
CLI gaining template-selection logic that has to be rebuilt from scratch
for a third template later (`auth`, `reactive`, etc. are explicitly
out of scope here — this spec only adds the mechanism plus one new template
per package).

## Approach: shared base + exclude-list overlay

The core problem this design solves: `minimal` shares the large majority of
its files with the existing template. Two fully independent template trees
would duplicate `pom.xml`/`package.json`, `common/` infra, CI workflow,
Docker config, etc. — and drift the first time either copy gets a bugfix or
dependency bump.

Instead, each package gets:

```
templates/
  _shared/            # the current template's full file tree, unchanged content
  base-layered/        # (backend) / base/ (frontend)
    manifest.py         # EXCLUDES = ()  — the full, current template
  minimal/
    manifest.py          # EXCLUDES = (glob patterns, see below)
```

`manifest.py` in each template directory exports one constant, `EXCLUDES: tuple[str, ...]`
— glob patterns matched against the **unrendered** template-source relative
path (e.g. `src/main/resources/db/changelog/**`), not the rendered output
path. Patterns are written in the same form the file tree already has on
disk (including Jinja placeholders like `{{ package_path }}` where
relevant), so a contributor adding an exclude can read it straight off
`_shared`'s directory listing.

This is deliberately exclude-only (no add/override) for now, because
`minimal` in both packages is a strict subset of the existing template —
nothing new is being introduced. A future template that *adds* files
(`auth`, `reactive`) will need an additive overlay directory layered on top
of the exclude-filtered `_shared` tree (second-wins-on-conflict); that's a
small additive change to the same mechanism, not a redesign, and is
explicitly deferred until a template actually needs it.

## Renderer changes (`core/renderer.py`, both packages)

`resolve_tree` and `render_tree` gain one new parameter:

```python
def resolve_tree(template_dir: Path, context: dict, excluded: tuple[str, ...] = ()) -> list[Path]: ...
def render_tree(template_dir: Path, target_dir: Path, context: dict, excluded: tuple[str, ...] = ()) -> None: ...
```

`_iter_rendered_files` filters each candidate file's template-relative path
against `excluded` (via `PurePath.match` or `fnmatch`) *before* rendering
any path segments, and skips yielding it if matched. No other renderer
behavior changes — `TargetExistsError`, `StrictUndefined`, and the
name+content templating both still apply exactly as today.

## CLI changes (`cli.py` / `forge_web/cli.py`)

- Replace the single `TEMPLATE_DIR` constant with a small registry mapping
  template name → `(_SHARED_DIR, excludes)`, built from each
  `templates/<name>/manifest.py`.
- Add `template: str = typer.Option("base-layered", "--template", click_type=click.Choice([...]))`
  (frontend default: `"base"`). Existing invocations without `--template`
  are unaffected — this is purely additive.
- The wizard (`core/wizard.py`) prompts for template choice when not given
  as a flag, alongside the existing prompts.
- `EXPECTED_STRUCTURAL_PATHS` becomes a function of the selected template:
  filter the existing full-template path list through the same exclude
  patterns used by the renderer, rather than hand-maintaining a second list
  — this guarantees the structural check can't drift from the actual
  manifest.

## Template content changes

### Backend: `base-layered` (unchanged) vs `minimal`

`minimal` excludes:
- `src/main/resources/db/changelog/**` (Liquibase migrations)
- The Testcontainers-backed repository test (`ExampleRepositoryTest`)

Everything else is retained, including the full `example/` CRUD slice,
MapStruct, springdoc-openapi, Actuator, and `docker-compose.yml`'s Postgres
service. `minimal` uses JPA `ddl-auto` (or leaves schema management to the
user) instead of Liquibase.

`pom.xml` (a shared file) needs its Liquibase and Testcontainers-BOM
dependency blocks wrapped in a Jinja2 conditional keyed off a new
`template_context()` boolean (`use_liquibase`), derived in
`ForgeConfig` from the selected template name. `application.yml`'s
Liquibase config block gets the same treatment. MapStruct's dependency
stays unconditional in both templates.

Implementation-time check required: confirm nothing in `common/` or the
retained `example/` slice imports Testcontainers or references a Liquibase
changelog path directly (only `ExampleRepositoryTest` should), so excluding
those two paths doesn't leave a dangling reference that fails compilation.

| Item | `base-layered` | `minimal` |
|---|---|---|
| `common/` infra | included | included |
| `example/` CRUD slice + MapStruct | included | included |
| Liquibase migrations | included | excluded |
| Testcontainers repository test | included | excluded |
| Postgres / `docker-compose.yml` | included | included |
| springdoc-openapi, Actuator | included | included |
| Generated CI workflow | included | included |

### Frontend: `base` (unchanged) vs `minimal`

`minimal` excludes:
- The sample CRUD dashboard (`/` route and its page component)
- The mock/real API client (`VITE_API_MODE` switch and both
  implementations)
- TanStack Query hooks
- react-hook-form + zod wired demo form logic (the Shadcn `form.tsx`
  *component* itself is retained since the full component set is kept)

Everything else is retained: the full 16-component Shadcn set, the
`/components` showcase page, routing, theme tokens, static pages
(404/error/loading/empty-state), and date/currency formatters.

`package.json` (a shared file) needs its `@tanstack/react-query`,
`react-hook-form`, and `zod` dependency entries wrapped in a Jinja2
conditional keyed off a new `template_context()` boolean
(`include_data_fetching`), derived the same way as backend's `use_liquibase`.

Implementation-time check required: confirm the retained `/components`
showcase page's demo data doesn't route through the excluded mock/real API
client (it currently uses inline mock data per the existing template, so
this should already hold — verify at implementation time).

| Item | `base` | `minimal` |
|---|---|---|
| Routing, theme tokens, static pages | included | included |
| Shadcn component set (all 16) + `/components` showcase | included | included |
| Sample CRUD dashboard (`/`) | included | excluded |
| Mock/real API client | included | excluded |
| TanStack Query hooks | included | excluded |
| react-hook-form + zod wired demo | included | excluded (component stays, wiring doesn't) |
| date/currency formatters | included | included |
| Generated CI workflow | included | included |

## Validation & testing

- `check_structure` receives the per-template filtered expected-paths list
  described above; no other validator logic changes.
- `run_compile` / `run_build` need no changes — they operate on whatever
  got rendered.
- **New test: manifest sanity.** For each registered template's `EXCLUDES`,
  assert every pattern matches at least one real file under `_shared`.
  Guards against a stale/typo'd glob silently excluding nothing after
  `_shared` is restructured.
- **New test: renderer exclude filtering.** Fixture template tree +
  `excluded` patterns → confirm `resolve_tree`/`render_tree` drop exactly
  the matched paths and leave the rest untouched.
- **Existing `test_generation.py` parametrized** over registered template
  names instead of testing one hardcoded template — each variant gets a
  real render + structural check + real `mvn test-compile` / `npm run
  build`+`tsc`+design-token check. Accepted cost: roughly doubles the
  slowest part of each package's CI run.
- **New CLI test:** `--template` defaults to the current template name
  (backward compatible with existing invocations), rejects an unregistered
  name via Click's `Choice` validation before the renderer runs, and the
  wizard prompts for it when omitted.

No new runtime error handling beyond Click's `Choice` validation, which
already rejects an invalid `--template` value before `cli.py`'s pipeline
starts.

## Documentation updates (part of this feature's scope)

- `CLAUDE.md` (repo-level) — update both packages' Architecture sections:
  replace "no template-selection concept yet" with a description of the
  registry + `--template` flag + `_shared`/manifest structure.
- `backend/README.md`, `frontend/README.md`, and each package's
  `QUICK_REFERENCE.md` — document `--template {base-layered,minimal}` /
  `--template {base,minimal}`, plus an include/exclude table (as above) so
  a user can pick the right template without reading source.
- `CONTRIBUTING.md` — document the pattern for adding a new template:
  create `templates/<name>/manifest.py` with an `EXCLUDES` tuple, and if
  the template needs shared-file content to differ (not just presence),
  add a corresponding `template_context()` boolean flag.
- Each package's `CHANGELOG.md` `[Unreleased]` section — bullet describing
  the new `--template` flag and the `minimal` template, per this repo's
  existing changelog convention.

## Out of scope

- Templates that add or override files rather than only excluding them
  (`auth`, `reactive`, `admin`, `landing` from earlier brainstorming) —
  deferred to a future spec once the additive-overlay mechanism is needed.
- Any change to the existing "abort if target directory exists" behavior.
- A non-interactive/CI mode flag (`--yes`) — a separate, previously
  discussed idea, not bundled into this change.
