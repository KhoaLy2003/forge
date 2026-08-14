# Production-Ready Template Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the `Example` vertical slice in `templates/base-layered` (and its supporting `common/` infrastructure) so a `forge new` project ships production-shaped Spring Boot code instead of a bare CRUD toy.

**Architecture:** Feature-based Java packages (`common/` for cross-cutting infra, `example/` for the domain slice) replacing the current layer-based (`controller/`, `service/`, `repository/`, `entity/`) structure. Lombok + MapStruct cut boilerplate; a generic `ApiResponse<T>`/`PageResponse<T>` envelope wraps every controller response; `BaseEntity` gives every entity UUID id, audit timestamps, optimistic locking, and soft delete for free.

**Tech Stack:** Java 21, Spring Boot 4.0.0, Spring Data JPA, Liquibase (Formatted SQL), Lombok, MapStruct 1.6.3, springdoc-openapi 2.8.5, Spring Boot Actuator, Testcontainers (JUnit 5 + PostgreSQL), JUnit 5, Mockito, MockMvc.

**Spec:** `docs/superpowers/specs/2026-08-14-production-ready-template-design.md`

## Global Constraints

- Java 21, `spring-boot-starter-parent` 4.0.0 (already pinned in `pom.xml` — do not change).
- Every new/changed Java file lives under `templates/base-layered/src/{main,test}/java/{{ package_path }}/...` and uses Jinja2 placeholders (`{{ base_package }}`, `{{ package_path }}`, `{{ app_class_name }}`) exactly where the existing template files already do — `jinja2.StrictUndefined` fails the whole render if a variable is referenced that isn't in `ForgeConfig.template_context()` (`core/config_schema.py:107-116`). This plan introduces **no new template variables** — confirm this holds as each task's file is written.
- Package layout: `common/` (entity, dto, exception, config, util) for cross-cutting infra shared by any future feature; `example/` (entity, dto, mapper, repository, service, controller) for the one demonstrated domain slice. Every new feature a project author adds later is expected to mirror `example/`'s six subpackages.
- API responses: every controller method wraps its body in `{{ base_package }}.common.dto.ApiResponse<T>`; paginated lists additionally wrap their data in `{{ base_package }}.common.dto.PageResponse<T>`.
- Entities extend `{{ base_package }}.common.entity.BaseEntity` (UUID id, `createdAt`/`updatedAt` via JPA auditing, `@Version`, soft delete via `deletedAt`).
- Controller base path: `/api/v1/examples` (URL path versioning).
- Lombok used throughout (`@Getter/@Setter/@Builder/@NoArgsConstructor/@AllArgsConstructor/@RequiredArgsConstructor/@Slf4j/@Data` as appropriate) — no hand-written getters/setters/constructors in new code.
- Testing matches `java-spring-boot` skill conventions: Mockito for service unit tests, `@WebMvcTest`+MockMvc for controller tests, `@DataJpaTest` + Testcontainers PostgreSQL (`postgres:16-alpine`, `@AutoConfigureTestDatabase(replace = Replace.NONE)`) for repository tests. **Repository tests require a running Docker daemon to execute** — flagged per-task below.
- Liquibase Formatted SQL only (no XML/YAML changesets) — matches existing `001-create-example-table.sql` style.
- Out of scope (do not implement): authentication/authorization, structured JSON/logstash logging, AOP method-timing, Micrometer business metrics, custom `HealthIndicator` beans, domain events, `PATCH` partial updates.

---

## File Structure

```
templates/base-layered/
├── pom.xml                                              [Modify — Task 1]
├── docker-compose.yml                                   [Modify — Task 10]
├── README.md                                             [Modify — Task 10]
└── src/
    ├── main/
    │   ├── java/{{ package_path }}/
    │   │   ├── {{ app_class_name }}Application.java      [unchanged]
    │   │   ├── common/
    │   │   │   ├── entity/BaseEntity.java                 [Create — Task 3]
    │   │   │   ├── dto/ApiResponse.java                   [Create — Task 2]
    │   │   │   ├── dto/PageResponse.java                  [Create — Task 2]
    │   │   │   ├── dto/PaginationMeta.java                [Create — Task 2]
    │   │   │   ├── util/PaginationUtils.java               [Create — Task 2]
    │   │   │   ├── exception/ResourceNotFoundException.java [Create — Task 4]
    │   │   │   ├── exception/ConflictException.java        [Create — Task 4]
    │   │   │   ├── exception/ErrorDetails.java              [Create — Task 4]
    │   │   │   ├── exception/ValidationErrorDetails.java    [Create — Task 4]
    │   │   │   ├── exception/GlobalExceptionHandler.java    [Create — Task 4]
    │   │   │   ├── config/JpaAuditingConfig.java             [Create — Task 3]
    │   │   │   ├── config/CorrelationIdFilter.java           [Create — Task 9]
    │   │   │   └── config/OpenApiConfig.java                 [Create — Task 9]
    │   │   ├── entity/Example.java                         [Delete — Task 5]
    │   │   ├── repository/ExampleRepository.java            [Delete — Task 5]
    │   │   ├── service/ExampleService.java                  [Delete — Task 7]
    │   │   ├── controller/ExampleController.java            [Delete — Task 8]
    │   │   ├── controller/GlobalExceptionHandler.java        [Delete — Task 8]
    │   │   └── example/
    │   │       ├── entity/ExampleStatus.java                [Create — Task 5]
    │   │       ├── entity/Example.java                      [Create — Task 5]
    │   │       ├── dto/CreateExampleRequest.java             [Create — Task 6]
    │   │       ├── dto/UpdateExampleRequest.java             [Create — Task 6]
    │   │       ├── dto/ExampleResponse.java                  [Create — Task 6]
    │   │       ├── mapper/ExampleMapper.java                 [Create — Task 6]
    │   │       ├── repository/ExampleRepository.java         [Create — Task 5]
    │   │       ├── service/ExampleService.java                [Create — Task 7]
    │   │       ├── service/ExampleServiceImpl.java             [Create — Task 7]
    │   │       └── controller/ExampleController.java          [Create — Task 8]
    │   └── resources/
    │       ├── application.yml                             [Modify — Task 10]
    │       ├── application-dev.yml                          [Create — Task 10]
    │       ├── application-prod.yml                         [Create — Task 10]
    │       └── db/changelog/001-create-example-table.sql    [Modify — Task 5]
    └── test/java/{{ package_path }}/
        ├── common/
        │   ├── util/PaginationUtilsTest.java                [Create — Task 2]
        │   ├── exception/GlobalExceptionHandlerTest.java     [Create — Task 4]
        │   └── config/CorrelationIdFilterTest.java           [Create — Task 9]
        └── example/
            ├── repository/ExampleRepositoryTest.java         [Create — Task 5]
            ├── mapper/ExampleMapperTest.java                  [Create — Task 6]
            ├── service/ExampleServiceImplTest.java             [Create — Task 7]
            └── controller/ExampleControllerTest.java           [Create — Task 8]

cli.py                                                    [Modify — Task 11]
core/validator.py                                          [Modify — Task 12]
tests/test_template_content.py                              [Modify — Task 11]
tests/test_generation.py                                    [Modify — Task 11]
tests/test_validator.py                                      [Modify — Task 12]
```

---

### Task 1: `pom.xml` — production dependencies and annotation processors

**Files:**
- Modify: `templates/base-layered/pom.xml`

**Interfaces:**
- Produces: `lombok`, `mapstruct` (+ `mapstruct-processor`), `spring-boot-starter-actuator`, `spring-boot-starter-validation`, `springdoc-openapi-starter-webmvc-ui`, `testcontainers`/`junit-jupiter`/`postgresql` (test scope) all resolvable on the classpath for every later task.

No test-first cycle here (pure build config) — verification is a manual render + `mvn compile`.

- [ ] **Step 1: Add the `mapstruct.version` property**

In the `<properties>` block (alongside the existing `<java.version>21</java.version>`), add:
```xml
<mapstruct.version>1.6.3</mapstruct.version>
```

- [ ] **Step 2: Add new dependencies**

Inside `<dependencies>`, after the existing `spring-boot-starter-data-jpa` entry, add (in this order):
```xml
<dependency>
  <groupId>org.springframework.boot</groupId>
  <artifactId>spring-boot-starter-validation</artifactId>
</dependency>
<dependency>
  <groupId>org.springframework.boot</groupId>
  <artifactId>spring-boot-starter-actuator</artifactId>
</dependency>
<dependency>
  <groupId>org.projectlombok</groupId>
  <artifactId>lombok</artifactId>
  <optional>true</optional>
</dependency>
<dependency>
  <groupId>org.mapstruct</groupId>
  <artifactId>mapstruct</artifactId>
  <version>${mapstruct.version}</version>
</dependency>
<dependency>
  <groupId>org.springdoc</groupId>
  <artifactId>springdoc-openapi-starter-webmvc-ui</artifactId>
  <version>2.8.5</version>
</dependency>
```

Add to the existing test-scoped block (near `spring-boot-starter-test`):
```xml
<dependency>
  <groupId>org.testcontainers</groupId>
  <artifactId>junit-jupiter</artifactId>
  <scope>test</scope>
</dependency>
<dependency>
  <groupId>org.testcontainers</groupId>
  <artifactId>postgresql</artifactId>
  <scope>test</scope>
</dependency>
```
(No explicit Testcontainers version — `spring-boot-starter-parent` manages `testcontainers.version` in its dependency management, same mechanism already pinning `spring-boot-starter-test`.)

- [ ] **Step 3: Configure the compiler plugin's annotation processors**

Inside `<build><plugins>`, add a `maven-compiler-plugin` entry (alongside the existing `spring-boot-maven-plugin`) so Lombok and MapStruct annotation processing compose correctly:
```xml
<plugin>
  <groupId>org.apache.maven.plugins</groupId>
  <artifactId>maven-compiler-plugin</artifactId>
  <configuration>
    <annotationProcessorPaths>
      <path>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
      </path>
      <path>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok-mapstruct-binding</artifactId>
        <version>0.2.0</version>
      </path>
      <path>
        <groupId>org.mapstruct</groupId>
        <artifactId>mapstruct-processor</artifactId>
        <version>${mapstruct.version}</version>
      </path>
    </annotationProcessorPaths>
  </configuration>
</plugin>
```

- [ ] **Step 4: Verify — render and compile**

From the repo root (`F:/Khoa-TonyRay/learning/projects/forge`), run:
```bash
.venv\Scripts\python -c "from core.config_schema import ForgeConfig; from core.renderer import render_tree; import tempfile,pathlib; d=pathlib.Path(tempfile.mkdtemp()); c=ForgeConfig(project_name='pom-check', target_path=d, group_id='com.example', artifact_id='pom-check'); render_tree(pathlib.Path('templates/base-layered'), c.target_dir, c.template_context()); print(c.target_dir)"
```
Then `cd` into the printed directory and run `mvn -q compile`. Expected: succeeds (the existing Java sources don't use Lombok/MapStruct yet, so this only proves the POM itself is well-formed and every new dependency resolves). Delete the temp directory afterward.

---

### Task 2: Common response envelope (`ApiResponse`, `PageResponse`, `PaginationMeta`, `PaginationUtils`)

**Files:**
- Create: `templates/base-layered/src/main/java/{{ package_path }}/common/dto/ApiResponse.java`
- Create: `templates/base-layered/src/main/java/{{ package_path }}/common/dto/PageResponse.java`
- Create: `templates/base-layered/src/main/java/{{ package_path }}/common/dto/PaginationMeta.java`
- Create: `templates/base-layered/src/main/java/{{ package_path }}/common/util/PaginationUtils.java`
- Test: `templates/base-layered/src/test/java/{{ package_path }}/common/util/PaginationUtilsTest.java`

**Interfaces:**
- Produces: `ApiResponse<T>` with static factories `success(String message, T data)`, `success(String message)` (returns `ApiResponse<Void>`), `error(String message, T details)`. `PageResponse<T>` with fields `List<T> data`, `PaginationMeta pagination`. `PaginationMeta` with fields `int page, int limit, long total, int totalPages, boolean hasNext, boolean hasPrev`. `PaginationUtils.createPageable(int page, int size, String sortBy, String sortDirection) -> Pageable` and `PaginationUtils.<T> toPageResponse(Page<?> page, List<T> content) -> PageResponse<T>`.

- [ ] **Step 1: Write `PaginationUtilsTest`**

Package `{{ base_package }}.common.util`. Plain JUnit 5, no Spring context. Two test methods:
- `createPageable_sortsAscendingWhenDirectionIsAsc`: call `createPageable(0, 20, "name", "ASC")`, assert the returned `Pageable`'s `getSort()` has a `Sort.Order` for `"name"` with `Sort.Direction.ASC`.
- `createPageable_defaultsToDescendingForUnrecognizedDirection`: call with `"bogus"`, assert direction resolves to `Sort.Direction.DESC`.
- `toPageResponse_mapsPageMetadataCorrectly`: build a Spring Data `PageImpl<>(List.of("a","b"), PageRequest.of(0, 2), 5)` fixture, call `toPageResponse(fixture, List.of("x","y"))`, assert `result.getData()` equals `List.of("x","y")` and `result.getPagination()` has `page=0, limit=2, total=5, totalPages=3, hasNext=true, hasPrev=false`.

- [ ] **Step 2: Run the test to verify it fails**

Compilation will fail (classes don't exist yet) — that's the expected "red" state for this task; there's no separate "run and see assertion failure" step since the target classes are entirely new.

- [ ] **Step 3: Implement `PaginationMeta`, `PageResponse`, `ApiResponse`**

`PaginationMeta` (package `{{ base_package }}.common.dto`): `@Data @Builder @NoArgsConstructor @AllArgsConstructor`, fields as listed in Interfaces above.

`PageResponse<T>` (same package): `@Data @Builder @NoArgsConstructor @AllArgsConstructor`, fields `List<T> data`, `PaginationMeta pagination`.

`ApiResponse<T>` (same package): `@Data @Builder @NoArgsConstructor @AllArgsConstructor`, fields `boolean success`, `String message`, `T data`. Static factories:
```java
public static <T> ApiResponse<T> success(String message, T data) {
    return ApiResponse.<T>builder().success(true).message(message).data(data).build();
}
public static ApiResponse<Void> success(String message) {
    return ApiResponse.<Void>builder().success(true).message(message).build();
}
public static <T> ApiResponse<T> error(String message, T details) {
    return ApiResponse.<T>builder().success(false).message(message).data(details).build();
}
```

- [ ] **Step 4: Implement `PaginationUtils`**

Package `{{ base_package }}.common.util`. Final class, private constructor (utility class — no instantiation).
```java
public static Pageable createPageable(int page, int size, String sortBy, String sortDirection) {
    Sort.Direction direction = "ASC".equalsIgnoreCase(sortDirection) ? Sort.Direction.ASC : Sort.Direction.DESC;
    return PageRequest.of(page, size, Sort.by(direction, sortBy));
}

public static <T> PageResponse<T> toPageResponse(Page<?> page, List<T> content) {
    PaginationMeta meta = PaginationMeta.builder()
        .page(page.getNumber())
        .limit(page.getSize())
        .total(page.getTotalElements())
        .totalPages(page.getTotalPages())
        .hasNext(page.hasNext())
        .hasPrev(page.hasPrevious())
        .build();
    return PageResponse.<T>builder().data(content).pagination(meta).build();
}
```

- [ ] **Step 5: Run the test to verify it passes**

From a rendered temp project (same render snippet as Task 1 Step 4), copy this task's four new files + test file into place manually is not needed — instead render the whole template fresh (it now includes these files) and run:
```bash
mvn -q -Dtest=PaginationUtilsTest test
```
Expected: `BUILD SUCCESS`, 3 tests run, 0 failures.

---

### Task 3: `BaseEntity` and JPA auditing config

**Files:**
- Create: `templates/base-layered/src/main/java/{{ package_path }}/common/entity/BaseEntity.java`
- Create: `templates/base-layered/src/main/java/{{ package_path }}/common/config/JpaAuditingConfig.java`

**Interfaces:**
- Produces: `BaseEntity` (`@MappedSuperclass`) with `UUID id`, `Instant createdAt`, `Instant updatedAt`, `Long version`, `Instant deletedAt`, plus `isDeleted()`, `softDelete()`, `restore()`. `JpaAuditingConfig` activates `@EnableJpaAuditing` so `@CreatedDate`/`@LastModifiedDate` populate.

No standalone test — `BaseEntity` is abstract and exercised indirectly by `ExampleRepositoryTest` in Task 5. Verification here is a compile check only.

- [ ] **Step 1: Implement `BaseEntity`**

Package `{{ base_package }}.common.entity`:
```java
@Getter
@Setter
@MappedSuperclass
@EntityListeners(AuditingEntityListener.class)
public abstract class BaseEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @Column(name = "id", updatable = false, nullable = false)
    private UUID id;

    @CreatedDate
    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    @LastModifiedDate
    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    @Version
    @Column(name = "version", nullable = false)
    private Long version;

    @Column(name = "deleted_at")
    private Instant deletedAt;

    public boolean isDeleted() {
        return deletedAt != null;
    }

    public void softDelete() {
        this.deletedAt = Instant.now();
    }

    public void restore() {
        this.deletedAt = null;
    }
}
```

- [ ] **Step 2: Implement `JpaAuditingConfig`**

Package `{{ base_package }}.common.config`:
```java
@Configuration
@EnableJpaAuditing
public class JpaAuditingConfig {
}
```

- [ ] **Step 3: Verify — compile**

Render a fresh temp project (Task 1 Step 4 snippet) and run `mvn -q compile`. Expected: succeeds. `BaseEntity` has no subclass yet, so this only proves it compiles standalone.

---

### Task 4: Common exceptions and `GlobalExceptionHandler`

**Files:**
- Create: `templates/base-layered/src/main/java/{{ package_path }}/common/exception/ResourceNotFoundException.java`
- Create: `templates/base-layered/src/main/java/{{ package_path }}/common/exception/ConflictException.java`
- Create: `templates/base-layered/src/main/java/{{ package_path }}/common/exception/ErrorDetails.java`
- Create: `templates/base-layered/src/main/java/{{ package_path }}/common/exception/ValidationErrorDetails.java`
- Create: `templates/base-layered/src/main/java/{{ package_path }}/common/exception/GlobalExceptionHandler.java`
- Delete: `templates/base-layered/src/main/java/{{ package_path }}/controller/GlobalExceptionHandler.java` (superseded — old version only handled `NoSuchElementException` with no body)
- Test: `templates/base-layered/src/test/java/{{ package_path }}/common/exception/GlobalExceptionHandlerTest.java`

**Interfaces:**
- Consumes: `ApiResponse<T>` from Task 2 (`{{ base_package }}.common.dto.ApiResponse`).
- Produces: `ResourceNotFoundException(String message)` (404), `ConflictException(String message)` (409) — both used by `ExampleServiceImpl` in Task 7. `GlobalExceptionHandler` — a `@RestControllerAdvice` picked up automatically by component scanning in any controller test that imports it.

- [ ] **Step 1: Write `GlobalExceptionHandlerTest`**

Package `{{ base_package }}.common.exception`. A `@WebMvcTest` slice against a small nested probe controller (defined in the test file itself) so the handler's behavior is exercised through real HTTP semantics rather than by hand-constructing exception types:

```java
@WebMvcTest(controllers = GlobalExceptionHandlerTest.ProbeController.class)
@Import(GlobalExceptionHandler.class)
class GlobalExceptionHandlerTest {

    @Autowired MockMvc mockMvc;

    @RestController
    static class ProbeController {
        @PostMapping("/probe/validate")
        String validate(@Valid @RequestBody ProbeRequest request) { return "ok"; }

        @GetMapping("/probe/not-found")
        String notFound() { throw new ResourceNotFoundException("probe not found"); }

        @GetMapping("/probe/conflict")
        String conflict() { throw new ConflictException("probe conflict"); }

        @GetMapping("/probe/boom")
        String boom() { throw new RuntimeException("boom"); }
    }

    record ProbeRequest(@NotBlank String name) {}

    // four @Test methods below
}
```

Four `@Test` methods, each POSTs/GETs the matching probe endpoint via `mockMvc.perform(...)`:
- `validate_withBlankName_returns400`: POST `/probe/validate` with `{"name": ""}` → `status().isBadRequest()`, `jsonPath("$.success").value(false)`, `jsonPath("$.data.fieldErrors.name").exists()`.
- `notFound_returns404`: GET `/probe/not-found` → `status().isNotFound()`, `jsonPath("$.success").value(false)`, `jsonPath("$.message").value("probe not found")`.
- `conflict_returns409`: GET `/probe/conflict` → `status().isConflict()`.
- `genericException_returns500`: GET `/probe/boom` → `status().isInternalServerError()`, `jsonPath("$.message").value("An unexpected error occurred")`.

- [ ] **Step 2: Run the test to verify it fails**

Compilation fails (target classes don't exist). Expected red state.

- [ ] **Step 3: Implement the exception types and DTOs**

`ResourceNotFoundException` (package `{{ base_package }}.common.exception`): `@ResponseStatus(HttpStatus.NOT_FOUND) public class ResourceNotFoundException extends RuntimeException { public ResourceNotFoundException(String message) { super(message); } }`

`ConflictException`: same shape, `@ResponseStatus(HttpStatus.CONFLICT)`.

`ErrorDetails`: `@Data @Builder @NoArgsConstructor @AllArgsConstructor` with `String code`, `String message`, `Instant timestamp`.

`ValidationErrorDetails`: `@Data @Builder @NoArgsConstructor @AllArgsConstructor` with `String code`, `String message`, `Map<String, List<String>> fieldErrors`, `Instant timestamp`.

- [ ] **Step 4: Implement `GlobalExceptionHandler`**

Package `{{ base_package }}.common.exception`, `@Slf4j @RestControllerAdvice`:
```java
@ExceptionHandler(ResourceNotFoundException.class)
public ResponseEntity<ApiResponse<ErrorDetails>> handleNotFound(ResourceNotFoundException ex) {
    log.warn("Resource not found: {}", ex.getMessage());
    ErrorDetails details = ErrorDetails.builder().code("RESOURCE_NOT_FOUND").message(ex.getMessage()).timestamp(Instant.now()).build();
    return ResponseEntity.status(HttpStatus.NOT_FOUND).body(ApiResponse.error(ex.getMessage(), details));
}

@ExceptionHandler(ConflictException.class)
public ResponseEntity<ApiResponse<ErrorDetails>> handleConflict(ConflictException ex) {
    log.warn("Conflict: {}", ex.getMessage());
    ErrorDetails details = ErrorDetails.builder().code("CONFLICT").message(ex.getMessage()).timestamp(Instant.now()).build();
    return ResponseEntity.status(HttpStatus.CONFLICT).body(ApiResponse.error(ex.getMessage(), details));
}

@ExceptionHandler(MethodArgumentNotValidException.class)
public ResponseEntity<ApiResponse<ValidationErrorDetails>> handleValidation(MethodArgumentNotValidException ex) {
    Map<String, List<String>> fieldErrors = new HashMap<>();
    ex.getBindingResult().getFieldErrors().forEach(error ->
        fieldErrors.computeIfAbsent(error.getField(), k -> new ArrayList<>()).add(error.getDefaultMessage()));
    ValidationErrorDetails details = ValidationErrorDetails.builder()
        .code("VALIDATION_FAILED").message("Request validation failed").fieldErrors(fieldErrors).timestamp(Instant.now()).build();
    return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(ApiResponse.error("Validation failed", details));
}

@ExceptionHandler(ObjectOptimisticLockingFailureException.class)
public ResponseEntity<ApiResponse<ErrorDetails>> handleOptimisticLock(ObjectOptimisticLockingFailureException ex) {
    log.warn("Optimistic locking failure: {}", ex.getMessage());
    ErrorDetails details = ErrorDetails.builder().code("OPTIMISTIC_LOCK_CONFLICT").message("The resource was modified by another request").timestamp(Instant.now()).build();
    return ResponseEntity.status(HttpStatus.CONFLICT).body(ApiResponse.error("Conflict detected", details));
}

@ExceptionHandler(DataIntegrityViolationException.class)
public ResponseEntity<ApiResponse<ErrorDetails>> handleDataIntegrityViolation(DataIntegrityViolationException ex) {
    log.error("Data integrity violation: {}", ex.getMessage());
    ErrorDetails details = ErrorDetails.builder().code("DATA_INTEGRITY_VIOLATION").message("Data integrity constraint violated").timestamp(Instant.now()).build();
    return ResponseEntity.status(HttpStatus.CONFLICT).body(ApiResponse.error("Data integrity constraint violated", details));
}

@ExceptionHandler(Exception.class)
public ResponseEntity<ApiResponse<ErrorDetails>> handleGeneric(Exception ex) {
    log.error("Unexpected error occurred", ex);
    ErrorDetails details = ErrorDetails.builder().code("INTERNAL_SERVER_ERROR").message("An unexpected error occurred").timestamp(Instant.now()).build();
    return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(ApiResponse.error("An unexpected error occurred", details));
}
```
(`ObjectOptimisticLockingFailureException` is `org.springframework.orm.ObjectOptimisticLockingFailureException`; `DataIntegrityViolationException` is `org.springframework.dao.DataIntegrityViolationException`.)

- [ ] **Step 5: Delete the superseded handler**

Delete `templates/base-layered/src/main/java/{{ package_path }}/controller/GlobalExceptionHandler.java`.

- [ ] **Step 6: Run the test to verify it passes**

Render a fresh temp project and run:
```bash
mvn -q -Dtest=GlobalExceptionHandlerTest test
```
Expected: `BUILD SUCCESS`, 4 tests run, 0 failures.

---

### Task 5: `Example` entity, migration, and repository

**Files:**
- Create: `templates/base-layered/src/main/java/{{ package_path }}/example/entity/ExampleStatus.java`
- Create: `templates/base-layered/src/main/java/{{ package_path }}/example/entity/Example.java`
- Create: `templates/base-layered/src/main/java/{{ package_path }}/example/repository/ExampleRepository.java`
- Modify: `templates/base-layered/src/main/resources/db/changelog/001-create-example-table.sql`
- Delete: `templates/base-layered/src/main/java/{{ package_path }}/entity/Example.java`
- Delete: `templates/base-layered/src/main/java/{{ package_path }}/repository/ExampleRepository.java`
- Test: `templates/base-layered/src/test/java/{{ package_path }}/example/repository/ExampleRepositoryTest.java`

**Interfaces:**
- Consumes: `BaseEntity` from Task 3 (`{{ base_package }}.common.entity.BaseEntity`), `JpaAuditingConfig`.
- Produces: `Example` (extends `BaseEntity`, fields `name`, `status`), `ExampleStatus` enum (`ACTIVE`, `ARCHIVED`), `ExampleRepository` with `findByIdAndDeletedAtIsNull(UUID)`, `findAllByDeletedAtIsNull(Pageable)`, `findByStatusAndDeletedAtIsNull(ExampleStatus, Pageable)`, `existsByNameAndDeletedAtIsNull(String)` — all consumed by `ExampleServiceImpl` in Task 7.

**Caveat:** the test in this task uses Testcontainers and requires a running Docker daemon. If Docker isn't available in the execution environment, implement the code and skip running Step 6 — the compile-only check in Task 12's final verification still catches syntax/type errors.

- [ ] **Step 1: Rewrite the migration**

Replace the full contents of `templates/base-layered/src/main/resources/db/changelog/001-create-example-table.sql`:
```sql
-- liquibase formatted sql

-- changeset forge:1700000000000
-- comment: Create the example table
DROP TABLE IF EXISTS example;

CREATE TABLE example
(
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name       VARCHAR(120)             NOT NULL,
    status     VARCHAR(20)              NOT NULL DEFAULT 'ACTIVE',
    version    BIGINT                   NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_example_status ON example (status);
CREATE INDEX idx_example_deleted_at ON example (deleted_at);

-- rollback DROP TABLE example;
```
(`gen_random_uuid()` is a PostgreSQL 13+ core builtin — no extension needed; `postgres:16` in `docker-compose.yml` already satisfies this. The changeset id is kept identical to the original since this is template source with no real deployment history to preserve.)

- [ ] **Step 2: Write `ExampleRepositoryTest`**

Package `{{ base_package }}.example.repository`:
```java
@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@Testcontainers
@Import(JpaAuditingConfig.class)
class ExampleRepositoryTest {

    @Container
    static final PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16-alpine")
        .withDatabaseName("testdb").withUsername("test").withPassword("test");

    @DynamicPropertySource
    static void configureProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.datasource.username", postgres::getUsername);
        registry.add("spring.datasource.password", postgres::getPassword);
    }

    @Autowired ExampleRepository repository;

    // three @Test methods below
}
```

Three `@Test` methods:
- `findByIdAndDeletedAtIsNull_excludesSoftDeletedRows`: save an active `Example` and a second one immediately soft-deleted (`entity.softDelete()` before `repository.save(...)`), assert `findByIdAndDeletedAtIsNull` returns present for the active one's id and empty for the deleted one's id.
- `findAllByDeletedAtIsNull_returnsOnlyActiveRowsPaged`: save 3 active examples + 1 soft-deleted, call `findAllByDeletedAtIsNull(PageRequest.of(0, 10))`, assert `getContent()` has size 3 and none of them is the soft-deleted one.
- `save_populatesAuditAndVersionFields`: save a new `Example.builder().name("audit-check").build()`, assert the persisted entity has non-null `getId()`, `getCreatedAt()`, `getUpdatedAt()`, and `getVersion()` equal to `0L`, and `getStatus()` equal to `ExampleStatus.ACTIVE`.

- [ ] **Step 3: Run the test to verify it fails**

Compilation fails (target classes don't exist). Expected red state.

- [ ] **Step 4: Implement `ExampleStatus` and `Example`**

`ExampleStatus` (package `{{ base_package }}.example.entity`): `public enum ExampleStatus { ACTIVE, ARCHIVED }`

`Example` (same package), extends `{{ base_package }}.common.entity.BaseEntity`:
```java
@Entity
@Table(
    name = "example",
    indexes = {
        @Index(name = "idx_example_status", columnList = "status"),
        @Index(name = "idx_example_deleted_at", columnList = "deleted_at")
    }
)
@Getter
@Setter
@NoArgsConstructor
public class Example extends BaseEntity {

    @Column(name = "name", nullable = false, length = 120)
    private String name;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false, length = 20)
    private ExampleStatus status = ExampleStatus.ACTIVE;

    @Builder
    public Example(String name, ExampleStatus status) {
        this.name = name;
        this.status = status != null ? status : ExampleStatus.ACTIVE;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof Example other)) return false;
        return getId() != null && getId().equals(other.getId());
    }

    @Override
    public int hashCode() {
        return getClass().hashCode();
    }
}
```
(No `@EqualsAndHashCode` Lombok annotation — per the skill's anti-pattern warning, it would trigger lazy-load of inherited fields.)

- [ ] **Step 5: Implement `ExampleRepository`**

Package `{{ base_package }}.example.repository`:
```java
public interface ExampleRepository extends JpaRepository<Example, UUID> {
    Optional<Example> findByIdAndDeletedAtIsNull(UUID id);
    Page<Example> findAllByDeletedAtIsNull(Pageable pageable);
    Page<Example> findByStatusAndDeletedAtIsNull(ExampleStatus status, Pageable pageable);
    boolean existsByNameAndDeletedAtIsNull(String name);
}
```

- [ ] **Step 6: Delete the superseded entity and repository**

Delete `templates/base-layered/src/main/java/{{ package_path }}/entity/Example.java` and `templates/base-layered/src/main/java/{{ package_path }}/repository/ExampleRepository.java`.

- [ ] **Step 7: Run the test to verify it passes (requires Docker)**

Render a fresh temp project and run:
```bash
mvn -q -Dtest=ExampleRepositoryTest test
```
Expected: `BUILD SUCCESS`, 3 tests run, 0 failures. If Docker isn't running, this step fails with a Testcontainers connection error unrelated to the code — note this in the task's completion report rather than treating it as a code defect.

---

### Task 6: `Example` DTOs and MapStruct mapper

**Files:**
- Create: `templates/base-layered/src/main/java/{{ package_path }}/example/dto/CreateExampleRequest.java`
- Create: `templates/base-layered/src/main/java/{{ package_path }}/example/dto/UpdateExampleRequest.java`
- Create: `templates/base-layered/src/main/java/{{ package_path }}/example/dto/ExampleResponse.java`
- Create: `templates/base-layered/src/main/java/{{ package_path }}/example/mapper/ExampleMapper.java`
- Test: `templates/base-layered/src/test/java/{{ package_path }}/example/mapper/ExampleMapperTest.java`

**Interfaces:**
- Consumes: `Example`, `ExampleStatus` from Task 5.
- Produces: `CreateExampleRequest{name}`, `UpdateExampleRequest{name, status}`, `ExampleResponse{id, name, status, createdAt, updatedAt, version}`, `ExampleMapper` with `toEntity(CreateExampleRequest) -> Example`, `toResponse(Example) -> ExampleResponse`, `updateEntityFromRequest(UpdateExampleRequest, Example)` — all consumed by `ExampleServiceImpl` in Task 7.

- [ ] **Step 1: Write `ExampleMapperTest`**

Package `{{ base_package }}.example.mapper`. Instantiate the MapStruct-generated implementation directly — `new ExampleMapperImpl()` — since the mapper has no field dependencies, this works even though `componentModel = "spring"` is set (Spring wiring is only needed when *injecting* the mapper elsewhere, not for direct instantiation in a test).

Three `@Test` methods:
- `toEntity_mapsNameAndDefaultsStatusToActive`: `mapper.toEntity(CreateExampleRequest.builder().name("Widget").build())` → assert `getName()` equals `"Widget"` and `getStatus()` equals `ExampleStatus.ACTIVE` (the entity field's inline default, untouched by MapStruct since `CreateExampleRequest` has no `status` property).
- `toResponse_mapsAllFields`: build an `Example` via `Example.builder().name("Widget").status(ExampleStatus.ARCHIVED).build()`, set `setId(...)`/`setCreatedAt(...)`/`setUpdatedAt(...)`/`setVersion(...)` on it directly (they're inherited setters from `BaseEntity`), call `toResponse`, assert every field round-trips.
- `updateEntityFromRequest_appliesNameAndStatusInPlace`: build an `Example`, call `mapper.updateEntityFromRequest(UpdateExampleRequest.builder().name("Renamed").status(ExampleStatus.ARCHIVED).build(), entity)`, assert `entity.getName()` and `entity.getStatus()` reflect the update.

- [ ] **Step 2: Run the test to verify it fails**

Compilation fails. Expected red state.

- [ ] **Step 3: Implement the DTOs**

`CreateExampleRequest` (package `{{ base_package }}.example.dto`): `@Data @Builder @NoArgsConstructor @AllArgsConstructor`, one field: `@NotBlank(message = "Name is required") @Size(max = 120, message = "Name must be at most 120 characters") private String name;`

`UpdateExampleRequest` (same package): same Lombok annotations, two fields: the same `name` validation as above, plus `@NotNull(message = "Status is required") private ExampleStatus status;`

`ExampleResponse` (same package): `@Data @Builder @NoArgsConstructor @AllArgsConstructor`, fields `UUID id`, `String name`, `ExampleStatus status`, `Instant createdAt`, `Instant updatedAt`, `Long version`.

- [ ] **Step 4: Implement `ExampleMapper`**

Package `{{ base_package }}.example.mapper`:
```java
@Mapper(componentModel = "spring", unmappedTargetPolicy = ReportingPolicy.IGNORE)
public interface ExampleMapper {
    Example toEntity(CreateExampleRequest request);
    ExampleResponse toResponse(Example entity);
    void updateEntityFromRequest(UpdateExampleRequest request, @MappingTarget Example entity);
}
```
(`ReportingPolicy.IGNORE` silences MapStruct's unmapped-target warnings for `id`/`createdAt`/`updatedAt`/`version`/`deletedAt`, which are intentionally not settable from either request DTO.)

- [ ] **Step 5: Run the test to verify it passes**

Render a fresh temp project and run:
```bash
mvn -q -Dtest=ExampleMapperTest test
```
Expected: `BUILD SUCCESS`, 3 tests run, 0 failures. (This exercises MapStruct's annotation processing — a failure here most likely means the `maven-compiler-plugin` annotation processor ordering from Task 1 Step 3 is wrong.)

---

### Task 7: `ExampleService` interface + implementation

**Files:**
- Create: `templates/base-layered/src/main/java/{{ package_path }}/example/service/ExampleService.java`
- Create: `templates/base-layered/src/main/java/{{ package_path }}/example/service/ExampleServiceImpl.java`
- Delete: `templates/base-layered/src/main/java/{{ package_path }}/service/ExampleService.java`
- Test: `templates/base-layered/src/test/java/{{ package_path }}/example/service/ExampleServiceImplTest.java`

**Interfaces:**
- Consumes: `ExampleRepository` (Task 5), `ExampleMapper` (Task 6), `ResourceNotFoundException`/`ConflictException` (Task 4), `PaginationUtils`/`PageResponse` (Task 2).
- Produces: `ExampleService` interface with `findById(UUID) -> ExampleResponse`, `findAll(int, int, String, String, ExampleStatus) -> PageResponse<ExampleResponse>`, `create(CreateExampleRequest) -> ExampleResponse`, `update(UUID, UpdateExampleRequest) -> ExampleResponse`, `delete(UUID) -> void` — consumed by `ExampleController` in Task 8.

- [ ] **Step 1: Write `ExampleServiceImplTest`**

Package `{{ base_package }}.example.service`. `@ExtendWith(MockitoExtension.class)`, `@Mock ExampleRepository repository`, `@Mock ExampleMapper mapper`, `@InjectMocks ExampleServiceImpl service`.

Six `@Test` methods:
- `findById_whenFound_returnsResponse`: stub `repository.findByIdAndDeletedAtIsNull(id)` to return `Optional.of(entity)`, stub `mapper.toResponse(entity)` to return a fixture response, assert `service.findById(id)` equals the fixture.
- `findById_whenNotFound_throwsResourceNotFoundException`: stub repository to return `Optional.empty()`, assert `assertThrows(ResourceNotFoundException.class, () -> service.findById(id))`.
- `create_whenNameIsUnique_savesAndReturnsResponse`: stub `repository.existsByNameAndDeletedAtIsNull(...)` to return `false`, stub `mapper.toEntity(...)`/`repository.save(...)`/`mapper.toResponse(...)`, assert the returned response and that `repository.save` was invoked once.
- `create_whenNameAlreadyExists_throwsConflictException`: stub `existsByNameAndDeletedAtIsNull` to return `true`, assert `assertThrows(ConflictException.class, ...)`, and `verify(repository, never()).save(any())`.
- `update_whenFound_appliesMapperAndSaves`: stub `findByIdAndDeletedAtIsNull` to return `Optional.of(entity)`, call `service.update(id, request)`, verify `mapper.updateEntityFromRequest(request, entity)` was called and `repository.save(entity)` was called.
- `delete_whenFound_softDeletesAndSaves`: stub `findByIdAndDeletedAtIsNull` to return `Optional.of(entity)` (a real `Example` instance, not a further mock, so `softDelete()` has an observable effect), call `service.delete(id)`, assert `entity.isDeleted()` is `true` and `verify(repository).save(entity)`.

- [ ] **Step 2: Run the test to verify it fails**

Compilation fails. Expected red state.

- [ ] **Step 3: Implement `ExampleService`**

Package `{{ base_package }}.example.service`:
```java
public interface ExampleService {
    ExampleResponse findById(UUID id);
    PageResponse<ExampleResponse> findAll(int page, int size, String sortBy, String sortDirection, ExampleStatus status);
    ExampleResponse create(CreateExampleRequest request);
    ExampleResponse update(UUID id, UpdateExampleRequest request);
    void delete(UUID id);
}
```

- [ ] **Step 4: Implement `ExampleServiceImpl`**

Same package, `@Service @RequiredArgsConstructor @Slf4j @Transactional(readOnly = true)`:
```java
private final ExampleRepository repository;
private final ExampleMapper mapper;

@Transactional(readOnly = true)
public ExampleResponse findById(UUID id) {
    Example entity = repository.findByIdAndDeletedAtIsNull(id)
        .orElseThrow(() -> new ResourceNotFoundException("Example not found with id: " + id));
    return mapper.toResponse(entity);
}

@Transactional(readOnly = true)
public PageResponse<ExampleResponse> findAll(int page, int size, String sortBy, String sortDirection, ExampleStatus status) {
    Pageable pageable = PaginationUtils.createPageable(page, size, sortBy, sortDirection);
    Page<Example> result = status != null
        ? repository.findByStatusAndDeletedAtIsNull(status, pageable)
        : repository.findAllByDeletedAtIsNull(pageable);
    List<ExampleResponse> content = result.getContent().stream().map(mapper::toResponse).toList();
    return PaginationUtils.toPageResponse(result, content);
}

@Transactional
public ExampleResponse create(CreateExampleRequest request) {
    if (repository.existsByNameAndDeletedAtIsNull(request.getName())) {
        throw new ConflictException("Example with name '" + request.getName() + "' already exists");
    }
    Example saved = repository.save(mapper.toEntity(request));
    log.info("Example created with id: {}", saved.getId());
    return mapper.toResponse(saved);
}

@Transactional
public ExampleResponse update(UUID id, UpdateExampleRequest request) {
    Example entity = repository.findByIdAndDeletedAtIsNull(id)
        .orElseThrow(() -> new ResourceNotFoundException("Example not found with id: " + id));
    mapper.updateEntityFromRequest(request, entity);
    Example saved = repository.save(entity);
    log.info("Example updated: {}", id);
    return mapper.toResponse(saved);
}

@Transactional
public void delete(UUID id) {
    Example entity = repository.findByIdAndDeletedAtIsNull(id)
        .orElseThrow(() -> new ResourceNotFoundException("Example not found with id: " + id));
    entity.softDelete();
    repository.save(entity);
    log.info("Example deleted: {}", id);
}
```

- [ ] **Step 5: Delete the superseded service**

Delete `templates/base-layered/src/main/java/{{ package_path }}/service/ExampleService.java`.

- [ ] **Step 6: Run the test to verify it passes**

Render a fresh temp project and run:
```bash
mvn -q -Dtest=ExampleServiceImplTest test
```
Expected: `BUILD SUCCESS`, 6 tests run, 0 failures.

---

### Task 8: `ExampleController`

**Files:**
- Create: `templates/base-layered/src/main/java/{{ package_path }}/example/controller/ExampleController.java`
- Delete: `templates/base-layered/src/main/java/{{ package_path }}/controller/ExampleController.java`
- Test: `templates/base-layered/src/test/java/{{ package_path }}/example/controller/ExampleControllerTest.java`

**Interfaces:**
- Consumes: `ExampleService` (Task 7), `ApiResponse`/`PageResponse` (Task 2), `GlobalExceptionHandler` (Task 4).
- Produces: REST endpoints under `/api/v1/examples` (GET list, GET by id, POST, PUT, DELETE) — this is the outermost layer; nothing later in this plan depends on it.

- [ ] **Step 1: Write `ExampleControllerTest`**

Package `{{ base_package }}.example.controller`. `@WebMvcTest(ExampleController.class)`, `@Import(GlobalExceptionHandler.class)`, `@AutoConfigureMockMvc(addFilters = false)`, `@MockBean ExampleService service`, `@Autowired MockMvc mockMvc`, `@Autowired ObjectMapper objectMapper`.

Four `@Test` methods:
- `findById_whenFound_returns200WithEnvelope`: stub `service.findById(id)` to return a fixture `ExampleResponse`, GET `/api/v1/examples/{id}`, assert `status().isOk()`, `jsonPath("$.success").value(true)`, `jsonPath("$.data.id").value(id.toString())`.
- `create_withBlankName_returns400`: POST `/api/v1/examples` with `CreateExampleRequest.builder().name("").build()` as JSON body, assert `status().isBadRequest()`, and `verifyNoInteractions(service)`.
- `findById_whenServiceThrowsNotFound_returns404`: stub `service.findById(id)` to throw `new ResourceNotFoundException("not found")`, GET the endpoint, assert `status().isNotFound()` — this proves `GlobalExceptionHandler` is correctly wired to this controller via `@Import`.
- `create_whenValid_returns201WithLocationHeader`: stub `service.create(any())` to return a fixture response with a known `id`, POST a valid body, assert `status().isCreated()`, `header().string("Location", containsString(id.toString()))`, `jsonPath("$.data.id").value(id.toString())`.

- [ ] **Step 2: Run the test to verify it fails**

Compilation fails. Expected red state.

- [ ] **Step 3: Implement `ExampleController`**

Package `{{ base_package }}.example.controller`:
```java
@RestController
@RequestMapping("/api/v1/examples")
@RequiredArgsConstructor
@Tag(name = "Examples", description = "Example resource CRUD endpoints")
@Validated
public class ExampleController {

    private final ExampleService service;

    @GetMapping
    @Operation(summary = "List examples")
    public ResponseEntity<ApiResponse<PageResponse<ExampleResponse>>> findAll(
            @RequestParam(defaultValue = "0") @Min(0) int page,
            @RequestParam(defaultValue = "20") @Min(1) @Max(100) int size,
            @RequestParam(defaultValue = "createdAt") String sortBy,
            @RequestParam(defaultValue = "DESC") String sortDirection,
            @RequestParam(required = false) ExampleStatus status) {
        PageResponse<ExampleResponse> result = service.findAll(page, size, sortBy, sortDirection, status);
        return ResponseEntity.ok(ApiResponse.success("Examples retrieved successfully", result));
    }

    @GetMapping("/{id}")
    @Operation(summary = "Get example by id")
    public ResponseEntity<ApiResponse<ExampleResponse>> findById(@PathVariable UUID id) {
        return ResponseEntity.ok(ApiResponse.success("Example retrieved successfully", service.findById(id)));
    }

    @PostMapping
    @Operation(summary = "Create example")
    public ResponseEntity<ApiResponse<ExampleResponse>> create(@Valid @RequestBody CreateExampleRequest request) {
        ExampleResponse created = service.create(request);
        URI location = ServletUriComponentsBuilder.fromCurrentRequest()
            .path("/{id}").buildAndExpand(created.getId()).toUri();
        return ResponseEntity.created(location).body(ApiResponse.success("Example created successfully", created));
    }

    @PutMapping("/{id}")
    @Operation(summary = "Update example")
    public ResponseEntity<ApiResponse<ExampleResponse>> update(
            @PathVariable UUID id, @Valid @RequestBody UpdateExampleRequest request) {
        return ResponseEntity.ok(ApiResponse.success("Example updated successfully", service.update(id, request)));
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "Delete example")
    public ResponseEntity<Void> delete(@PathVariable UUID id) {
        service.delete(id);
        return ResponseEntity.noContent().build();
    }
}
```

- [ ] **Step 4: Delete the superseded controller**

Delete `templates/base-layered/src/main/java/{{ package_path }}/controller/ExampleController.java`.

- [ ] **Step 5: Run the test to verify it passes**

Render a fresh temp project and run:
```bash
mvn -q -Dtest=ExampleControllerTest test
```
Expected: `BUILD SUCCESS`, 4 tests run, 0 failures.

---

### Task 9: Correlation ID filter and OpenAPI config

**Files:**
- Create: `templates/base-layered/src/main/java/{{ package_path }}/common/config/CorrelationIdFilter.java`
- Create: `templates/base-layered/src/main/java/{{ package_path }}/common/config/OpenApiConfig.java`
- Test: `templates/base-layered/src/test/java/{{ package_path }}/common/config/CorrelationIdFilterTest.java`

**Interfaces:**
- Produces: `CorrelationIdFilter` (a `@Component` servlet `Filter`, auto-registered by Spring Boot). `OpenApiConfig` exposes an `OpenAPI` bean for springdoc.

- [ ] **Step 1: Write `CorrelationIdFilterTest`**

Package `{{ base_package }}.common.config`. Plain JUnit 5, no Spring context — use `org.springframework.mock.web.MockHttpServletRequest`, `MockHttpServletResponse`, `MockFilterChain` (already on the classpath via `spring-boot-starter-test`).

Three `@Test` methods:
- `doFilter_withNoIncomingHeader_generatesAndEchoesCorrelationId`: build a `MockHttpServletRequest`/`MockHttpServletResponse`, use a `MockFilterChain` whose downstream is a lambda capturing `MDC.get("correlationId")` into a local variable during the call, invoke `new CorrelationIdFilter().doFilter(request, response, chain)`, assert the captured MDC value is non-null and equals `response.getHeader("X-Correlation-ID")`.
- `doFilter_withIncomingHeader_reusesIt`: set `request.addHeader("X-Correlation-ID", "test-id-123")` before calling `doFilter`, assert `response.getHeader("X-Correlation-ID")` equals `"test-id-123"`.
- `doFilter_clearsMdcAfterChainCompletes`: after `doFilter` returns, assert `MDC.get("correlationId")` is `null` (cleanup happened in the `finally` block).

- [ ] **Step 2: Run the test to verify it fails**

Compilation fails. Expected red state.

- [ ] **Step 3: Implement `CorrelationIdFilter`**

Package `{{ base_package }}.common.config`:
```java
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class CorrelationIdFilter implements Filter {

    private static final String HEADER = "X-Correlation-ID";
    private static final String MDC_KEY = "correlationId";

    @Override
    public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain)
            throws IOException, ServletException {
        HttpServletRequest httpRequest = (HttpServletRequest) request;
        HttpServletResponse httpResponse = (HttpServletResponse) response;
        String correlationId = httpRequest.getHeader(HEADER);
        if (correlationId == null || correlationId.isBlank()) {
            correlationId = UUID.randomUUID().toString();
        }
        try {
            MDC.put(MDC_KEY, correlationId);
            httpResponse.setHeader(HEADER, correlationId);
            chain.doFilter(request, response);
        } finally {
            MDC.clear();
        }
    }
}
```

- [ ] **Step 4: Implement `OpenApiConfig`**

Package `{{ base_package }}.common.config` (this file is Jinja2-templated — `{{ project_name }}` gets interpolated at render time, same as other files under `templates/base-layered`):
```java
@Configuration
public class OpenApiConfig {

    @Bean
    public OpenAPI exampleServiceOpenAPI() {
        return new OpenAPI().info(new Info()
            .title("{{ project_name }}")
            .version("0.0.1")
            .description("API documentation for {{ project_name }}"));
    }
}
```

- [ ] **Step 5: Run the test to verify it passes**

Render a fresh temp project and run:
```bash
mvn -q -Dtest=CorrelationIdFilterTest test
```
Expected: `BUILD SUCCESS`, 3 tests run, 0 failures.

---

### Task 10: Config profiles, docker-compose, README

**Files:**
- Modify: `templates/base-layered/src/main/resources/application.yml`
- Create: `templates/base-layered/src/main/resources/application-dev.yml`
- Create: `templates/base-layered/src/main/resources/application-prod.yml`
- Modify: `templates/base-layered/README.md`

**Interfaces:**
- No Java interfaces — this task is config/docs only. Verification is a manual render + `mvn spring-boot:run`-style sanity read (no automated test; covered indirectly by Task 12's end-to-end `mvn test-compile` and by manual review).

- [ ] **Step 1: Rewrite `application.yml` to hold only shared defaults**

Replace the full contents:
```yaml
spring:
  application:
    name: {{ artifact_id }}
  profiles:
    active: dev
  liquibase:
    change-log: classpath:db/changelog/db.changelog-master.xml
  jpa:
    hibernate:
      ddl-auto: none

management:
  endpoints:
    web:
      exposure:
        include: health,info

server:
  port: 8080

logging:
  pattern:
    console: "%d{yyyy-MM-dd HH:mm:ss} [%X{correlationId}] %-5level %logger{36} - %msg%n"
```

- [ ] **Step 2: Create `application-dev.yml`**

```yaml
spring:
  datasource:
    url: jdbc:postgresql://localhost:5432/{{ artifact_id.replace('-', '_') }}
    username: forge
    password: forge
  jpa:
    show-sql: true

springdoc:
  swagger-ui:
    enabled: true
```

- [ ] **Step 3: Create `application-prod.yml`**

```yaml
spring:
  datasource:
    url: ${DB_URL}
    username: ${DB_USERNAME}
    password: ${DB_PASSWORD}
  jpa:
    show-sql: false

springdoc:
  api-docs:
    enabled: false
  swagger-ui:
    enabled: false
```

- [ ] **Step 4: Update `README.md`**

Replace the full contents:
```markdown
# {{ project_name }}

Generated by Forge.

## Run locally

    docker compose up -d
    mvn spring-boot:run

Runs with the `dev` Spring profile by default (set in `application.yml`),
which points at the local Postgres container started above. Swagger UI is
available at http://localhost:8080/swagger-ui.html and the health check at
http://localhost:8080/actuator/health.

## Database credentials

The default Postgres credentials (`forge`/`forge`) are hardcoded in
`docker-compose.yml` and `src/main/resources/application-dev.yml` for local
development convenience. Change them before this project is used anywhere
beyond a local dev machine.

## Production profile

Run with `SPRING_PROFILES_ACTIVE=prod` and set `DB_URL`, `DB_USERNAME`,
`DB_PASSWORD` as environment variables — see `application-prod.yml`. The
prod profile disables Swagger UI and SQL logging.
```

- [ ] **Step 5: Verify — render and inspect**

Render a fresh temp project (Task 1 Step 4 snippet), open the generated `application.yml`/`application-dev.yml`/`application-prod.yml`/`README.md`, confirm all Jinja2 placeholders resolved (no literal `{{ ... }}` left) and YAML is well-formed (`python -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" <path>` for each of the three YAML files).

---

### Task 11: Forge wiring — structural paths and generation tests

**Files:**
- Modify: `cli.py:26-48` (`EXPECTED_STRUCTURAL_PATHS`, `expected_structural_paths`)
- Modify: `tests/test_template_content.py`
- Modify: `tests/test_generation.py`

**Interfaces:**
- Consumes: the full new file tree from Tasks 1–10.
- Produces: `expected_structural_paths(context: dict) -> list[Path]` covering every new source and test file — consumed by `cli.py`'s `new` command (already wired at `cli.py:96`) and by `tests/test_generation.py`.

- [ ] **Step 1: Update `EXPECTED_STRUCTURAL_PATHS` in `cli.py`**

Add the two new profile files:
```python
EXPECTED_STRUCTURAL_PATHS = [
    Path("pom.xml"),
    Path("docker-compose.yml"),
    Path(".gitignore"),
    Path("README.md"),
    Path("src/main/resources/application.yml"),
    Path("src/main/resources/application-dev.yml"),
    Path("src/main/resources/application-prod.yml"),
    Path("src/main/resources/db/changelog/db.changelog-master.xml"),
    Path("src/main/resources/db/changelog/001-create-example-table.sql"),
]
```

- [ ] **Step 2: Rewrite `expected_structural_paths` in `cli.py`**

```python
def expected_structural_paths(context: dict) -> list[Path]:
    """Build the rendered Java-source paths the template produces for this run's context."""
    package_path = context["package_path"]
    app_class_name = context["app_class_name"]
    java_root = Path("src/main/java") / package_path
    test_root = Path("src/test/java") / package_path
    common = java_root / "common"
    example = java_root / "example"
    return [
        java_root / f"{app_class_name}Application.java",
        common / "entity" / "BaseEntity.java",
        common / "dto" / "ApiResponse.java",
        common / "dto" / "PageResponse.java",
        common / "dto" / "PaginationMeta.java",
        common / "util" / "PaginationUtils.java",
        common / "exception" / "GlobalExceptionHandler.java",
        common / "exception" / "ResourceNotFoundException.java",
        common / "exception" / "ConflictException.java",
        common / "exception" / "ErrorDetails.java",
        common / "exception" / "ValidationErrorDetails.java",
        common / "config" / "JpaAuditingConfig.java",
        common / "config" / "OpenApiConfig.java",
        common / "config" / "CorrelationIdFilter.java",
        example / "entity" / "Example.java",
        example / "entity" / "ExampleStatus.java",
        example / "dto" / "CreateExampleRequest.java",
        example / "dto" / "UpdateExampleRequest.java",
        example / "dto" / "ExampleResponse.java",
        example / "mapper" / "ExampleMapper.java",
        example / "repository" / "ExampleRepository.java",
        example / "service" / "ExampleService.java",
        example / "service" / "ExampleServiceImpl.java",
        example / "controller" / "ExampleController.java",
        test_root / "common" / "util" / "PaginationUtilsTest.java",
        test_root / "common" / "exception" / "GlobalExceptionHandlerTest.java",
        test_root / "common" / "config" / "CorrelationIdFilterTest.java",
        test_root / "example" / "repository" / "ExampleRepositoryTest.java",
        test_root / "example" / "mapper" / "ExampleMapperTest.java",
        test_root / "example" / "service" / "ExampleServiceImplTest.java",
        test_root / "example" / "controller" / "ExampleControllerTest.java",
    ]
```

- [ ] **Step 3: Update `tests/test_template_content.py`**

Rewrite `EXPECTED_TEMPLATE_FILES` to list the raw (unrendered) template paths mirroring Step 2's structure, prefixed with the literal `{{ package_path }}` and `{{ app_class_name }}` placeholders exactly as the existing entries do, e.g. `"src/main/java/{{ package_path }}/common/entity/BaseEntity.java"`, `"src/test/java/{{ package_path }}/example/controller/ExampleControllerTest.java"`, etc. — one entry per file from the File Structure section's `[Create]`/`[Modify]` list in `src/main` and `src/test`, plus the existing non-Java entries (`pom.xml`, `docker-compose.yml`, `.gitignore`, `README.md`, `application.yml`, `application-dev.yml`, `application-prod.yml`, both changelog files). Remove the four old layer-based paths (`entity/Example.java`, `repository/ExampleRepository.java`, `service/ExampleService.java`, `controller/ExampleController.java`) since Tasks 5/7/8 delete them.

- [ ] **Step 4: Extend `tests/test_generation.py`**

Add an import of `expected_structural_paths` alongside the existing `EXPECTED_STRUCTURAL_PATHS`/`TEMPLATE_DIR` import, and after the existing `structural` assertion, add:
```python
from cli import EXPECTED_STRUCTURAL_PATHS, TEMPLATE_DIR, expected_structural_paths
...
    dynamic_paths = expected_structural_paths(config.template_context())
    dynamic_structural = check_structure(config.target_dir, dynamic_paths)
    assert dynamic_structural.passed, dynamic_structural.details
```
placed right after the existing `structural = check_structure(...)` / `assert structural.passed` pair, before the `compile_result = run_compile(...)` line.

- [ ] **Step 5: Run the full Forge test suite**

```bash
.venv\Scripts\pytest tests/test_template_content.py tests/test_generation.py -v
```
Expected: all tests pass. `test_generation.py`'s `run_compile` call (still `mvn compile` at this point — Task 12 changes it to `test-compile`) exercises the entire new source tree end-to-end for the first time; this is the main integration checkpoint for Tasks 1–10. Investigate and fix any compile errors surfaced here before moving to Task 12.

---

### Task 12: Validator upgrade and final end-to-end verification

**Files:**
- Modify: `core/validator.py:28-48` (`run_compile`)
- Modify: `tests/test_validator.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `run_compile` now runs the Maven `test-compile` phase (compiles main **and** test sources, without executing tests) instead of `compile` — closing the gap noted in the spec's Testing section, where `mvn compile` alone wouldn't catch a broken test file.

- [ ] **Step 1: Add a test proving `run_compile` catches a broken test source**

In `tests/test_validator.py`, add (using the existing `MINIMAL_POM`/`MINIMAL_JAVA` fixtures already in the file):
```python
def test_run_compile_fails_for_broken_java_test_source(tmp_path):
    (tmp_path / "pom.xml").write_text(MINIMAL_POM, encoding="utf-8")
    main_dir = tmp_path / "src" / "main" / "java" / "com" / "example"
    main_dir.mkdir(parents=True)
    (main_dir / "Hello.java").write_text(MINIMAL_JAVA, encoding="utf-8")
    test_dir = tmp_path / "src" / "test" / "java" / "com" / "example"
    test_dir.mkdir(parents=True)
    (test_dir / "HelloTest.java").write_text("this is not valid java", encoding="utf-8")

    result = run_compile(tmp_path)

    assert result.passed is False
    assert result.details
```

- [ ] **Step 2: Run the new test to verify it fails**

```bash
.venv\Scripts\pytest tests/test_validator.py::test_run_compile_fails_for_broken_java_test_source -v
```
Expected: FAIL — `run_compile` currently only runs `mvn compile`, which never touches `src/test`, so the broken test file goes undetected and `result.passed` is `True`.

- [ ] **Step 3: Change `run_compile` to run `test-compile`**

In `core/validator.py`, change the Maven invocation:
```python
result = subprocess.run(
    [mvn_cmd, "-q", "test-compile"],
    ...
)
```
Update the function's docstring to: `"""Run mvn test-compile in target_dir (compiles main and test sources, without executing tests) and report whether it succeeded."""`

- [ ] **Step 4: Run the full validator test suite to verify all tests pass**

```bash
.venv\Scripts\pytest tests/test_validator.py -v
```
Expected: all tests pass, including the existing `test_run_compile_passes_for_a_valid_minimal_maven_project` (a project with no `src/test` directory still `test-compile`s cleanly — there's simply nothing to compile there) and the new broken-test-source case.

- [ ] **Step 5: Run the complete Forge test suite**

```bash
.venv\Scripts\pytest -v
```
Expected: all tests pass. This now runs `mvn test-compile` against the fully rewritten template inside `test_generation.py`, which compiles every file from Tasks 1–10 including all seven new test classes — the strongest single signal that the whole rewrite is internally consistent (correct imports, matching signatures across `common/`↔`example/`, no leftover references to deleted classes).

- [ ] **Step 6: Manual full-stack smoke check (requires Docker)**

Render one more fresh temp project (Task 1 Step 4 snippet), then from inside it:
```bash
docker compose up -d
mvn spring-boot:run
```
In a second terminal, exercise the API: `curl -X POST http://localhost:8080/api/v1/examples -H "Content-Type: application/json" -d "{\"name\":\"Widget\"}"` should return `201` with a `Location` header and an `ApiResponse` envelope body; `curl http://localhost:8080/actuator/health` should return `{"status":"UP"}`; `curl http://localhost:8080/swagger-ui/index.html` should return the Swagger UI HTML. Stop the app (`Ctrl+C`) and run `docker compose down -v` afterward. Report results; this step is exploratory validation, not a scripted pass/fail gate.

---

## Self-Review Notes

- **Spec coverage:** every section of the spec (`docs/superpowers/specs/2026-08-14-production-ready-template-design.md`) maps to a task — package structure (all tasks), domain model (5), DTOs/validation/mapping (6), common envelope (2), error handling (4), repository (5), service (7), controller (8), observability/ops (9, 10), config profiles (10), migration (5), testing (2/4/5/6/7/8/9 individually + 11/12 wiring), dependency changes (1), Forge wiring changes (11, 12).
- **Type consistency checked:** `PaginationUtils.toPageResponse`/`createPageable` signatures (Task 2) match their call sites in `ExampleServiceImpl` (Task 7); `ExampleMapper`'s three method signatures (Task 6) match their call sites in `ExampleServiceImpl` (Task 7); `ExampleService` interface methods (Task 7 Step 3) match `ExampleServiceImpl`'s implementations (Task 7 Step 4) and `ExampleController`'s call sites (Task 8); `ApiResponse.success`/`error` factory signatures (Task 2) match every call site in `GlobalExceptionHandler` (Task 4) and `ExampleController` (Task 8).
- **No placeholders:** every step above states exact class/method signatures and either full implementation code or a fully specified test scenario (fixture values, assertions) — none deferred to "later" or described only abstractly.
