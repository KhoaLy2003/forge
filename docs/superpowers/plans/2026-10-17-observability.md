# Backend Observability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Repo conventions that override the skill defaults:** do NOT run `git commit`/`git push` at any step; leave all changes in the working tree until the user reviews. Steps describe *what* to write and *which signatures*; write the real code fresh and verify it against a real compiler/test run.

**Goal:** Generated `base-layered` projects meet the cross-project observability standard (Phase 1 logging in both templates, Phase 3 metrics/monitoring stack in `base-layered`), and Forge statically validates the monitoring files.

**Architecture:** Spring Boot structured logging (ECS JSON in `prod`) plus small servlet filters/helpers in `common/config`; Micrometer + Prometheus on a separate management port; a rendered `observability/` folder (Prometheus, alerts, Grafana, Loki, Alloy) with a compose overlay and runbook; a Docker-free Forge validator `check_observability`. Gating uses a new `ForgeConfig.include_monitoring` flag and `minimal`'s `EXCLUDES`.

**Tech Stack:** Python 3.11 (Typer, Jinja2, pydantic, PyYAML, pytest), Java 21, Spring Boot 4.1 (version taken from the template's `pom.xml`), Micrometer, JUnit 5/AssertJ/MockHttpServlet*.

**Spec:** `docs/superpowers/specs/2026-10-17-observability-design.md`. Reference (read-only, do not edit): `F:\Khoa-TonyRay\learning\projects\meowgo\meowgo_server_java` (`common/config/CorrelationIdFilter.java`, `RequestLogFilter.java`, `JobContext.java`, their tests, `application*.yml`). Standard: `F:\Khoa-TonyRay\learning\projects\knowledge-base\cross-project-observability-standard.md`.

## Global Constraints

- Work only in `backend/` (and `docs/`). Do not touch `frontend/` or MeowGo.
- Local machine has **no Docker**: nothing run locally may need Docker. `mvn` is available and is used for `test-compile` and for the Docker-free logging tests.
- MDC key is `request_id` (not `correlationId`). Inbound `X-Correlation-ID` is reused only if it matches `[A-Za-z0-9._-]{1,64}`.
- `RequestLogFilter` never reads query strings, headers, cookies or bodies; route is the matched pattern or `UNMATCHED`.
- Event names: `http.request.completed`, `notification.*`-style `domain.entity.action[.outcome]`; no IDs in event names.
- ECS output only in `prod`; `dev` keeps a text pattern containing `%X{request_id}`. Stack traces bounded at 4096 characters (`logging.structured.json.stacktrace.max-length`).
- Management port default `8081`; env override `MANAGEMENT_SERVER_PORT`. Prometheus retention 15d, Loki retention 7d (local defaults, documented as such).
- `minimal` gets Phase 1 only. Its `EXCLUDES` add exactly: `observability/*`, `docker-compose.observability.yml`, `docs/observability/runbook.md`.
- `include_monitoring` is `self.template != "minimal"`, exposed through `template_context()`.
- Jinja delimiters `{{ }}` inside Grafana JSON / Alloy / alert templates must be wrapped in `{% raw %}...{% endraw %}`.
- Generated tests must not need Docker or a database; new classes must keep the template's 90% JaCoCo line gate satisfiable in the generated project's CI.
- No new CLI flags, no wizard prompts.

## Review Focus

- A client sends `X-Correlation-ID` containing CR/LF, spaces, 65+ characters, or an empty value → replaced by a UUID; response header never echoes the bad value (Task 2).
- A request to an unmapped path with `?token=secret&email=a@b.c` → log event has route `UNMATCHED` and the line contains neither query value (Task 3).
- A handler throws → exactly one ERROR `http.request.completed` event (status 500) and MDC `request_id` is removed afterward; other MDC keys set by callers survive (Tasks 2–3).
- A user-supplied string containing `\n{"fake":true}` logged in `prod` format stays inside one JSON line (Task 6).
- A scheduled job throws inside `JobContext.run` → MDC `job`/`request_id` are cleared on the pooled thread (Task 4).
- An alert expression or dashboard query references a metric the app does not expose → `check_observability` fails with the metric name (Task 11).

---

### Task 1: `include_monitoring` flag and `minimal` exclusions

**Files:**
- Modify: `backend/core/config_schema.py` (add property + context key)
- Modify: `backend/templates/minimal/manifest.py` (add three globs)
- Test: `backend/tests/test_config_schema.py`, `backend/tests/test_template_manifests.py`

**Interfaces:**
- Produces: `ForgeConfig.include_monitoring: bool`; `template_context()["include_monitoring"]`; `minimal` manifest `EXCLUDES` containing `observability/*`, `docker-compose.observability.yml`, `docs/observability/runbook.md`. Later tasks create files matching those globs.

- [ ] **Step 1:** Write failing tests: `include_monitoring` is `True` for `base-layered`, `False` for `minimal`; `template_context()` contains the key; `discover_templates()["minimal"]` contains the three globs and `["base-layered"]` is still `()`.
- [ ] **Step 2:** Run `.venv\Scripts\pytest backend/tests/test_config_schema.py backend/tests/test_template_manifests.py -v`. Expected: FAIL.
- [ ] **Step 3:** Implement the property (mirror `use_liquibase`) and the context entry; add the globs to the manifest.
- [ ] **Step 4:** Re-run those tests. Expected: manifest test `test_each_exclude_pattern_matches_at_least_one_shared_file[minimal]` will FAIL until Task 9/10 create files matching the new globs. Mark the three new globs' coverage check as expected-red; do not weaken the test. Proceed and re-run after Task 10.

### Task 2: Rewrite `CorrelationIdFilter` (`request_id`, validated, own-key removal)

**Files:**
- Modify: `backend/templates/_shared/src/main/java/{{ package_path }}/common/config/CorrelationIdFilter.java`
- Modify: `backend/templates/_shared/src/test/java/{{ package_path }}/common/config/CorrelationIdFilterTest.java`
- Modify: `backend/templates/_shared/src/main/resources/application.yml` (pattern uses `%X{request_id}`)

**Interfaces:**
- Produces: `public static final String MDC_KEY = "request_id"` on `CorrelationIdFilter` (used by Tasks 3, 4); header constant stays `X-Correlation-ID`.

- [ ] **Step 1:** Extend the test class: reused valid id; generated when absent; replaced when containing CR/LF, a space, 65 characters, or blank; response header equals the MDC value; a pre-existing unrelated MDC key survives the request; `request_id` is removed after the request even when the chain throws.
- [ ] **Step 2:** Render the template into `_testing/obs` (see Task 13 helper or a one-off `render_tree` call) and run `mvn -q test -Dtest=CorrelationIdFilterTest`. Expected: FAIL.
- [ ] **Step 3:** Implement per the spec: `Pattern.compile("[A-Za-z0-9._-]{1,64}")`, `MDC.remove(MDC_KEY)` in `finally`, keep `@Order(HIGHEST_PRECEDENCE)`. Port javadoc style from MeowGo's version (read it first).
- [ ] **Step 4:** Update the `logging.pattern.console` line in `application.yml` to use `request_id`. Re-run the test. Expected: PASS.

### Task 3: `RequestLogFilter`

**Files:**
- Create: `backend/templates/_shared/src/main/java/{{ package_path }}/common/config/RequestLogFilter.java`
- Test: `backend/templates/_shared/src/test/java/{{ package_path }}/common/config/RequestLogFilterTest.java`

**Interfaces:**
- Consumes: `CorrelationIdFilter` ordering (`HIGHEST_PRECEDENCE`).
- Produces: `@Component @Order(HIGHEST_PRECEDENCE + 1) class RequestLogFilter extends OncePerRequestFilter`; constructor `RequestLogFilter(@Value("${app.logging.slow-request-ms:2000}") long)`; package-private `static final String UNMATCHED_ROUTE = "UNMATCHED"`.

- [ ] **Step 1:** Port MeowGo's `RequestLogFilterTest` as the starting point (read it), adapting package names. Cases: matched route attribute (`HandlerMapping.BEST_MATCHING_PATTERN_ATTRIBUTE`) is logged as template; no attribute → `UNMATCHED`; query string/header/cookie/body values never appear in the captured events (use a logback `ListAppender` on the filter's logger); levels: 200 → INFO, 500 or thrown exception → ERROR with status 500, duration ≥ threshold → WARN, `/actuator/health` → DEBUG; key-values `event.name`, `http.request.method`, `http.route`, `http.response.status_code`, `duration_ms` present.
- [ ] **Step 2:** Run `mvn -q test -Dtest=RequestLogFilterTest` in a rendered project. Expected: FAIL (class missing).
- [ ] **Step 3:** Implement following MeowGo's class; level selection helper and `route(request)` helper as private methods; health path prefix `/actuator/health`.
- [ ] **Step 4:** Re-run. Expected: PASS. Add the "unmapped path with `?token=secret`" case from Review Focus if not already covered.

### Task 4: `JobContext`

**Files:**
- Create: `.../common/config/JobContext.java`, test `.../common/config/JobContextTest.java` (same template roots as above)

**Interfaces:**
- Produces: `public final class JobContext { public static final String JOB_KEY = "job"; public static void run(String job, Runnable task) }` — puts `job` and a fresh `request_id` (key from `CorrelationIdFilter.MDC_KEY`) in MDC, removes both in `finally`, lets exceptions propagate. Consumed by the notification plan's `DeliveryWorker`.

- [ ] **Step 1:** Tests: MDC has both keys inside the task; both removed after normal completion; both removed and exception rethrown unchanged when the task throws; each run gets a different `request_id`; pre-existing unrelated MDC keys untouched.
- [ ] **Step 2:** Run `mvn -q test -Dtest=JobContextTest`. Expected: FAIL.
- [ ] **Step 3:** Implement (private constructor, as MeowGo). **Step 4:** Re-run. Expected: PASS.

### Task 5: `SensitiveDataCustomizer`

**Files:**
- Create: `.../common/config/SensitiveDataCustomizer.java`, test `.../common/config/SensitiveDataCustomizerTest.java`

**Interfaces:**
- Produces: a Spring bean implementing Spring Boot's `StructuredLoggingJsonMembersCustomizer` (confirm the exact type/package in the Boot version from the template `pom.xml` by inspecting the `spring-boot` jar on the local Maven repo, `~/.m2`) that masks values (replace with `***`) of members whose key matches `(?i)(pass(word)?|secret|token|authorization|cookie|api[_-]?key)`.

- [ ] **Step 1:** Spike: find the customizer SPI and how it is registered (`logging.structured.json.customizer` property takes a class name). Record the finding in a comment at the top of the class. If the SPI cannot see MDC/key-value members, fall back to masking in a `JsonWriter` member filter and document the limitation in `docs/observability/logging.md` (Task 10).
- [ ] **Step 2:** Test: format a log event (via the ECS formatter built from `StructuredLogFormatter` support, or via `ApplicationContextRunner` if direct construction is impractical) with MDC `access_token=abc123` and key-value `password=hunter2` plus a normal key; assert the output JSON contains `***` for the sensitive keys, the original secrets appear nowhere in the line, and the normal key is intact.
- [ ] **Step 3:** Run `mvn -q test -Dtest=SensitiveDataCustomizerTest`. Expected: FAIL. Implement. Re-run. Expected: PASS.

### Task 6: Logging configuration and log-format test

**Files:**
- Modify: `.../resources/application.yml`, `application-prod.yml`, `application-dev.yml`; `.../pom.xml` (resource filtering for `@project.version@` if not already effective)
- Test: `.../src/test/java/{{ package_path }}/common/config/StructuredLogFormatTest.java`

**Interfaces:**
- Consumes: Tasks 2–5 classes.
- Produces: config keys `app.logging.slow-request-ms: 2000`; `logging.structured.format.console: ecs`, `logging.structured.ecs.service.{name,version,environment}`, `logging.structured.json.stacktrace.max-length: 4096`, `logging.structured.json.customizer: <SensitiveDataCustomizer FQCN>` in `application-prod.yml`; `${DEPLOYMENT_ENVIRONMENT:production}`; `dev` environment `development`.

- [ ] **Step 1:** Write `StructuredLogFormatTest` (plain JUnit): produce one event through the ECS formatter configured as in `prod` and assert it parses as JSON with `@timestamp`, `log.level`, `message`, `service.name`, `service.version`, `service.environment`, `request_id`; assert an injected value `x\n{"fake":true}` yields exactly one line and the quote/newline are escaped; assert a long stack trace is truncated to ≤ 4096 characters of the trace field.
- [ ] **Step 2:** Run it. Expected: FAIL. Apply the config; align property names with MeowGo's `application-prod.yml` and the Boot version in `pom.xml`. If `@project.version@` isn't substituted in the Jinja-rendered file, enable filtering for that one resource in `pom.xml`.
- [ ] **Step 3:** Run `mvn -q test -Dtest=StructuredLogFormatTest`. Expected: PASS. Then `mvn -q test-compile` on a rendered `base-layered` and a rendered `minimal`.

### Task 7: `GlobalExceptionHandler` logging review

**Files:**
- Modify: `.../common/exception/GlobalExceptionHandler.java`, `.../test/.../GlobalExceptionHandlerTest.java`

- [ ] **Step 1:** Add tests asserting each handler logs once, includes a stable `event.name` key-value (`request.not_found`, `request.conflict`, `request.validation.failed`, `request.unexpected`), and the unexpected-exception handler logs the stack trace at ERROR while the 4xx handlers log at WARN without exception messages that may contain user data (check what messages the current handlers interpolate and keep only constants/ids already public).
- [ ] **Step 2:** Run `mvn -q test -Dtest=GlobalExceptionHandlerTest`. Expected: FAIL. **Step 3:** Update the handlers. **Step 4:** Re-run. Expected: PASS.

### Task 8: Metrics on the app side (`include_monitoring`)

**Files:**
- Modify: `.../pom.xml` (micrometer-registry-prometheus under `{% if include_monitoring %}`), `.../resources/application.yml` (management block)
- Test: `.../src/test/java/{{ package_path }}/common/config/ManagementConfigTest.java` (templated with `{% if include_monitoring %}`; file excluded for `minimal` by wrapping content, or add its path to the `minimal` EXCLUDES and Task 1's test list)

**Interfaces:**
- Produces: `management.server.port: ${MANAGEMENT_SERVER_PORT:8081}`; `management.endpoints.web.exposure.include: health,info,prometheus`; `management.endpoint.health.probes.enabled: true`; `management.metrics.tags.application: ${spring.application.name}`; `management.metrics.tags.environment`; `management.metrics.distribution.percentiles-histogram.http.server.requests: true`. For `minimal` the block stays `health,info` with no separate port.

- [ ] **Step 1:** Write a Docker-free test that loads `application.yml` with Spring's `YamlPropertySourceLoader` and asserts the keys above (no application context, no DB). Add it to the `minimal` exclusion by path if it is only valid for monitoring.
- [ ] **Step 2:** Run it. Expected: FAIL. **Step 3:** Add the conditionals. **Step 4:** Re-run on a rendered `base-layered`; `mvn -q test-compile` on both templates. Expected: PASS and `minimal` has no `micrometer-registry-prometheus` in its `pom.xml`.

### Task 9: Monitoring stack files (`base-layered` only)

**Files (all new, under `backend/templates/_shared/`):**
`docker-compose.observability.yml`, `observability/prometheus/prometheus.yml`, `observability/prometheus/alerts.yml`, `observability/grafana/provisioning/datasources/datasources.yml`, `observability/grafana/provisioning/dashboards/dashboards.yml`, `observability/grafana/dashboards/service-overview.json`, `observability/loki/loki-config.yml`, `observability/alloy/config.alloy`

**Interfaces:**
- Produces: metric names used in expressions: `up`, `http_server_requests_seconds_count|sum|bucket`, `jvm_memory_used_bytes`, `jvm_memory_max_bytes`, `hikaricp_connections_active`, `hikaricp_connections_max`, `process_cpu_usage` (this is the set Task 11's registry must accept). Alert names: `ServiceDown`, `HighErrorRatio`, `HighLatencyP95`, `JvmHeapSaturation`, `DbPoolSaturation`, each with labels `severity`, `team: {{ project_name }}` and annotations `summary`, `impact`, `first_checks`, `runbook`.

- [ ] **Step 1:** Write the files. Prometheus scrapes `host.docker.internal:8081` path `/actuator/prometheus` with a `service` label and 15d retention flag in the compose overlay; Loki retention 7d; Alloy reads Docker container logs and ships to Loki with low-cardinality labels (service, environment) only. Wrap any `{{`/`}}` (Grafana legends, Prometheus annotation templates) in `{% raw %}`.
- [ ] **Step 2:** Render a `base-layered` project into `_testing/obs` and confirm all files appear; confirm `minimal` render lacks them (this also turns Task 1's manifest test green).
- [ ] **Step 3:** Run `.venv\Scripts\pytest backend/tests/test_template_manifests.py -v`. Expected: PASS.

### Task 10: Documentation in the template

**Files:**
- Create: `backend/templates/_shared/docs/observability/logging.md` (both templates), `backend/templates/_shared/docs/observability/runbook.md` (`base-layered` only, per Task 1 glob)
- Modify: `backend/templates/_shared/README.md` (Observability section)

- [ ] **Step 1:** `logging.md`: field mapping table (copy from the spec), severity policy, event-naming rules, "rules for new log lines", stdout-only decision, retention statement with a fill-in table, a short "where to find logs / filter by `request_id`" section (this is the `minimal` runbook substitute, OBS-10), and any limitation recorded in Task 5.
- [ ] **Step 2:** `runbook.md`: where logs/metrics/alerts live; investigating error, latency, saturation; telling app failure from telemetry failure; ownership/escalation placeholders; secrets-in-logs handling; threshold caveats (starting points; low-traffic services need absolute counts); management port must not be published beyond the monitoring network.
- [ ] **Step 3:** Render both templates; confirm `minimal` has `logging.md` but no `runbook.md`.

### Task 11: `check_observability` validator

**Files:**
- Modify: `backend/core/validator.py`, `backend/pyproject.toml` (add `pyyaml>=6.0`)
- Create: `backend/core/observability_metrics.py` (the registry)
- Test: `backend/tests/test_validator.py` (add cases) and new `backend/tests/test_observability_metrics.py`

**Interfaces:**
- Produces: `KNOWN_METRICS: frozenset[str]` and `PROMQL_WORDS: frozenset[str]` in `observability_metrics.py`; `extract_metric_names(expr: str) -> set[str]` (tokenizes snake_case identifiers, drops PromQL functions/keywords/label names/numbers); `check_observability(target_dir: Path, include_monitoring: bool) -> ValidationResult` — returns passed immediately when `include_monitoring` is false; otherwise checks: required files exist, YAML files parse (`safe_load`), dashboard JSON parses, every alert `expr` and every dashboard target `expr` references only `KNOWN_METRICS`, each alert has labels `severity` and `team` and annotations `summary`, `impact`, `first_checks`, `runbook`.

- [ ] **Step 1:** Write failing tests with tiny fixture trees in `tmp_path`: valid tree passes; missing file, malformed YAML, unknown metric (`foo_bar_total`) fails and the message names it; alert without `severity` fails; `include_monitoring=False` passes with an empty dir. Unit-test `extract_metric_names` on `histogram_quantile(0.95, sum by (le) (rate(http_server_requests_seconds_bucket[5m])))` → `{"http_server_requests_seconds_bucket"}`.
- [ ] **Step 2:** Run `.venv\Scripts\pytest backend/tests/test_observability_metrics.py backend/tests/test_validator.py -v`. Expected: FAIL.
- [ ] **Step 3:** Implement. Install PyYAML: `.venv\Scripts\pip install -e "./backend[dev]"`.
- [ ] **Step 4:** Re-run. Expected: PASS. Then run `check_observability` against a freshly rendered `base-layered` project and fix any file/registry mismatch from Task 9 (fix the registry or the file, whichever is wrong).

### Task 12: Wire into the CLI and the generated CI

**Files:**
- Modify: `backend/cli.py` (structural paths; pipeline step), `backend/templates/_shared/.github/workflows/ci.yml`
- Test: `backend/tests/test_cli.py`, `backend/tests/test_template_content.py`

**Interfaces:**
- Consumes: `check_observability` (Task 11), `include_monitoring`.

- [ ] **Step 1:** Add to the expected structural lists: `docs/observability/logging.md`, the `common/config` Java files (`RequestLogFilter`, `JobContext`, `SensitiveDataCustomizer`) and their tests; add the monitoring files as a separate list returned only when `context["include_monitoring"]` is true (or rely on `filter_excluded_paths`, as for other `minimal` exclusions).
- [ ] **Step 2:** Test (CLI, using the existing `test_cli.py` style with a patched `run_compile`): pipeline calls `check_observability` between structure and compile; a failing observability result aborts with the delete-folder prompt. Update the step counter (`n/total`) and its test.
- [ ] **Step 3:** Implement. Add the `observability-config` CI job under `{% if include_monitoring %}` (runs `docker run` of `prom/prometheus` entrypoint `promtool check config` and `check rules`, and `docker compose -f docker-compose.yml -f docker-compose.observability.yml config -q`; no new third-party action; `permissions: contents: read`; `persist-credentials: false` on checkout as in other jobs, same pinned checkout SHA). `{% raw %}` where GitHub `${{ }}` appears.
- [ ] **Step 4:** Test: rendered `ci.yml` for `base-layered` contains the job and for `minimal` does not; rendered YAML parses. Run `.venv\Scripts\pytest backend/tests/test_cli.py backend/tests/test_template_content.py -v`. Expected: PASS.

### Task 13: End-to-end generation test and Docker-free log tests

**Files:**
- Modify: `backend/core/validator.py` (add `run_tests(target_dir, test_filter, timeout=300) -> ValidationResult`, shells `mvn -q test -Dtest=<filter>`), `backend/tests/test_generation.py`, `backend/tests/test_validator.py`

**Interfaces:**
- Produces: `run_tests(target_dir: Path, test_filter: str, timeout: int = 300) -> ValidationResult`.

- [ ] **Step 1:** Unit-test `run_tests` the same way `run_compile` is tested (fake project in `tmp_path`, missing `mvn`, timeout, failure output).
- [ ] **Step 2:** Extend `test_generation.py`: for both templates also run `run_tests(..., "CorrelationIdFilterTest,RequestLogFilterTest,JobContextTest,SensitiveDataCustomizerTest,StructuredLogFormatTest,GlobalExceptionHandlerTest")`; for `minimal` assert no `observability/` dir, no `docker-compose.observability.yml`, no `micrometer-registry-prometheus` in `pom.xml`, `docs/observability/logging.md` exists, `runbook.md` absent; for `base-layered` assert `check_observability(...).passed`.
- [ ] **Step 3:** Run `.venv\Scripts\pytest backend/tests -v` with `mvn` on PATH. Expected: all PASS.

### Task 14: Docs

**Files:** `backend/README.md`, `backend/QUICK_REFERENCE.md`, `backend/CHANGELOG.md`, `docs/superpowers/specs/2026-10-17-entity-modeling-design.md` (roadmap line 14: note that actuator/Prometheus is delivered by the observability spec)

- [ ] **Step 1:** Describe the new generated files, `include_monitoring`, the validator step, and the Docker-in-CI note. **Step 2:** Run the full suite once more (`.venv\Scripts\pytest backend/tests -v`). Expected: PASS.

---

## Self-Review notes

- Spec coverage: Phase 1 components (Tasks 2–7), config/identity (6), Phase 3 app side (8) and stack (9), docs/runbook/retention (10), Forge validator (11), CLI/CI (12), testing section (13), roadmap note (14). OBS-05/OBS-09 intentionally documented only (Task 10).
- Open spike points are explicit steps (Task 5 SPI, Task 6 property names/filtering), not placeholders.
