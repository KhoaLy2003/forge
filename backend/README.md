# Forge (backend)

Forge generates a ready-to-build **Java 21 + Spring Boot 4 + PostgreSQL**
project. You describe the project in one small file, `forge.yaml`, and Forge
creates the whole Maven project from it, checks that it compiles, and tells
you the next commands to run.

## Contents

1. [Prerequisites](#1-prerequisites)
2. [Install](#2-install)
3. [Step-by-step guide](#3-step-by-step-guide)
4. [`forge.yaml` reference](#4-forgeyaml-reference)
5. [Your own entities](#5-your-own-entities)
6. [Templates](#6-templates)
7. [What gets generated](#7-what-gets-generated)
8. [Run the generated project](#8-run-the-generated-project)
9. [Troubleshooting](#9-troubleshooting)
10. [Development](#10-development)

---

## 1. Prerequisites

| Needed for | Tool | Notes |
|---|---|---|
| Running Forge | Python **3.11+** | `py --version` to check |
| Forge's compile check | Maven 3.9+ on `PATH` | `mvn -v` to check |
| The generated project | JDK **21** | `java -version` to check |
| The generated project | Docker (with Compose) | local PostgreSQL; not needed to generate |

Forge does not need Docker to generate a project. Docker is needed only to run
the generated project's database and its Testcontainers tests.

## 2. Install

Run from the repository root, in a virtual environment:

```bash
py -m venv .venv
.venv\Scripts\pip install -e "./backend[dev]"
```

This installs the `forge` command into `.venv`. Check it:

```bash
.venv\Scripts\forge --help
```

You should see the two commands, `init` and `new`.

## 3. Step-by-step guide

Forge reads its settings only from `forge.yaml` in the folder where you run it.
There are no options to remember or type.

### Step 1 — Create the project file

Go to the folder where you want the new project to appear, then run:

```bash
cd C:\projects
forge init
```

Output:

```
Created C:\projects\forge.yaml. Edit it, then run "forge new".
```

`forge init` writes a commented starter file. It never overwrites an existing
`forge.yaml`; if one is already there, it stops and changes nothing.

### Step 2 — Edit `forge.yaml`

Open the file and set your values:

```yaml
project_name: order-service
target_path: C:\projects
group_id: com.example
artifact_id: order-service
template: base-layered
```

See [section 4](#4-forgeyaml-reference) for what each key means.

### Step 3 — Generate

```bash
forge new
```

Forge then:

1. Reads and validates `forge.yaml`. Every problem is listed at once, and
   nothing is written if any exist.
2. Prints the values it will use:

   ```
   Config:   C:\projects\forge.yaml
   Project:  order-service
   Target:   C:\projects\order-service
   Group:    com.example
   Artifact: order-service
   Template: base-layered
   ```

3. Shows a preview of every file and folder it will create, and asks
   `Generate this project? [y/N]`. Answer `n` to cancel without writing anything.
4. Writes the project.
5. Runs the checks: expected files present, observability files valid, and
   `mvn test-compile` on the new project. If a check fails, Forge explains why
   and asks whether to delete the half-built folder.

On success it prints:

```
Project generated successfully!
cd C:\projects\order-service
docker compose up -d
mvn spring-boot:run
```

### Step 4 — Run it

Follow [section 8](#8-run-the-generated-project).

### Changing a project after generation

`forge new` never merges into or overwrites an existing folder. To regenerate,
delete or rename the existing project folder first, or change `project_name`
in `forge.yaml`.

---

## 4. `forge.yaml` reference

| Key | Required | Default | Allowed values | Meaning |
|---|---|---|---|---|
| `project_name` | yes | — | lowercase letters, digits, hyphens; starts with a letter | Name of the project folder and the default app name. |
| `target_path` | yes | — | any path; `~` and relative paths are resolved | Folder the project folder is created in. `.` means the folder containing `forge.yaml`. |
| `group_id` | yes | — | dot-separated lowercase segments, e.g. `com.example`; no Java keywords | Maven group id; becomes the base Java package. |
| `artifact_id` | yes | — | lowercase letters, digits, hyphens; starts with a letter | Maven artifact id. |
| `template` | no | `base-layered` | `base-layered`, `minimal` | Which template to generate. See [section 6](#6-templates). |
| `entities` | no | — | see [section 5](#5-your-own-entities) | Your own domain model. Omit it to get the sample `Example` slice. |

Rules:

- Unknown keys are an error. A misspelled key (such as `groupId`) is reported
  by name rather than silently ignored.
- Windows paths work as written, for example `target_path: C:\projects`.
- A value that is empty (`group_id:` with nothing after it) counts as missing.

Example with every top-level key:

```yaml
project_name: order-service
target_path: C:\projects
group_id: com.example
artifact_id: order-service
template: base-layered
entities:
  # see section 5
```

---

## 5. Your own entities

By default the generated project contains one sample entity, `Example`. To
generate your own entities instead, add an `entities:` block to `forge.yaml`.
Entities need the `base-layered` template, because `minimal` has no Liquibase
migrations. Combining `template: minimal` with `entities` is an error.

```yaml
entities:
  Customer:
    fields:
      name:   { type: string, length: 100, required: true }
      email:  { type: string, unique: true, required: true }
      status: { type: enum, values: [ACTIVE, SUSPENDED] }
  Order:
    table: customer_orders          # optional; default is a snake_case plural
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

### Field types

| Type | Extra keys | Notes |
|---|---|---|
| `string` | `length` (default 255) or `text: true` | `length` and `text` cannot be combined |
| `int` | — | |
| `long` | — | |
| `decimal` | `precision` and `scale` (both required) | `scale` must not exceed `precision` |
| `boolean` | — | |
| `date` | — | |
| `instant` | — | |
| `uuid` | — | |
| `enum` | `values` (required) | UPPER_SNAKE_CASE values, unique, at most the length limit |

Common keys on any field: `required`, `unique`, `default`.

### Relation types

| Type | Meaning |
|---|---|
| `many-to-one` | The owning side: a foreign-key column. Optional `inverse: <name>` adds a back-reference collection on the target. |
| `one-to-many` | Unidirectional by default: the foreign key lives on the child, and the parent has no collection. Bidirectional only with `mappedBy: <many-to-one name on the child>`. |
| `many-to-many` | Declared on one side only; that side owns a generated join table. `required` is not allowed. |
| `one-to-one` | A many-to-one with a unique foreign key. |

`cascade: all` and `orphanRemoval: true` are allowed only on a `one-to-many`
with `mappedBy`. All associations are `LAZY`, foreign keys are indexed and use
`ON DELETE RESTRICT`, and DTOs expose related ids rather than nested objects.

### Validation

Every rule is checked before anything is written, and all problems are listed
together:

- Entity names are PascalCase and singular, not Java reserved words, and not
  names the generated code already uses.
- Field and relation names are camelCase, unique within their entity, and must
  not collide with `BaseEntity` members (`id`, `version`, `createdAt`,
  `updatedAt`, `deletedAt`).
- A derived table name that is a reserved SQL word (`Order`, `User`, `Group`,
  ...) is rejected. Set `table:` to fix it, as `Order` does above.
- Relation targets must exist in the file.
- `mappedBy` must name the many-to-one on the target that owns the relation.
- A cycle of *required* relations is an error. Optional cycles are allowed.

---

## 6. Templates

| | `base-layered` (default) | `minimal` |
|---|---|---|
| `common/` infrastructure, `example/` CRUD slice, MapStruct | included | included |
| Liquibase migrations | included | excluded — schema left to JPA `ddl-auto: update` |
| Testcontainers-backed repository test | included | excluded |
| PostgreSQL in `docker-compose.yml`, springdoc-openapi, Actuator | included | included |
| Structured logging, request log, correlation, redaction, `logging.md` | included | included |
| Notification module (outbox, in-app + email, inbox API, `002` migration) | included | excluded |
| Prometheus metrics, `observability/` stack, alerts, dashboard, runbook | included | excluded |
| Entities (`entities:` in `forge.yaml`) | supported | not supported |

---

## 7. What gets generated

- **Stack:** Java 21, Spring Boot 4, Maven, PostgreSQL 16.
- **Packages:**
  - `common/` — `BaseEntity` (UUID id, audit timestamps, optimistic locking,
    soft delete), the `ApiResponse` / `PageResponse` envelope, global exception
    handling, a correlation-ID filter, OpenAPI config, shared utilities.
  - `example/` (or your entities) — entity, DTO, mapper, repository, service,
    controller, wired end-to-end.
- **Data:** DTOs with Bean Validation and MapStruct mapping, so entities are
  never exposed over HTTP. Liquibase migrations (`base-layered`).
- **Notifications** (`base-layered`): a database-outbox module with in-app
  inbox and email (SMTP), retries with backoff, idempotency keys and an inbox
  API under `/api/v1/notifications`. It has no user model of its own; you
  provide a `RecipientDirectory` and a `CurrentRecipientProvider`. Without
  them, email is skipped and the API answers `401`.
- **Observability:** ECS JSON logs in the `prod` profile, a correlation id
  stored as `request_id`, one structured event per request, masking of
  sensitive fields. `base-layered` also adds Prometheus metrics, a
  `docker-compose.observability.yml` overlay (Prometheus, Grafana, Loki,
  Alloy), starter alerts and a dashboard, and a runbook.
- **Tests:** unit tests (Mockito), a `@WebMvcTest` slice, and a Testcontainers
  repository test (`base-layered`). A JaCoCo gate requires 90% line coverage on
  `mvn verify`.
- **CI:** `.github/workflows/ci.yml` runs `mvn verify`, Spotless format check,
  CodeQL, a Trivy scan, PR dependency review and zizmor. The dependency-review
  job needs Dependabot and vulnerability alerts enabled on your GitHub repo.

---

## 8. Run the generated project

```bash
cd C:\projects\order-service
docker compose up -d        # starts PostgreSQL
mvn spring-boot:run         # starts the app
```

Then open:

- Swagger UI: `http://localhost:8080/swagger-ui.html`
- Health: `http://localhost:8080/actuator/health`

Run the tests with `mvn verify`. The repository tests need Docker running.

---

## 9. Troubleshooting

| Message | Cause | Fix |
|---|---|---|
| `No forge.yaml found in … Run "forge init" first.` | You ran `forge new` in a folder without the file | `cd` to the folder with `forge.yaml`, or run `forge init` there |
| `Invalid …forge.yaml:` followed by `- key: missing` | A required key is absent or empty | Set the key listed |
| `- <key>: unknown key …` | Misspelled or unsupported key | Fix the spelling; see [section 4](#4-forgeyaml-reference) |
| `Error: target directory already exists` | `target_path/project_name` already exists | Delete or rename that folder, or change `project_name` |
| `Error: <file> already exists` on `init` | `forge.yaml` is already there | Keep it, or delete it and run `init` again |
| `Validation failed: …` (structural or observability) | The generated project is missing a file or has a bad monitoring file | Read the details printed under the message; regenerate after fixing the cause |
| `Validation failed: mvn test-compile failed` | The generated project does not compile | Read the Maven output; delete the folder and regenerate after fixing the cause |
| `Validation failed: mvn executable not found on PATH` | Maven is not installed or not on `PATH` | Install Maven 3.9+ and reopen the terminal |
| `Invalid entity model:` | Entity rules failed | Read each listed line, fix it in `forge.yaml` (see [section 5](#5-your-own-entities)) |

---

## 10. Development

Run from the repository root:

```bash
.venv\Scripts\pytest backend/tests -v
```

`mvn` must be on `PATH` for `backend/tests/test_generation.py` and the compile
check, because both build a real Maven project.

Design specs and implementation plans live under
[`../docs/superpowers/specs/`](../docs/superpowers/specs/) and
[`../docs/superpowers/plans/`](../docs/superpowers/plans/). Version history is
in [CHANGELOG.md](CHANGELOG.md); a command and key cheat sheet is in
[QUICK_REFERENCE.md](QUICK_REFERENCE.md).
