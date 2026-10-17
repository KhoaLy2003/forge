# Quick Reference

## Generate a project

```bash
.venv\Scripts\forge new
```

Prompts for anything not passed as a flag:

| Flag | Prompt it skips | Example |
|---|---|---|
| `--name` | Project name | `my-service` |
| `--path` | Target path (parent directory) | `C:\projects` |
| `--group-id` | Group id | `com.example` |
| `--artifact-id` | Artifact id | `my-service` |
| `--template` | *(not wizard-prompted — see below)* | `base-layered` or `minimal` |

`--template` is not part of the wizard/prompt table above — it always
defaults to `base-layered` if you don't pass it, so an invocation with
every other flag supplied still runs non-interactively without a prompt.

Fully non-interactive example:

```bash
.venv\Scripts\forge new --name my-service --path C:\projects --group-id com.example --artifact-id my-service --template minimal
```

Mixed — only the flags you omit get prompted:

```bash
.venv\Scripts\forge new --name my-service --group-id com.example
```

## Generate from a `forge.yaml` (entities)

```bash
.venv\Scripts\forge new --from forge.yaml
```

| Flag | Meaning |
|---|---|
| `--from PATH` | Read project parameters (`project_name`, `target_path`, `group_id`, `artifact_id`, `template`) and `entities` from a YAML file |

Precedence per parameter: explicit CLI flag > value in the file > wizard
prompt. `template:` in the file beats the `base-layered` default but not an
explicit `--template`. Entities need `base-layered`; `minimal` + entities is an
error (exit 1). A missing/invalid file or invalid entity set exits 1 and
writes nothing; all problems are listed together.

In an interactive run (the wizard prompted for a project parameter), on
`base-layered` and with no `--from` entities, the wizard asks "Add an
entity?" and afterwards "Save the model as forge.yaml?" (writes
`<project>/forge.yaml` after a successful generation). Flag-complete and
`--from`-complete runs never get these prompts. Format, field types and
relation semantics: see "Entities" in [README.md](README.md).

## What happens on each run

1. Collects parameters (wizard or flags)
2. Aborts immediately if `<path>\<name>` already exists — no overwrite, no merge
3. Shows a text preview of every file/folder that will be created, asks `[y/N]`
4. Writes the project
5. Runs a structural check (expected files present), then an observability
   check (monitoring files parse, and every metric in the alerts/dashboard is
   one the app exposes — static, no Docker; skipped for `minimal`), then
   `mvn test-compile`
6. If any check fails, prompts to keep or delete the generated folder
7. On success, prints `cd`, `docker compose up -d`, and `mvn spring-boot:run`

## After generation

```bash
cd <generated-project>
docker compose up -d
mvn spring-boot:run
```

The example entity is exposed at `/api/v1/examples` (`GET`, `GET /{id}`,
`POST`, `PUT /{id}`, `DELETE /{id}`). Ids are UUIDs, not `Long`s. Every
response is wrapped in a common `{success, message, data}` envelope, and the
list endpoint additionally wraps its `data` in a paginated `{data, pagination}`
shape:

```json
{
  "success": true,
  "message": "Examples retrieved successfully",
  "data": {
    "data": [{ "id": "...", "name": "sample", "status": "ACTIVE", "createdAt": "...", "updatedAt": "...", "version": 0 }],
    "pagination": { "page": 0, "size": 20, "totalElements": 1, "totalPages": 1 }
  }
}
```

```bash
curl http://localhost:8080/api/v1/examples
curl -X POST http://localhost:8080/api/v1/examples -H "Content-Type: application/json" -d "{\"name\":\"test\"}"
curl http://localhost:8080/api/v1/examples/<uuid>
curl -X PUT http://localhost:8080/api/v1/examples/<uuid> -H "Content-Type: application/json" -d "{\"name\":\"updated\",\"status\":\"ACTIVE\"}"
curl -X DELETE http://localhost:8080/api/v1/examples/<uuid>
```

To explore or verify the API without hand-writing curl commands, use Swagger
UI (http://localhost:8080/swagger-ui.html) or Actuator health
(http://localhost:8080/actuator/health).

## Notifications (`base-layered` only)

Send with `NotificationService.enqueue(...)`; recipients are opaque ids. To enable email,
implement `RecipientDirectory` and set `MAIL_HOST` (plus `MAIL_PORT`/`MAIL_USERNAME`/
`MAIL_PASSWORD`/`MAIL_FROM`); to enable the inbox API, implement `CurrentRecipientProvider`
(otherwise it answers `401`). Add templates with a Liquibase migration. Full guide: the
"Notifications" section of the generated project's README.

## Run Forge's own tests

```bash
.venv\Scripts\pytest -v
```

This does **not** require Docker — `test_generation.py` only runs
`mvn test-compile` against the generated project (compiles sources without
running tests). If you want to run the *generated* project's own `mvn test`
(which includes a Testcontainers-backed repository test), that does require
Docker running locally. For generated entity slices the same applies: only
the generated `*RepositoryTest` classes need Docker, and they run in the
generated project's CI.
