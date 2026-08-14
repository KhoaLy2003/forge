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

Fully non-interactive example:

```bash
.venv\Scripts\forge new --name my-service --path C:\projects --group-id com.example --artifact-id my-service
```

Mixed — only the flags you omit get prompted:

```bash
.venv\Scripts\forge new --name my-service --group-id com.example
```

## What happens on each run

1. Collects parameters (wizard or flags)
2. Aborts immediately if `<path>\<name>` already exists — no overwrite, no merge
3. Shows a text preview of every file/folder that will be created, asks `[y/N]`
4. Writes the project
5. Runs a structural check (expected files present), then `mvn test-compile`
6. If either check fails, prompts to keep or delete the generated folder
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

## Run Forge's own tests

```bash
.venv\Scripts\pytest -v
```

This does **not** require Docker — `test_generation.py` only runs
`mvn test-compile` against the generated project (compiles sources without
running tests). If you want to run the *generated* project's own `mvn test`
(which includes a Testcontainers-backed repository test), that does require
Docker running locally.
