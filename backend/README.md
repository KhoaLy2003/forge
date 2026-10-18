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
- A database-outbox notification module *(`base-layered` only)*: in-app inbox
  and email (SMTP) with templates, retries with backoff, idempotency keys,
  per-recipient preferences and an inbox REST API under
  `/api/v1/notifications`. It has no user model of its own — you provide a
  `RecipientDirectory` (email/locale lookup) and a `CurrentRecipientProvider`
  (who is calling) and can add channels by implementing `ChannelSender`;
  without them email is skipped and the API answers `401`
- Observability per the cross-project standard: structured ECS JSON logs in
  the `prod` profile, a validated `X-Correlation-ID` stored as `request_id`,
  one `http.request.completed` event per request (route template only — never
  query strings, headers or bodies), a `JobContext` helper for scheduled
  work, masking of sensitive log members, and `docs/observability/logging.md`.
  `base-layered` also gets Prometheus metrics on a separate management port,
  a `docker-compose.observability.yml` overlay (Prometheus, Grafana, Loki,
  Alloy), starter alerts and dashboard under `observability/`, and a
  `docs/observability/runbook.md`
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
| Structured logging, request log, correlation, redaction, `logging.md` | included | included |
| Notification module (outbox, in-app + email, inbox API, `002` migration) | included | excluded |
| Prometheus metrics, `observability/` stack, alerts, dashboard, runbook | included | excluded |

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

## Entities (`forge.yaml`)

Instead of the built-in `example` slice you can have Forge generate your own
entities. Describe them in a `forge.yaml`, or let the interactive wizard ask
for them and save the file for you. Entities require the `base-layered`
template (`minimal` has no Liquibase); `template: minimal` plus entities is an
error.

```yaml
project_name: shop-service        # optional: any of project_name, target_path,
group_id: com.example             #   group_id, artifact_id, template may be given here
artifact_id: shop-service
entities:
  Customer:
    fields:
      name:   { type: string, length: 100, required: true }
      email:  { type: string, unique: true, required: true }
      status: { type: enum, values: [ACTIVE, SUSPENDED] }
  Order:
    table: customer_orders          # optional; default = snake_case plural
    fields:
      total:    { type: decimal, precision: 12, scale: 2, required: true }
      placedAt: { type: instant }
    relations:
      customer: { type: many-to-one, target: Customer, required: true, inverse: orders }
      items:    { type: one-to-many, target: OrderItem, mappedBy: order }
  OrderItem:
    fields:
      quantity: { type: int, required: true }
    relations:
      order: { type: many-to-one, target: Order, required: true }
  Product:
    fields:
      name: { type: string, required: true }
    relations:
      categories: { type: many-to-many, target: Category }
  Category:
    fields:
      name: { type: string, required: true }
```

Field types: `string` (`length`, or `text: true`), `int`, `long`, `decimal`
(`precision` and `scale` required), `boolean`, `date`, `instant`, `uuid`,
`enum` (`values` required, UPPER_SNAKE_CASE). Common modifiers: `required`,
`unique`, `default`. Unknown keys in the file are rejected.

Each entity's list endpoint (`GET /api/v1/<plural>`) also takes optional filter
query parameters, generated from the model, next to `page`, `size`, `sortBy`
and `sortDirection`. Soft-deleted rows are always excluded.

| Field type | Query parameters | Match |
|---|---|---|
| `string` | `name` | case-insensitive contains (`%` and `_` are literal) |
| `int`, `long`, `decimal`, `date`, `instant` | `totalFrom`, `totalTo` | inclusive range; dates are `2026-01-31`, instants ISO-8601 |
| `boolean`, `uuid`, `enum` | `active` | exact |
| `many-to-one`, `one-to-one` | `customerId` | related id |

Only fields in the model can be filtered, and `many-to-many` relations are not
filterable. A field whose name collides with a list parameter (`size`, `page`,
`sortBy`, `sortDirection`) is exposed as `filterSize` etc. The code lives in
`<Entity>Filter` (a record whose `toSpecification()` feeds the repository's
`JpaSpecificationExecutor`) and `common/search/SearchSpecifications`.

```bash
.venv\Scripts\forge new --from forge.yaml
.venv\Scripts\forge new --from forge.yaml --name other-name --path C:\projects
```

**Precedence**, per parameter: an explicit CLI flag, then the value in the
file, then the wizard prompt. A `template:` in the file overrides the
`base-layered` default but never an explicit `--template` (including an
explicit `--template base-layered`). If the file supplies all four of project
name, target path, group id and artifact id, nothing is prompted. A missing,
unreadable or invalid file exits with code 1 (naming the file and the key
path of every problem) and writes nothing.

**Interactive entity step.** When the wizard had to prompt for at least one of
the four project parameters, the template is `base-layered`, and `--from`
supplied no entities, it also offers "Add an entity?" (fields with their type,
`required` and type-specific attributes, then relations to previously declared
entities). Each answer is checked live with the same rules as the file. Flag-complete and
`--from`-complete runs never get this step, so scripts and CI are not blocked
on a prompt. After a successful generation you are asked "Save the model as
forge.yaml?"; yes writes `<generated project>/forge.yaml`. `inverse`,
`mappedBy`, `cascade`, `unique` and `default` are not asked; add them to the
saved file by hand.

**Validation** (everything is checked before anything is written, and every
problem is reported at once): entity names are PascalCase, singular, not a
Java reserved word and not a name used by the generated code; field and
relation names are camelCase, unique per entity and must not collide with the
`BaseEntity` members (`id`, `version`, `createdAt`, `updatedAt`, `deletedAt`);
derived table names that are reserved SQL words (`Order`, `User`, `Group`, ...)
are rejected with a suggested `table:` override; relation targets must exist;
`mappedBy` must name the owning many-to-one of the target; a cycle of
*required* relations is an error (optional ones may form cycles).

**Relation semantics.** `many-to-one` is the owning side: an FK column plus a
`LAZY` `@ManyToOne`. A `one-to-many` is unidirectional by default (the FK
lives on the child; the parent gets no collection); it is bidirectional only
when requested with `mappedBy` on the one-to-many or `inverse: name` on the
many-to-one, and bidirectional pairs get add/remove helpers. `many-to-many` is
declared on exactly one side, which owns a generated join table with a
composite primary key. `one-to-one` is a many-to-one with a unique FK.
`cascade: all` and `orphanRemoval` exist only on a `one-to-many` with
`mappedBy`. All associations are `LAZY`, foreign keys are indexed and use
`ON DELETE RESTRICT`, and DTOs expose related ids rather than nested objects.

Local checks stay Docker-free: Forge compiles the generated project. Only the
generated `*RepositoryTest` classes need Docker (Testcontainers), and they run
in the generated project's CI.

## Development

Run from the repo root:

```bash
.venv\Scripts\pytest backend/tests -v
```

The design spec and implementation plan live under
`../docs/superpowers/specs/` and `../docs/superpowers/plans/`.
