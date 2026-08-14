# Forge — Java/Spring Boot Project Scaffolding Tool — Design

## Goal

Speed up the "init source code" phase for new services by generating a
ready-to-build Java + Spring Boot + PostgreSQL project from a template,
instead of creating it by hand. Faster than manual setup *and* trustworthy
enough that people use it instead of copy-pasting an old project.

## Name

**Forge.**

## Tech Stack (generated projects)

- Java 21
- Spring Boot 4
- PostgreSQL
- Maven (v1 supports Maven only; Gradle is out of scope for v1)
- Liquibase for DB migrations
- docker-compose for local PostgreSQL

## Tooling (the generator itself)

- Python CLI built with Typer
- Jinja2 for templating (custom renderer, not Cookiecutter/Copier — see
  Architecture)

## Scope (v1)

Forge targets **monolith** projects, not microservices. The base template
uses a **pure layered** package structure (`controller/`, `service/`,
`repository/`, `entity/` as top-level packages). Package-by-feature
("module package as top level", each feature owning its own layered
sub-packages) is a noted **future** option, not built in v1.

v1 ships exactly one template: `base-layered`, including Liquibase
migrations and a `docker-compose.yml` for local Postgres. No feature-module
system (Kafka, Redis, security, testcontainers) exists in v1 — these are
explicitly deferred, and the template/module-layering architecture to
support them is not designed yet.

### Entity/domain classes

Forge does **not** collect entity definitions (names, fields) during the
wizard. The base template ships with a single example entity (e.g.
`Example`) with full wiring across all four layers — `controller/`,
`service/`, `repository/`, `entity/` — plus a matching Liquibase migration.
This gives the generated project a working end-to-end request path
(a real CRUD flow that boots, compiles, and hits Postgres) that the user
copies as the pattern for their own domain classes. A wizard-driven
multi-entity/field schema generator (per-entity CRUD scaffolding) is
explicitly deferred — it would need its own field-type schema and
significantly more template logic than v1's scope calls for.

## Architecture

Forge is a Python CLI (Typer) that renders a base Jinja2 template tree into
a new Maven-based Spring Boot project. Flow: interactive wizard collects
parameters → tree preview shown for confirmation → files written to disk →
structural + compile validation → next-steps output.

Templating is a **custom Jinja2 renderer** built directly for this tool
(not Cookiecutter or Copier), because Forge's preview/progress/validation
hooks need tighter control over the render pipeline than those libraries'
prompt/hook models comfortably allow. This is more code to own but avoids
fighting a framework's assumptions for a fairly small template surface
area (one base template in v1).

## Components

```
forge/
  README.md
  CHANGELOG.md
  QUICK_REFERENCE.md
  cli.py                    # Typer entry point (`forge new`)
  core/
    config_schema.py        # Pydantic model — single source of truth for params
    wizard.py                # interactive prompts for missing params
    tree_preview.py          # renders resolved tree, prompts y/n
    progress.py              # step tracker / status printer
    renderer.py              # Jinja2 rendering engine, writes to disk
    validator.py             # structural + compile checks
  templates/
    base-layered/            # the only v1 template
  tests/
    test_generation.py       # generates into tmpdir, asserts structural+compile pass
```

- **`cli.py`** — entry point, `forge new` command. Uses flags if given,
  otherwise falls back to the wizard for anything missing.
- **`core/config_schema.py`** — Pydantic model defining all wizard-collected
  parameters: project name, target path, group id, artifact id. Java
  version (21) and Spring Boot version (4) are fixed constants baked into
  the `base-layered` template, not wizard-collected parameters — v1 has
  exactly one supported stack, so there's nothing to choose. All other
  components read from this schema rather than duplicating parameter
  definitions.
- **`core/wizard.py`** — interactive prompts (Typer prompt support) for any
  parameter not passed as a CLI flag, validating each against
  `config_schema` as entered (e.g. rejects malformed Maven group id
  immediately and re-prompts).
- **`core/tree_preview.py`** — resolves the template tree (post-Jinja2 name
  resolution, pre-write), prints it as text, asks the user y/n to proceed.
- **`core/progress.py`** — prints step-by-step status while generation
  runs.
- **`core/renderer.py`** — walks `templates/base-layered/`, applies Jinja2
  to file/folder names and file contents, writes to the target path. If
  the target folder already exists, aborts immediately with a clear error
  before any writes occur (no merge, no auto-overwrite, no prompt at this
  stage).
- **`core/validator.py`** — v1 runs two checks, in order: structural
  (expected files exist) and compile (`mvn compile` in the generated
  project directory, capturing output on failure). No boot smoke test and
  no DB connectivity check in v1.
- **`templates/base-layered/`** — Maven, layered packages, Liquibase
  migrations, `docker-compose.yml` for local Postgres.
- **`tests/test_generation.py`** — generates a project into a tmpdir by
  passing all parameters directly (bypassing the wizard), then asserts
  structural + compile validation both pass. This is Forge's own
  regression safety net against template drift.

## Data Flow & Error Handling

1. User runs `forge new` (with or without flags).
2. Wizard fills in any missing parameters, validating each as entered.
3. Forge checks the target path. If it already exists, **abort
   immediately** with a clear error message — no partial writes, no
   prompt, no merge/overwrite behavior in v1.
4. `renderer` resolves the template tree in memory and hands it to
   `tree_preview`, which prints the tree and asks y/n.
5. On "no": exit cleanly, no filesystem changes made.
   On "yes": `renderer` writes files to disk while `progress` prints
   per-step status.
6. `validator` runs the structural check, then `mvn compile`.
   - If either check fails, Forge reports the failure clearly (including
     captured Maven output on compile failure), then **prompts the user**
     to keep the generated folder for debugging or delete it. Forge never
     decides this automatically.
   - If both pass, continue to step 7.
7. On success, print next-steps: `cd` command, `docker compose up -d`,
   `mvn spring-boot:run`, and the generated DB URL/credentials.

## Testing

`tests/test_generation.py` generates a project into a tmpdir via direct
parameters (no wizard interaction) and asserts structural + compile
validation both pass, using `mvn compile` (not `package`/`install` — v1
deliberately keeps this fast and avoids depending on the generated
template's own test suite being valid). This same `mvn compile` check is
what `validator.py` runs live against real user-generated projects, so the
test suite and production behavior stay in sync by construction.

## Explicitly Out of Scope for v1

- Gradle support
- Hexagonal/DDD and package-by-feature layouts
- Feature-module system (Kafka, Redis, security, testcontainers)
- Wizard-driven multi-entity/field schema generation (per-entity CRUD
  scaffolding beyond the single example entity)
- Boot smoke test and DB connectivity validation
- Overwrite/merge behavior for existing target folders (`--force` flag,
  interactive overwrite) — v1 always aborts on an existing folder
- `mvn clean package` / `mvn clean install` as the validation command

## Open Questions Resolved

All open questions from the original plan draft are now resolved:

| Question | Decision |
|---|---|
| Maven or Gradle? | Maven only (v1) |
| Default package structure? | Pure layered |
| Optional modules in v1? | No — base template + Liquibase + docker-compose only |
| Behavior on existing target folder? | Abort immediately with clear error |
| Final name? | Forge |
| DB migration tool? | Liquibase |
| Parameter input mode? | Interactive wizard by default, flags to skip |
| Validation scope for v1? | Structural + compile only |
| Templating approach? | Custom Jinja2 renderer |
| Validation command? | `mvn compile` |
| Behavior on validation failure? | Prompt user to keep or delete the generated folder |
| Multiple entity/domain classes? | Ship one example entity as a full-stack pattern; no multi-entity wizard in v1 |
| Java/Spring Boot version selectable? | No — fixed constants (Java 21, Spring Boot 4), not a wizard parameter |
