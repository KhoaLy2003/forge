# Quick Reference (Forge, backend)

Full guide: [README.md](README.md).

## Commands

| Command | What it does |
|---|---|
| `forge init` | Writes a commented `forge.yaml` into the current folder. Refuses to overwrite. |
| `forge new` | Generates the project described by `./forge.yaml`. No options. |
| `forge new --verbose` | Same, with full tracebacks on failure. |

```bash
.venv\Scripts\forge init
# edit forge.yaml
.venv\Scripts\forge new
```

## `forge.yaml`

```yaml
project_name: my-service          # required; lowercase, digits, hyphens; starts with a letter
target_path: C:\projects          # required; parent folder for the project
group_id: com.example             # required; dot-separated lowercase, no Java keywords
artifact_id: my-service           # required; lowercase, digits, hyphens; starts with a letter
template: base-layered            # optional; base-layered (default) or minimal
# entities:                       # optional; your own model (base-layered only), see README section 5
```

Unknown keys are an error. Relative and `~` paths in `target_path` are resolved.

## Templates

| Template | Use it for |
|---|---|
| `base-layered` (default) | Full reference project: Liquibase, notifications, observability, entities |
| `minimal` | No Liquibase, no notifications, no monitoring stack; sample `Example` slice only |

## What `forge new` does

1. Reads and validates `forge.yaml`. Problems are listed together; nothing is written.
2. Prints the resolved values.
3. Aborts if `<target_path>\<project_name>` already exists. No overwrite, no merge.
4. Shows the file tree and asks `Generate this project? [y/N]`.
5. Writes the project.
6. Checks: expected files, observability files (skipped for `minimal`), then `mvn test-compile`.
7. On a failed check, asks whether to delete the generated folder.
8. On success, prints `cd`, `docker compose up -d`, `mvn spring-boot:run`.

## After generation

```bash
cd <generated-project>
docker compose up -d
mvn spring-boot:run
```

The sample entity is at `/api/v1/examples` (`GET`, `GET /{id}`, `POST`,
`PUT /{id}`, `DELETE /{id}`). Ids are UUIDs. Responses use a
`{success, message, data}` envelope.

```bash
curl http://localhost:8080/api/v1/examples
curl -X POST http://localhost:8080/api/v1/examples -H "Content-Type: application/json" -d "{\"name\":\"test\"}"
```

Swagger UI: http://localhost:8080/swagger-ui.html
Health: http://localhost:8080/actuator/health

## Forge's own tests

```bash
.venv\Scripts\pytest backend/tests -v
```

Needs `mvn` on `PATH` for the generation tests. Docker is not needed: those
tests compile the generated project, they do not run its repository tests.
