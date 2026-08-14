# Forge

Forge scaffolds a ready-to-build Java + Spring Boot 4 + PostgreSQL project
from a single template, so starting a new service is faster than copying an
old project by hand.

## What it generates

- Java 21, Spring Boot 4, Maven
- Liquibase migrations
- docker-compose for local PostgreSQL
- A layered package structure (`controller/`, `service/`, `repository/`,
  `entity/`) with one example entity wired end-to-end (full CRUD)

## Install

```bash
py -m venv .venv
.venv\Scripts\pip install -e ".[dev]"
```

## Usage

```bash
.venv\Scripts\forge new
```

Run without flags to be walked through an interactive wizard (project name,
target path, group id, artifact id). Any flag you pass skips its prompt:

```bash
.venv\Scripts\forge new --name my-service --path C:\projects --group-id com.example --artifact-id my-service
```

Forge shows a preview of the file tree it's about to write and asks for
confirmation before touching disk. After generation it runs a structural
check and `mvn compile` against the new project, and reports next steps.

See [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for command details, and
[CHANGELOG.md](CHANGELOG.md) for version history.

## Development

```bash
.venv\Scripts\pytest -v
```

The design spec and implementation plan live under
`docs/superpowers/specs/` and `docs/superpowers/plans/`.
