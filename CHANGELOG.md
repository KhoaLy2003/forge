# Changelog

## 0.1.0 — 2026-08-13

Initial release.

- `forge new` command: interactive wizard, tree preview with confirmation,
  Jinja2-based rendering, structural + `mvn compile` validation
- Single `base-layered` template: Maven, Java 21, Spring Boot 4, Liquibase,
  docker-compose for local PostgreSQL, one example entity with full CRUD
  (Create, Read, Update, Delete) wired across controller/service/repository/
  entity layers
- Abort-before-write if the target directory already exists (no merge or
  overwrite in this version)
- On validation failure, prompts to keep or delete the generated folder
