# Forge

Forge scaffolds a ready-to-build Java + Spring Boot 4 + PostgreSQL project,
so starting a new service is faster than copying an old project by hand.
Two templates are available via `--template` — see [Templates](#templates)
below.

## What it generates

- Java 21, Spring Boot 4, Maven, PostgreSQL 16
- A feature-based package structure:
  - `common/` — cross-cutting infrastructure: a `BaseEntity` (UUID id, audit
    timestamps, optimistic locking, soft delete), the `ApiResponse`/
    `PageResponse` response envelope, global exception handling, a
    correlation-ID filter, OpenAPI config, and shared utilities
  - `example/` — one domain slice (entity/DTO/mapper/repository/service/
    controller) wired end-to-end as a pattern to copy for new features
- DTOs with Bean Validation and MapStruct mapping, so entities are never
  exposed directly over HTTP
- Liquibase Formatted SQL migrations *(`base-layered` template only — see
  [Templates](#templates))*
- docker-compose for local PostgreSQL
- Spring Boot Actuator (health/info) and springdoc-openapi (Swagger UI)
- A test suite covering unit tests (Mockito) and a `@WebMvcTest` slice, plus
  a Testcontainers-backed repository test *(`base-layered` only)* — running
  the generated project's own `mvn test` requires Docker, but Forge's own
  validation only runs `mvn test-compile`, which doesn't
- A JaCoCo coverage gate (90% overall line coverage) bound to `mvn verify`,
  with a per-run coverage summary in CI — framework bootstrap/bean-wiring
  code (`main()`, `JpaAuditingConfig`, `OpenApiConfig`) is excluded as
  untestable boilerplate, everything else counts
- A GitHub Actions CI workflow (`.github/workflows/ci.yml`): `mvn verify`
  (build, test, Spotless format check, coverage gate), CodeQL, a Trivy
  filesystem scan, PR dependency review, and zizmor workflow linting — the
  dependency-review job
  needs Dependabot/vulnerability alerts enabled on your GitHub repo first

## Install

Run from the repo root:

```bash
py -m venv .venv
.venv\Scripts\pip install -e "./backend[dev]"
```

## Templates

| | `base-layered` (default) | `minimal` |
|---|---|---|
| `common/` infra, `example/` CRUD slice, MapStruct | included | included |
| Liquibase migrations | included | excluded — schema left to JPA `ddl-auto: update` |
| Testcontainers-backed repository test | included | excluded |
| Postgres / `docker-compose.yml`, springdoc-openapi, Actuator | included | included |

Pick one with `--template base-layered` or `--template minimal`; the flag
defaults to `base-layered` if omitted (it is **not** part of the interactive
wizard — pass it explicitly, or accept the default, the same way you'd
handle `--verbose`).

## Usage

```bash
.venv\Scripts\forge new
```

Run without flags to be walked through an interactive wizard (project name,
target path, group id, artifact id). Any flag you pass skips its prompt:

```bash
.venv\Scripts\forge new --name my-service --path C:\projects --group-id com.example --artifact-id my-service --template minimal
```

Forge shows a preview of the file tree it's about to write and asks for
confirmation before touching disk. After generation it runs a structural
check and `mvn compile` against the new project, and reports next steps.

See [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for command details, and
[CHANGELOG.md](CHANGELOG.md) for version history.

## Development

Run from the repo root:

```bash
.venv\Scripts\pytest backend/tests -v
```

The design spec and implementation plan live under
`../docs/superpowers/specs/` and `../docs/superpowers/plans/`.
