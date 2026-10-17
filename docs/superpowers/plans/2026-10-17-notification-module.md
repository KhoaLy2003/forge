# Backend Notification Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Repo conventions that override the skill defaults:** do NOT run `git commit`/`git push` at any step. Steps describe *what* to write and *which signatures*; write the real code fresh and verify it with a real compile/test run. **Prerequisite:** the observability plan (`2026-10-17-observability.md`) is implemented first — this plan uses `JobContext`.

**Goal:** Generated `base-layered` projects include a database-outbox notification module: in-app inbox + email, retries, templates, preferences and an inbox REST API, with `ChannelSender`, `RecipientDirectory` and `CurrentRecipientProvider` extension points.

**Architecture:** A `notification/` slice (service, JPA for templates/preferences, `JdbcTemplate` `NotificationQueries` for the outbox with `FOR UPDATE SKIP LOCKED` + lease), a scheduled `DeliveryWorker`/`DeliveryProcessor`, and a controller whose caller identity is supplied by an interface. Excluded from `minimal` by glob.

**Tech Stack:** Spring Boot 4.1 (`spring-boot-starter-mail`, Spring `@Scheduled`, `JdbcTemplate`), Liquibase SQL changelog, JUnit 5/Mockito/AssertJ, `@WebMvcTest`, Testcontainers (CI-only), Python/pytest for Forge.

**Spec:** `docs/superpowers/specs/2026-10-17-notification-module-design.md`. Reference (read-only): `F:\Khoa-TonyRay\learning\projects\meowgo\meowgo_server_java\src\main\java\com\meowgo\meowgoserver\notifications\` and `src\main\resources\db\changelog\006-create-notifications.sql`, `007-add-delivery-dismissed-at.sql`, with tests under `src\test\java\...\notifications\`.

## Global Constraints

- Work only in `backend/` and `docs/`. MeowGo is read-only.
- Template placement: `templates/_shared/`; `minimal` `EXCLUDES` add exactly `src/main/java/{{ package_path }}/notification/*`, `src/test/java/{{ package_path }}/notification/*`, `src/main/resources/db/changelog/002-create-notifications.sql`. No new `ForgeConfig` property; conditionals use `use_liquibase`.
- Channels: `IN_APP`, `EMAIL` only (`dbValue()` `in_app`, `email`). No push, device tokens, admin API, "all users" audience or fan-out.
- Migration file `002-create-notifications.sql` (the entity-modeling plan numbers its changelogs from `003`). Tables: `notification_templates`, `notifications`, `deliveries`, `notification_preferences` exactly as the spec's data-model table; `deliveries.recipient_id` has no FK; JSONB `data`; partial unique index on `idempotency_key`; every changeset has `-- rollback`.
- Seed one `welcome` template for `in_app` and `email`, locale `en`, with a `{{name}}` placeholder (wrap in `{% raw %}` in the template file).
- Retry delays 60s, 300s, 1800s, 7200s; `app.notifications.max-attempts` default 5; explicit audience size 1–500; default locale `app.notifications.default-locale: en`.
- Skip reasons: `opted_out`, `no_template`, `email_not_configured`, `recipient_unresolved`, `cancelled`.
- `enqueue` is `@Transactional(REQUIRED)`; the processor performs network I/O outside any transaction.
- Logs never contain recipient addresses, message bodies or tokens; event names `notification.delivery.failed` / `notification.delivery.skipped` / `notification.accepted`.
- Default `CurrentRecipientProvider` yields no caller → API answers `401`; no endpoint accepts a recipient id from the client; no endpoint creates notifications.
- Local machine has no Docker: Docker-free tests must pass with `mvn`; `NotificationQueries` SQL tests are Testcontainers tests that run only in CI.
- Mail settings come from env vars with empty defaults (blank host = not configured); nothing secret committed.
- `{{ }}` in any template file → `{% raw %}`.

## Review Focus

- Same idempotency key sent twice (including concurrently) → one notification, second call returns `duplicate=true` with the original id (Task 6, CI test in Task 5).
- Template has `{{name}}` but request data omits it → `enqueue` rejects with a message naming `name`; nothing is written (Task 6).
- Recipient has no resolvable email (default `RecipientDirectory`) → email delivery is `skipped/recipient_unresolved`, in-app still delivered, no retry loop (Task 9).
- SMTP down mid-batch → that delivery retries with backoff and finally `failed` after 5 attempts; other deliveries in the batch are unaffected (Task 9, 10).
- Two worker instances tick simultaneously → each delivery is claimed once (Task 5, CI test) and a crashed claimer's lease expires and is re-claimed.
- User A requests delivery id belonging to user B (mark read / dismiss) → 404, not 200 (Tasks 7, 11).
- Default provider in a freshly generated project → every `/api/v1/notifications` endpoint returns 401 and the app still starts with the worker running and no mail configured (Tasks 8, 11, 12).

---

### Task 1: Migration, changelog include, and `minimal` exclusions

**Files:**
- Create: `backend/templates/_shared/src/main/resources/db/changelog/002-create-notifications.sql`
- Modify: `.../db/changelog/db.changelog-master.xml` (add include for `002`, inside `{% if use_liquibase %}` — the whole file is already absent from `minimal` only via the changelog glob, so keep it unconditional and rely on the existing `db/changelog/*` exclusion)
- Modify: `backend/templates/minimal/manifest.py`
- Test: `backend/tests/test_template_manifests.py`, `backend/tests/test_template_content.py`

**Interfaces:**
- Produces: tables listed in Global Constraints; `minimal` EXCLUDES additions.

- [ ] **Step 1:** Failing tests: `minimal` excludes include the three globs and each matches ≥1 shared file; rendered master changelog for `base-layered` includes `002-create-notifications.sql` after `001`; the migration text contains `CREATE TABLE` for each of the four tables, the partial unique index, and a `rollback` per table.
- [ ] **Step 2:** Run `.venv\Scripts\pytest backend/tests/test_template_manifests.py backend/tests/test_template_content.py -v`. Expected: FAIL.
- [ ] **Step 3:** Write the migration by adapting MeowGo `006` (drop `device_tokens`, `push` from channel check, `all` audience check, fan-out columns, `push_enabled`, `locale` in preferences; add `dismissed_at` from `007` into `deliveries`; add `provider_message_id`) and the seed. Update the master changelog and the manifest. (Glob matches need files from Tasks 3–11 to exist; re-run this test file at Task 12.)
- [ ] **Step 4:** Re-run the content tests. Expected: PASS (manifest glob checks for the Java globs turn green by Task 3).

### Task 2: Dependencies, scheduling, configuration

**Files:**
- Modify: `.../pom.xml` (`spring-boot-starter-mail` under `{% if use_liquibase %}`), `.../{{ app_class_name }}Application.java` (`@EnableScheduling` — guard with `{% if use_liquibase %}`), `.../resources/application.yml`
- Test: `backend/tests/test_template_content.py`

**Interfaces:**
- Produces: config keys `app.notifications.{worker-delay-ms: 3000, batch-size: 100, lease-seconds: 300, max-attempts: 5, default-locale: en}`, `app.mail.{host,port,username,password,from,starttls}` from `${MAIL_*}` env with empty defaults; `spring.mail` wiring is handled by Task 8's config.

- [ ] **Step 1:** Failing content tests: rendered `base-layered` pom contains the mail starter and application class has `@EnableScheduling`; rendered `minimal` has neither.
- [ ] **Step 2:** Run them; expected FAIL. **Step 3:** Implement. **Step 4:** Re-run; expected PASS; render both templates and run `mvn -q test-compile`.

### Task 3: Core types and `TemplateRenderer`

**Files:** under `backend/templates/_shared/src/main/java/{{ package_path }}/notification/` and the matching `src/test/...`: `Audience.java`, `NotificationChannel.java`, `NotificationRequest.java`, `NotificationAck.java`, `NotificationStatus.java`, `DeliveryStatus.java`, `TemplateRenderer.java`; test `TemplateRendererTest.java`

**Interfaces:**
- Produces (exact):
  - `record Audience(String type, Set<UUID> userIds)` with `static Audience users(Set<UUID>)`, constant `USERS = "users"`.
  - `enum NotificationChannel { IN_APP("in_app"), EMAIL("email") }` with `dbValue()` and `static fromDb(String)` (IllegalArgumentException when unknown).
  - `record NotificationRequest(String type, String templateKey, Set<NotificationChannel> channels, Audience audience, Map<String,String> data, Instant scheduledAt, String idempotencyKey, UUID createdBy)`.
  - `record NotificationAck(UUID id, String status, Instant createdAt, boolean duplicate)`.
  - `final class NotificationStatus` constants `ACCEPTED, QUEUED, COMPLETED, PARTIALLY_FAILED, FAILED, CANCELLED` (strings, lowercase snake).
  - `final class DeliveryStatus` constants `PENDING, SENT, FAILED, SKIPPED` and skip reasons from Global Constraints (`SKIP_OPTED_OUT`, `SKIP_NO_TEMPLATE`, `SKIP_EMAIL_NOT_CONFIGURED`, `SKIP_RECIPIENT_UNRESOLVED`, `SKIP_CANCELLED`).
  - `TemplateRenderer.render(String text, Map<String,String> data): String` (missing value → empty string) and `TemplateRenderer.placeholders(String text): Set<String>`, token regex `\{\{\s*([a-zA-Z][a-zA-Z0-9]*)\s*}}`.

- [ ] **Step 1:** Port MeowGo `TemplateRendererTest`; add `NotificationChannel.fromDb` unknown-value test and `Audience.users` immutability test. **Step 2:** `mvn -q test -Dtest=TemplateRendererTest` in a rendered project; expected FAIL. **Step 3:** Write the classes. **Step 4:** Re-run; expected PASS.

### Task 4: Template and preference persistence (JPA)

**Files:** `notification/entity/NotificationTemplate.java`, `notification/entity/NotificationPreference.java`, `notification/repository/NotificationTemplateRepository.java`, `notification/repository/NotificationPreferenceRepository.java`; entity-mapping check test `notification/entity/NotificationEntitiesTest.java` (annotation-level, no DB)

**Interfaces:**
- Consumes: `BaseEntity` from `common/entity`.
- Produces: `NotificationTemplate` (`templateKey, channel, locale, subject, body, templateVersion, active`; getters used by processor); `NotificationPreference` (`recipientId`, `emailEnabled` default true, builder); repositories: `findByTemplateKeyAndActiveTrue(String)`, `findByTemplateKeyAndChannelAndLocaleAndActiveTrue(String,String,String)`, `findByRecipientId(UUID)`, `deleteByRecipientId(UUID)`.

- [ ] **Step 1:** Test the entities' table/column annotations by reflection (`@Table(name=...)`, `@Column` names match the migration), and the builder default `emailEnabled == true`. **Step 2:** run; FAIL. **Step 3:** Implement following the `Example` entity/repository style and MeowGo's entities. **Step 4:** run; PASS; `mvn -q test-compile`.

### Task 5: `NotificationQueries` (outbox SQL)

**Files:** `notification/NotificationQueries.java`; CI-only test `src/test/java/{{ package_path }}/notification/NotificationQueriesIT.java` (Testcontainers Postgres, mirroring `ExampleRepositoryTest`'s setup)

**Interfaces:**
- Consumes: migration tables.
- Produces (port of MeowGo, minus fan-out/`all`/push): `insertNotification(type, templateKey, channels, audienceType, data, status, scheduledAt, idempotencyKey, createdBy) -> Optional<Inserted>`; `record Inserted(UUID id, Instant createdAt)`; `findByIdempotencyKey(String) -> Optional<Existing>`; `record Existing(UUID id, String status, Instant createdAt)`; `insertDeliveries(UUID notificationId, Collection<UUID> recipients, List<String> channels, Instant scheduledAt)`; `promoteScheduled()`; `claimDue(int batchSize, int leaseSeconds) -> List<DeliveryJob>`; `record DeliveryJob(UUID id, UUID notificationId, UUID recipientId, String channel, int attemptCount)`; `findNotification(UUID) -> Optional<NotificationInfo>`; `record NotificationInfo(String type, String templateKey, String status, Map<String,String> data)`; `markSent(UUID id, String providerMessageId)`, `markInAppSent(UUID id, String title, String body)`, `markSkipped(UUID id, String reason)`, `markFailed(UUID id, int attempts, String error)`, `scheduleRetry(UUID id, int attempts, int delaySeconds, String error)`, `rollUp()`, `inbox(UUID recipient, int limit, long offset) -> List<InboxRow>`, `inboxCount(UUID)`, `unreadCount(UUID)`, `markRead(UUID delivery, UUID recipient) -> boolean`, `markAllRead(UUID)`, `dismiss(UUID delivery, UUID recipient) -> boolean`, `deleteDeliveriesOf(UUID recipient)`. Read MeowGo's `NotificationQueries` first and list in the file header which methods were intentionally dropped.

- [ ] **Step 1:** Write `NotificationQueriesIT` (compile-only locally): idempotent insert returns empty second time; `claimDue` returns each due row once under two concurrent callers and re-claims after lease expiry; `scheduleRetry` pushes `next_retry_at`; `rollUp` produces `completed`/`partially_failed`/`failed`; inbox paging newest-first, excludes dismissed, `markRead` returns false for another recipient's delivery.
- [ ] **Step 2:** Implement the class. **Step 3:** `mvn -q test-compile` on a rendered project (the IT cannot run locally without Docker; say so in the task report). Expected: compiles. **Step 4:** Add the IT path to `minimal` exclusions (covered by the `notification/*` test glob).

### Task 6: `NotificationService.enqueue`

**Files:** `notification/NotificationService.java`, `notification/NotificationServiceImpl.java` (enqueue + helpers), test `NotificationServiceImplTest.java`

**Interfaces:**
- Consumes: Tasks 3–5 types; `NotificationQueries` mocked in tests.
- Produces: `interface NotificationService { NotificationAck enqueue(NotificationRequest); ... }` (read-side methods added in Task 7); `NotificationServiceImpl.MAX_EXPLICIT_RECIPIENTS = 500`; class annotated `@Service @Transactional(readOnly = true)` with `enqueue` `@Transactional`.

- [ ] **Step 1:** Tests (Mockito): rejects empty channels; rejects 0 and 501 recipients; rejects a channel with no active template (message names key and channel); rejects missing placeholders (message lists the names, sorted); duplicate key returns the original ack with `duplicate=true` and writes no deliveries; immediate explicit audience → status `queued` and deliveries inserted with the sorted channel list; future `scheduledAt` → `accepted`; logs `notification.accepted` without data values.
- [ ] **Step 2:** Run `mvn -q test -Dtest=NotificationServiceImplTest`; FAIL. **Step 3:** Implement (port MeowGo `enqueue`/`validate`, remove `all`-audience branches). **Step 4:** PASS.

### Task 7: Inbox, preferences and purge methods

**Files:** modify `NotificationService`/`Impl`; create `notification/dto/InboxItemResponse.java`, `PreferencesResponse.java`, `UpdatePreferencesRequest.java`; extend `NotificationServiceImplTest`

**Interfaces:**
- Produces: `PageResponse<InboxItemResponse> inbox(UUID recipient, int page, int size)`; `long unreadCount(UUID)`; `void markRead(UUID recipient, UUID deliveryId)` and `deleteNotification(UUID recipient, UUID deliveryId)` throwing `ResourceNotFoundException` when `queries` returns false; `void markAllRead(UUID)`; `PreferencesResponse getPreferences(UUID)` (defaults `emailEnabled=true`); `PreferencesResponse updatePreferences(UUID, UpdatePreferencesRequest)` (null fields untouched); `void purgeRecipient(UUID)`. DTO records: `InboxItemResponse(UUID id, UUID notificationId, String type, String title, String body, Instant createdAt, boolean read)`, `PreferencesResponse(boolean emailEnabled)`, `UpdatePreferencesRequest(Boolean emailEnabled)`.

- [ ] **Step 1:** Tests: another recipient's delivery → `ResourceNotFoundException` (mark read and dismiss); preferences default and partial update; inbox maps rows and uses `PaginationUtils`; purge calls all deletes. **Step 2:** run; FAIL. **Step 3:** implement (reuse the existing `PaginationUtils`/`PageResponse`). **Step 4:** PASS.

### Task 8: Channel senders and extension interfaces

**Files:** `notification/ChannelSender.java`, `InAppSender.java`, `EmailSender.java`, `Recipient.java`, `RecipientDirectory.java`, `DefaultRecipientDirectory.java`, `CurrentRecipientProvider.java`, `DefaultCurrentRecipientProvider.java`, `config/MailConfig.java`; tests `EmailSenderTest.java`, `InAppSenderTest.java`, `DefaultProvidersTest.java`, `config/MailConfigTest.java`

**Interfaces:**
- Produces:
  - `interface ChannelSender { NotificationChannel channel(); SendOutcome send(SendRequest request); }` with `record SendRequest(UUID deliveryId, UUID recipientId, Recipient recipient, String title, String body)` and `record SendOutcome(Result result, String providerMessageId)`, `enum Result { SENT, NOT_CONFIGURED, FAILED }` (FAILED = retryable; senders never throw).
  - `record Recipient(String email, String locale)`; `interface RecipientDirectory { Optional<Recipient> find(UUID recipientId); }`; `@Bean @ConditionalOnMissingBean DefaultRecipientDirectory` returning empty.
  - `interface CurrentRecipientProvider { Optional<UUID> currentRecipientId(); }`; default `@ConditionalOnMissingBean` bean returns empty.
  - `InAppSender` is a marker sender: `send` returns `SENT` (the processor writes the rendered in-app row via `markInAppSent`; keep the in-app path in the processor, `InAppSender` documents it and satisfies the extension contract — if this proves redundant when implementing Task 9, drop `InAppSender` and say so in the report).
  - `EmailSender(ObjectProvider<JavaMailSender>, @Value("${app.mail.from:}") String)`: no sender bean → `NOT_CONFIGURED`; `MailException` → `FAILED`; never logs address/body.
  - `MailConfig`: creates a `JavaMailSender` only when `app.mail.host` is non-blank (`@ConditionalOnExpression`/`@ConditionalOnProperty`), from the `app.mail.*` keys.

- [ ] **Step 1:** Tests: email not configured → `NOT_CONFIGURED`; sends `SimpleMailMessage` with from/to/subject/text when configured; `MailException` → `FAILED`; default directory returns empty; default provider returns empty; `MailConfig` yields no bean for blank host and a configured bean for a host. **Step 2:** run; FAIL. **Step 3:** implement (port MeowGo `EmailSender`/`MailConfig`). **Step 4:** PASS.

### Task 9: `DeliveryProcessor`

**Files:** `notification/DeliveryProcessor.java`, test `DeliveryProcessorTest.java`

**Interfaces:**
- Consumes: `NotificationQueries`, `NotificationTemplateRepository`, `NotificationPreferenceRepository`, `RecipientDirectory`, `List<ChannelSender>`, `@Value("${app.notifications.max-attempts:5}") int maxAttempts`, `@Value("${app.notifications.default-locale:en}") String defaultLocale`.
- Produces: `void process(NotificationQueries.DeliveryJob job)` (never throws); backoff constants `{60, 300, 1800, 7200}`.

- [ ] **Step 1:** Tests (Mockito): cancelled notification → `skipped/cancelled`; `EMAIL` + preference disabled → `skipped/opted_out`; no template for recipient locale falls back to default locale, none at all → `skipped/no_template`; in-app → `markInAppSent` with rendered title/body, no directory lookup; email with empty directory → `skipped/recipient_unresolved`; email `NOT_CONFIGURED` → `skipped/email_not_configured`; email `FAILED` on attempt 1 → `scheduleRetry(…, 1, 60, …)`, attempt 4 → delay 7200, attempt reaching `maxAttempts` → `markFailed`; error text truncated to 500 chars; an unexpected `RuntimeException` is caught, logged as `notification.delivery.failed` without address/body, and routed to retry; if recording the failure also throws, `process` still returns.
- [ ] **Step 2:** run `mvn -q test -Dtest=DeliveryProcessorTest`; FAIL. **Step 3:** implement (port MeowGo, drop push branch; sender lookup by `channel()` map). **Step 4:** PASS.

### Task 10: `DeliveryWorker`

**Files:** `notification/DeliveryWorker.java`, test `DeliveryWorkerTest.java`

**Interfaces:**
- Consumes: `JobContext.run(String, Runnable)` (observability plan), `NotificationQueries`, `DeliveryProcessor`.
- Produces: `@Component DeliveryWorker` with `@Scheduled(fixedDelayString = "${app.notifications.worker-delay-ms:3000}") void tick()` running steps `promoteScheduled`, `processDue`, `rollUp`, each isolated; `void processDue()` (package-private); batch size and lease from config.

- [ ] **Step 1:** Tests: a step throwing does not stop the others (verify later steps still invoked); `tick` runs inside `JobContext` (MDC `job == "notifications.worker"` observable from within a stubbed step); `processDue` calls `processor.process` for each claimed job and continues if one call throws. **Step 2:** run; FAIL. **Step 3:** implement. **Step 4:** PASS.

### Task 11: Controller

**Files:** `notification/NotificationController.java`, test `NotificationControllerTest.java` (`@WebMvcTest`)

**Interfaces:**
- Consumes: `NotificationService` (Task 7), `CurrentRecipientProvider`, `ApiResponse`, `PageResponse`, `GlobalExceptionHandler`.
- Produces: routes under `/api/v1/notifications`: `GET ""` (page ≥0, size 1–100, default 0/20), `GET /unread-count`, `PATCH /{id}/read`, `POST /read-all`, `DELETE /{id}`, `GET /preferences`, `PUT /preferences`. A missing caller returns `401` with the project's `ApiResponse.error` envelope (add `UnauthorizedException` + handler to `common/exception` if none exists; update `GlobalExceptionHandlerTest` accordingly and keep it single-log with an event name `request.unauthorized`).

- [ ] **Step 1:** Tests: with the default provider (no caller) every route → 401; with a stub provider returning an id → inbox 200 envelope, unread count, mark read 204/200 per project convention (follow `ExampleController`), 404 when service throws `ResourceNotFoundException`, invalid `size=0` / `size=101` → 400; the recipient id passed to the service is always the provider's, never a request parameter.
- [ ] **Step 2:** run `mvn -q test -Dtest=NotificationControllerTest`; FAIL. **Step 3:** implement with OpenAPI `@Tag`/`@Operation` like `ExampleController`. **Step 4:** PASS.

### Task 12: Forge integration, docs and end-to-end

**Files:** `backend/cli.py` (structural paths), `backend/tests/test_generation.py`, `backend/tests/test_template_manifests.py`, `backend/templates/_shared/README.md`, `backend/README.md`, `backend/QUICK_REFERENCE.md`, `backend/CHANGELOG.md`

- [ ] **Step 1:** Add every new always-present notification file (main + test) to `expected_structural_paths` (they are filtered out for `minimal` by the globs) and `002-create-notifications.sql` to the static list.
- [ ] **Step 2:** Extend `test_generation.py`: for `minimal`, assert no `notification/` dir under main or test, no `002-…sql`, no mail starter; for `base-layered`, run `run_tests(..., "TemplateRendererTest,NotificationServiceImplTest,DeliveryProcessorTest,DeliveryWorkerTest,EmailSenderTest,NotificationControllerTest,DefaultProvidersTest,MailConfigTest")` (helper from the observability plan Task 13; if that plan isn't merged yet, implement `run_tests` per its interface).
- [ ] **Step 3:** Template README "Notifications" section: `welcome` usage snippet calling `NotificationService.enqueue`, the three extension points with minimal example implementations, env vars `MAIL_HOST`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_FROM`, `MAIL_STARTTLS`, and the delivery-guarantee note (at-least-once to provider; idempotency prevents duplicate notifications only). Update `backend/` docs.
- [ ] **Step 4:** Run `.venv\Scripts\pytest backend/tests -v` with `mvn` on PATH. Expected: all PASS, including Task 1's manifest glob checks.

---

## Self-Review notes

- Spec coverage: data model (1), config/scheduling (2), types/renderer (3), persistence (4–5), sending (6), read side (7), extension points + senders (8), delivery (9–10), API (11), Forge/docs/tests/CI-only SQL tests (5, 12). Coverage-gate decision from the spec is recorded under Task 5 (IT runs in CI where the gate runs).
- Task 8's `InAppSender` has an explicit keep-or-drop decision point rather than a hidden assumption.
