# Production-Ready Template — Design

## Problem

`templates/base-layered`'s `Example` slice is a toy: the controller returns
the JPA entity directly, there is no validation, no DTO/mapping layer, error
handling is a single `NoSuchElementException → 404` mapping with no body, and
there are zero tests. Forge is meant to scaffold a project that already looks
like production Spring Boot code, not a bare CRUD tutorial. This design
rewrites the `Example` vertical slice and its supporting configuration to
match the conventions in the `java-spring-boot` skill.

## Scope

In scope: the `Example` entity and everything around it (DTOs, mapper,
service, repository, controller, exceptions), cross-cutting `common/`
infrastructure (base entity, API envelope, exception handling, correlation
ID, OpenAPI config), `pom.xml` dependencies, `application*.yml` profiles, and
the generated project's test suite. Also in scope: updating Forge's own
`cli.py` (`EXPECTED_STRUCTURAL_PATHS`) and `config_schema.py` if new template
variables are needed.

Out of scope (explicitly deferred, not partially implemented):
- Authentication/authorization (no `@CurrentUserId`, no ownership checks, no
  `createdBy` field) — there is no auth system in this template at all.
- Structured JSON logging (`logstash-logback-encoder`) — console pattern
  logging with the correlation ID in MDC is enough for a scaffold.
- AOP method-timing (`LoggingAspect`), Micrometer business metrics, custom
  `HealthIndicator` beans — Actuator's built-in DB health check already
  covers the one datasource; there's no other domain to instrument.
- Domain events (`ApplicationEventPublisher`) — no second consumer exists in
  a single-entity scaffold.
- `PATCH` partial-update semantics — only `PUT` (full replacement) is
  implemented; partial-update needs a diff/nullable-field convention that's
  disproportionate for the example entity.

## Package structure

Feature-based, per the skill, replacing the current layer-based
`controller/`, `service/`, `repository/`, `entity/` top-level packages:

```
{{ base_package }}/
├── {{ app_class_name }}Application.java      (adds @EnableJpaAuditing)
├── common/
│   ├── entity/BaseEntity.java
│   ├── dto/ApiResponse.java
│   ├── dto/PageResponse.java
│   ├── dto/PaginationMeta.java
│   ├── exception/GlobalExceptionHandler.java
│   ├── exception/ResourceNotFoundException.java
│   ├── exception/ConflictException.java
│   ├── exception/ErrorDetails.java
│   ├── exception/ValidationErrorDetails.java
│   ├── config/JpaAuditingConfig.java
│   ├── config/OpenApiConfig.java
│   ├── config/CorrelationIdFilter.java
│   └── util/PaginationUtils.java
└── example/
    ├── entity/Example.java
    ├── entity/ExampleStatus.java
    ├── dto/CreateExampleRequest.java
    ├── dto/UpdateExampleRequest.java
    ├── dto/ExampleResponse.java
    ├── mapper/ExampleMapper.java
    ├── repository/ExampleRepository.java
    ├── service/ExampleService.java
    ├── service/ExampleServiceImpl.java
    └── controller/ExampleController.java
```

## Domain model

`common/entity/BaseEntity.java` — `@MappedSuperclass`, `@EntityListeners(AuditingEntityListener.class)`:
- `UUID id` (`@GeneratedValue(strategy = GenerationType.UUID)`)
- `Instant createdAt` (`@CreatedDate`), `Instant updatedAt` (`@LastModifiedDate`)
- `Long version` (`@Version`) — optimistic locking
- `Instant deletedAt` + `isDeleted()`/`softDelete()`/`restore()` helpers

`example/entity/Example.java` extends `BaseEntity`:
- `String name` — `@Column(nullable=false, length=120)`
- `ExampleStatus status` — `@Enumerated(EnumType.STRING)`, defaults to `ACTIVE`
- Lombok `@Getter @Setter @NoArgsConstructor` + a named `@Builder` constructor
  (per the skill's anti-pattern warning: never `@Builder` + `@AllArgsConstructor`
  together on a JPA entity)
- `equals()`/`hashCode()` based on `id` only

`example/entity/ExampleStatus.java` — enum `ACTIVE`, `ARCHIVED`.

`{{ app_class_name }}Application.java` gains `@EnableJpaAuditing` (or it lives
on a separate `common/config/JpaAuditingConfig.java` — using the latter to
keep the application class untouched by feature concerns).

## DTOs, validation, mapping

- `CreateExampleRequest` — Lombok `@Data @Builder @NoArgsConstructor @AllArgsConstructor`,
  `@NotBlank @Size(max=120) String name`. `status` omitted — server defaults to `ACTIVE`.
- `UpdateExampleRequest` — same shape, `name` and `status` both settable (full replacement).
- `ExampleResponse` — `id`, `name`, `status`, `createdAt`, `updatedAt`, `version`.
- `example/mapper/ExampleMapper.java` — MapStruct `@Mapper(componentModel = "spring")`:
  `Example toEntity(CreateExampleRequest)`, `ExampleResponse toResponse(Example)`,
  `void updateEntityFromRequest(UpdateExampleRequest, @MappingTarget Example)`.

## Common response envelope

`common/dto/ApiResponse.java` — generic `{boolean success, String message, T data}`
with static `success(message, data)` / `success(message)` / `error(message, details)`
factories, matching the skill's `GlobalExceptionHandler` templates.

`common/dto/PageResponse.java` — `{List<T> data, PaginationMeta pagination}`.
`common/dto/PaginationMeta.java` — `{int page, int limit, long total, int totalPages, boolean hasNext, boolean hasPrev}`.
`common/util/PaginationUtils.java` — `Pageable createPageable(int page, int size, String sortBy, String sortDirection)`
and `<T> PageResponse<T> toPageResponse(Page<?> page, List<T> content)`.

## Error handling

`common/exception/ResourceNotFoundException.java` (`@ResponseStatus(NOT_FOUND)`),
`ConflictException.java` (`@ResponseStatus(CONFLICT)`) — used for optimistic-lock
failures and duplicate-name conflicts.

`common/exception/GlobalExceptionHandler.java` (`@Slf4j @RestControllerAdvice`),
handlers for:
- `ResourceNotFoundException` → 404
- `ConflictException` → 409
- `MethodArgumentNotValidException` (bean validation) → 400, field errors folded
  into `ValidationErrorDetails`
- `ObjectOptimisticLockingFailureException` → 409
- `DataIntegrityViolationException` (e.g. unique constraint) → 409
- generic `Exception` → 500, logged with full stack trace + correlation id (via MDC)

All handlers return `ResponseEntity<ApiResponse<ErrorDetails|ValidationErrorDetails>>`.

## Repository

`example/repository/ExampleRepository.java` extends `JpaRepository<Example, UUID>`:
- `Optional<Example> findByIdAndDeletedAtIsNull(UUID id)`
- `Page<Example> findAllByDeletedAtIsNull(Pageable pageable)`
- `Page<Example> findByStatusAndDeletedAtIsNull(ExampleStatus status, Pageable pageable)`
- `boolean existsByNameAndDeletedAtIsNull(String name)`

## Service

`example/service/ExampleService.java` (interface) + `ExampleServiceImpl.java`
(`@Service @RequiredArgsConstructor @Slf4j @Transactional(readOnly = true)`):
- `ExampleResponse findById(UUID id)` — `findByIdAndDeletedAtIsNull` or throw `ResourceNotFoundException`
- `PageResponse<ExampleResponse> findAll(int page, int size, String sortBy, String sortDirection, ExampleStatus status)`
- `ExampleResponse create(CreateExampleRequest request)` (`@Transactional`) — checks
  `existsByNameAndDeletedAtIsNull` first, throws `ConflictException` on duplicate
- `ExampleResponse update(UUID id, UpdateExampleRequest request)` (`@Transactional`) —
  loads via `findByIdAndDeletedAtIsNull`, applies mapper, relies on `@Version` to
  surface `ObjectOptimisticLockingFailureException` on concurrent writes
- `void delete(UUID id)` (`@Transactional`) — loads, calls `entity.softDelete()`, saves

## Controller

`example/controller/ExampleController.java`:
- `@RestController @RequestMapping("/api/v1/examples") @RequiredArgsConstructor @Tag(name = "Examples") @Validated`
- `GET /api/v1/examples?page=&size=&sortBy=&sortDirection=&status=` →
  `ResponseEntity<ApiResponse<PageResponse<ExampleResponse>>>`
- `GET /api/v1/examples/{id}` → `ResponseEntity<ApiResponse<ExampleResponse>>`
- `POST /api/v1/examples` (`@Valid @RequestBody CreateExampleRequest`) → 201 with
  `Location` header set to the new resource's URI, body `ApiResponse<ExampleResponse>`
- `PUT /api/v1/examples/{id}` (`@Valid @RequestBody UpdateExampleRequest`) → 200
- `DELETE /api/v1/examples/{id}` → 204 (no body)
- Minimal `@Operation`/`@ApiResponses` annotations for Swagger UI; no `BindingResult`
  parameters anywhere — validation failures flow to `GlobalExceptionHandler` automatically.

## Observability & ops

`common/config/CorrelationIdFilter.java` — `@Component @Order(HIGHEST_PRECEDENCE)`,
implements `Filter`: reads/generates `X-Correlation-ID`, puts it in MDC under
`correlationId`, echoes it back as a response header, clears MDC in `finally`.

Logback pattern (`application.yml` `logging.pattern.console` or a minimal
`logback-spring.xml`) includes `%X{correlationId}` so every log line carries it —
plain pattern output, not the JSON/logstash encoder (see Out of scope).

`spring-boot-starter-actuator` added; `management.endpoints.web.exposure.include=health,info`
in the shared `application.yml`. No custom `HealthIndicator` — the built-in
datasource health check is sufficient.

`common/config/OpenApiConfig.java` — minimal `@Bean OpenAPI` with title/version
from `{{ project_name }}`; `springdoc-openapi-starter-webmvc-ui` dependency gives
Swagger UI at `/swagger-ui.html` for free.

## Config profiles

- `application.yml` — shared defaults: `spring.application.name`, Liquibase
  changelog path, `management.endpoints.web.exposure.include`, logging pattern.
- `application-dev.yml` — today's hardcoded local Postgres creds
  (`jdbc:postgresql://localhost:5432/...`, `forge`/`forge`), `ddl-auto: none`,
  SQL logging on, springdoc enabled.
- `application-prod.yml` — datasource from `${DB_URL}`, `${DB_USERNAME}`,
  `${DB_PASSWORD}` env vars, SQL logging off, springdoc disabled.
- `docker-compose.yml`/`README.md` updated to set `SPRING_PROFILES_ACTIVE=dev`
  as the documented default for local runs.

## Database migration

Liquibase Formatted SQL, per `migration-rules.md`, replacing the current
`001-create-example-table.sql`. New columns: `status`, `version`, `created_at`,
`updated_at`, `deleted_at`; `id` becomes `UUID PRIMARY KEY DEFAULT gen_random_uuid()`.
Indexes on `status` and `deleted_at` per the skill's `entity-rules.md` example.
Changeset uses a fixed, hardcoded epoch-millis id (this is a static template
with exactly one migration ever — no need to generate one dynamically at
render time, consistent with the prior `2026-08-13-forge-enhancements-design.md`
decision for the same file). Every changeset includes a `-- rollback` line.

## Testing

Three tests replacing the current zero coverage, matching `testing-rules.md`
exactly:

- `ExampleServiceImplTest` — `@ExtendWith(MockitoExtension.class)`, `@Mock`
  repository + mapper, `@InjectMocks` service. Covers: find-by-id happy path,
  find-by-id not-found → `ResourceNotFoundException`, create happy path,
  create duplicate name → `ConflictException`, update happy path, delete calls
  `softDelete()` + `save()`.
- `ExampleControllerTest` — `@WebMvcTest(ExampleController.class)`,
  `@AutoConfigureMockMvc(addFilters = false)`, `@MockBean` service. Covers:
  200 + `ApiResponse` envelope shape on get, 400 on blank `name`, 404 mapped
  correctly, 201 + `Location` header on create.
- `ExampleRepositoryTest` — `@DataJpaTest` +
  `@AutoConfigureTestDatabase(replace = Replace.NONE)` + `@Testcontainers` with
  a `PostgreSQLContainer<>("postgres:16-alpine")`, `@DynamicPropertySource`
  wiring the container's JDBC url/credentials. Covers: Liquibase migration
  applies cleanly, `findByIdAndDeletedAtIsNull` excludes soft-deleted rows,
  paging works.

**Caveat carried into the implementation plan:** Forge's own
`core/validator.py` only runs `mvn compile`, not `mvn test` — these tests
won't execute as part of Forge's generation/validation pipeline (no Docker
guarantee there). They exist for the *generated project's* own CI/dev loop.
The compile step still needs the test sources to compile cleanly, so
`mvn compile` isn't enough to guarantee correctness here — Forge's own
`tests/test_generation.py` should additionally assert the generated project's
test sources exist, without invoking `mvn test` (running Testcontainers-based
tests during Forge's own test suite would make `pytest` depend on Docker,
which is a new, heavier requirement than today's `mvn` dependency).

## Dependency changes (`pom.xml`)

Added: `org.projectlombok:lombok` (+ annotation processor path),
`org.mapstruct:mapstruct` + `mapstruct-processor` (annotation processor path,
ordered after Lombok per `lombok-mapstruct-binding` requirements),
`org.springdoc:springdoc-openapi-starter-webmvc-ui`,
`org.springframework.boot:spring-boot-starter-actuator`,
`org.springframework.boot:spring-boot-starter-validation`,
`org.testcontainers:junit-jupiter` + `org.testcontainers:postgresql` (test
scope, via the Testcontainers BOM).

## Forge wiring changes

- `cli.py`: `EXPECTED_STRUCTURAL_PATHS` rewritten for the new `common/` +
  `example/` package layout and new resource files (`application-dev.yml`,
  `application-prod.yml`).
- `config_schema.py`: audited for whether `template_context()` needs new
  variables. Expectation is no new *user-facing* CLI parameters — package
  subpaths (`common`, `example`) are static template structure, not derived
  per-project values — but this gets confirmed during implementation since
  `jinja2.StrictUndefined` will fail fast if anything's missing.
- `tests/test_generation.py`: extended to assert the new structural paths
  exist and that `mvn compile` (including test-source compilation) still
  succeeds; no `mvn test` invocation added (see Testing caveat above).

## Non-goals / explicitly not revisited

This design does not touch Forge's wizard, renderer, or preview logic — only
the template content and the two `cli.py`/`config_schema.py` integration
points listed above. Template-selection (multiple starter templates) remains
out of scope, as it has been since the original v1 design.
