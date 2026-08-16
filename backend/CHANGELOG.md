## [Unreleased]

## 0.3.0 — 2026-08-16

- Generated projects' `pom.xml` now includes `jacoco-maven-plugin`, gating
  `mvn verify` (and therefore the generated CI workflow) on 90% overall line
  coverage; a coverage-summary step writes the actual percentage to the CI
  run's job summary regardless of pass/fail. The application entry point's
  `main()` and pure bean-wiring `@Configuration` classes (`JpaAuditingConfig`,
  `OpenApiConfig`) are excluded from the gate as untestable framework
  boilerplate; `CorrelationIdFilter` stays in scope since it has real request
  logic. Existing template tests were extended (`GlobalExceptionHandlerTest`,
  `ExampleControllerTest`, `ExampleServiceImplTest`) to close real coverage
  gaps this surfaced (previously-untested `findAll`/`update`/`delete`
  endpoints and not-found/optimistic-lock/data-integrity-violation branches)
  so both `base-layered` and `minimal` clear the gate out of the box.
- This repo's own CI now runs `pytest --cov=core --cov=cli`, gated at 90%
  coverage of the generator's own Python source (`core/`/`cli.py` — not
  `templates/`). A coverage-summary step writes the per-file breakdown to
  the job summary. `main()`'s console-encoding boilerplate is excluded via
  `# pragma: no cover`.
- Added a `--template` flag (`base-layered` [default] / `minimal`) plus the
  registry mechanism behind it: `templates/base-layered/` was split into
  `templates/_shared/` (the file tree) and per-template `manifest.py`
  exclude-glob manifests, discovered by a new `core/templates.py`. `minimal`
  drops Liquibase migrations and the Testcontainers-backed repository test
  while keeping the `example` CRUD slice and MapStruct; `pom.xml` and
  `application.yml` gained `{% if use_liquibase %}` conditionals for the
  content that must differ even though the files themselves are shared.
  `--template` is deliberately not part of the interactive wizard and
  always defaults to `base-layered`, so existing non-interactive,
  flag-complete invocations are unaffected.
- Generated projects now ship a GitHub Actions CI workflow
  (`.github/workflows/ci.yml`): `mvn verify` (build, full Testcontainers-backed
  test suite, Spotless format check), CodeQL (`java-kotlin`, manual build
  mode), a Trivy filesystem scan of `pom.xml`, PR-only dependency review, and
  zizmor linting of the workflow file itself — all actions pinned to commit
  hashes with `persist-credentials: false`
- The generated README notes the one-time setup step (enabling
  Dependabot/vulnerability alerts) the `dependency-review` job requires on
  the user's own GitHub repo
- `EXPECTED_STRUCTURAL_PATHS` updated to include the new workflow file

## 0.2.0 — 2026-08-14

Template rewrite from a flat layer-based package to a feature-based
package structure, plus supporting Forge tooling and documentation changes.

### Template rewrite

- Replaced the flat `controller/service/repository/entity` package with
  `common/` (cross-cutting infrastructure) and `example/` (a self-contained
  domain slice with its own `controller/dto/entity/mapper/repository/service`
  subpackages)
- Added `common/entity/BaseEntity`: UUID primary key, `created_at`/`updated_at`
  timestamps populated via Spring Data JPA auditing, `@Version`-based
  optimistic locking, and soft delete via a `deleted_at` column (no automatic
  query filtering — repositories must expose `*AndDeletedAtIsNull` methods)
- Added `common/dto/ApiResponse`, `PageResponse`, and `PaginationMeta` as a
  standard response envelope, plus request/response DTOs and a MapStruct
  mapper (`ExampleMapper`) for the `example` slice, replacing direct
  entity exposure
- Added `common/exception/GlobalExceptionHandler` for centralized error
  handling, with `ResourceNotFoundException`, `ConflictException`,
  `ErrorDetails`, and `ValidationErrorDetails`
- Added `common/config/CorrelationIdFilter` for correlation-ID-based request
  logging, `JpaAuditingConfig` to enable the auditing listener used by
  `BaseEntity`, and `OpenApiConfig`
- Added `common/util/DateTimeUtils`, `SlugUtils`, and `JsonUtils` utility
  classes, alongside the existing `PaginationUtils`
- Added springdoc-openapi (Swagger UI) and Spring Boot Actuator dependencies
  for API documentation and operational endpoints
- Fixed a startup bug where PGJDBC/Liquibase failed to connect on hosts whose
  OS timezone isn't present in the postgres image's tzdata (e.g.
  `Asia/Saigon`): the generated `Application` class now pins the JVM default
  timezone to UTC in a static initializer that runs before any JDBC
  connection is opened
- Split `application.yml` into base config plus `application-dev.yml` and
  `application-prod.yml` profiles
- Added Testcontainers-backed repository tests (`ExampleRepositoryTest`)
  against a real PostgreSQL container, plus unit/slice tests for the
  controller, service, mapper, exception handler, correlation-ID filter, and
  utility classes
- Reorganized `pom.xml`: introduced versioned properties
  (`mapstruct.version`, `springdoc.version`, `testcontainers-bom.version`,
  `spring-boot-liquibase.version`), added a `testcontainers-bom` import in
  `dependencyManagement` (not otherwise managed by
  `spring-boot-starter-parent:4.0.0`), and grouped dependencies into
  documented blocks (Web & Validation, Persistence & Migration,
  Observability, Boilerplate reduction, API Documentation, Testing)
- Added production-level Javadoc throughout the template's Java classes

### Documentation

- Rewrote the generated project's `README.md` to a production-standard doc
  covering tech stack, prerequisites, project structure (`common/` vs
  `example/` and when to mirror the six subpackages), and getting-started
  steps

### Forge tooling

- `core/validator.py`'s `run_compile` now runs `mvn test-compile` instead of
  `mvn compile`, so generated test sources are compile-checked as well as
  main sources

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
