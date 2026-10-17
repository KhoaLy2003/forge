# Backend Notification Module — Design

Status: draft for review (2026-10-17). Scope: `backend/` (Forge) only.

## Intent

Almost every service eventually needs the same notification plumbing: record "tell this user X" reliably, deliver it by email or in an in-app inbox, retry failures, and let users read and opt out. Forge exists to speed up scaffolding work that repeats across projects, so a generated `base-layered` project should ship that plumbing instead of each project rebuilding it.

The MeowGo server (`meowgo_server_java`, package `notifications`) already implements it and is the **reference to generalize from**, not a spec and not a target. Where MeowGo is tied to its own domain (sightings, "First Finder", its account model, FCM push, `vi`/`en`), the Forge module generalizes or leaves it out.

Decisions fixed by the user:
- Channels: outbox pipeline, **in-app inbox and email (SMTP)**, with a `ChannelSender` interface so other channels (push, SMS) can be added. No push/FCM in the default module.
- Recipients are opaque ids. Email address and locale come from a `RecipientDirectory` interface that the project implements; the default finds nobody.
- Templates live in the database and are seeded with one generic example.
- The inbox REST API ships, and the caller is identified through a `CurrentRecipientProvider` interface whose default yields no caller, so the endpoints answer `401` until the project wires its auth.
- The module belongs to `base-layered` only. `minimal` excludes it (no Liquibase, and the worker SQL is Postgres-specific).
- No new CLI flags or wizard prompts.
- Local development has no Docker; anything that needs Postgres is verified in the generated project's CI.

## Dependencies on other specs

- **Observability spec** (`2026-10-17-observability-design.md`): the worker uses `JobContext` and the stable-event-name convention from it. That spec is implemented first.
- **Entity-modeling spec** (`2026-10-17-entity-modeling-design.md`): both add Liquibase migrations. This module takes `002-create-notifications.sql` (the existing template has `001-create-example-table.sql`). The entity-modeling spec's generated changelogs must be numbered after it (`003` and up); that spec is updated when both are approved. The roadmap's "messaging" mention in item 2 of that spec is not covered here (this module is a database outbox, not a message broker).

## Template placement

Files live in `templates/_shared/` and are removed from `minimal` through its `manifest.py`. Because `minimal` does not use Liquibase, the exclusion is by glob:

```
src/main/java/{{ package_path }}/notification/*
src/test/java/{{ package_path }}/notification/*
src/main/resources/db/changelog/002-create-notifications.sql
```

Shared files that must differ get `{% if use_liquibase %}` blocks (`use_liquibase` already means "not minimal"): `pom.xml` (mail starter), `application.yml` (`app.notifications.*`, `app.mail.*`), the Liquibase master changelog include, and the application class (`@EnableScheduling`). No new `ForgeConfig` property is needed.

## Data model (`002-create-notifications.sql`)

Generalized from MeowGo's `006`/`007`, without push and device tokens:

| Table | Purpose | Differences from MeowGo |
|---|---|---|
| `notification_templates` | `template_key`, `channel` (`in_app`, `email`), `locale`, `subject`, `body`, `template_version`, `active`, standard base columns; unique on (`template_key`, `channel`, `locale`) | `push` removed from the channel check; locale is a free two-letter code, not limited to `vi`/`en` |
| `notifications` | The outbox record: `type`, `template_key`, `channels`, `audience_type`, `data` (JSONB), `status`, `scheduled_at`, `idempotency_key` (partial unique index), `created_by`, `fanout_*` | `audience_type` allows only `users` (no `all`); fan-out columns dropped |
| `deliveries` | One row per notification, recipient and channel: status, `attempt_count`, `next_retry_at`, `last_error`, `skip_reason`, rendered `title`/`body`, `read_at`, `dismissed_at`; unique on (`notification_id`, `recipient_id`, `channel`); indexes for due work and inbox | `recipient_id` has no foreign key (as in MeowGo); `provider_message_id` kept for email; `dismissed_at` included from the start |
| `notification_preferences` | `recipient_id` (unique), `email_enabled` | `push_enabled` and `locale` dropped; locale comes from `RecipientDirectory` |

Seed: one generic `welcome` template for `in_app` and `email` in `en`, with a `{{name}}` placeholder, so a fresh project can send something immediately. Rollback comments are included, as in the existing migrations.

## Components (package `notification`)

**Sending.**
- `NotificationService` / `NotificationServiceImpl`: `enqueue(NotificationRequest)` runs in the caller's transaction (`REQUIRED`) so a notification commits or rolls back with the business change. It validates that every channel has an active template, that template data covers all placeholders, and that the explicit audience has 1 to 500 recipients. An existing idempotency key returns the original acknowledgement with `duplicate=true`. Records `NotificationRequest`, `NotificationAck`, `Audience` (explicit users only), `NotificationChannel` (`IN_APP`, `EMAIL`), `NotificationStatus`, `DeliveryStatus`.
- Read side of the same service: `inbox`, `unreadCount`, `markRead`, `markAllRead`, `deleteNotification` (dismiss), `getPreferences`, `updatePreferences`, `purgeRecipient`.
- `TemplateRenderer`: `{{name}}` placeholders, literal insertion, as in MeowGo.

**Delivery.**
- `DeliveryWorker`: `@Scheduled(fixedDelay)`, one tick runs independent steps (promote scheduled notifications, process due deliveries, roll statuses up), each isolated so one failure does not block the others, wrapped in `JobContext.run("notifications.worker", ...)`. The "fan out audience `all`" step is not generated.
- `DeliveryProcessor`: not transactional (it does network I/O); one single-statement state change per outcome. Retries with backoff (60 s, 5 min, 30 min, 2 h) up to `app.notifications.max-attempts` (5), then `failed`. Skip reasons: `opted_out`, `no_template`, `email_not_configured`, `recipient_unresolved`, `cancelled`. Locale resolution: recipient's locale from `RecipientDirectory`, falling back to `app.notifications.default-locale` (`en`).
- `NotificationQueries`: plain `JdbcTemplate` SQL for the outbox, kept from MeowGo, using `FOR UPDATE SKIP LOCKED` plus a lease so several instances can run safely. JPA is used for templates and preferences only.
- Failures log with stable event names (`notification.delivery.failed`, `notification.delivery.skipped`) and never log recipient addresses or message bodies.

**Extension points** (small interfaces, safe defaults, each documented in the README):

| Interface | Default | Purpose |
|---|---|---|
| `ChannelSender` | `InAppSender`, `EmailSender` (SMTP via `JavaMailSender`; "not configured" is a normal skip, not an error) | Add a channel by registering a bean |
| `RecipientDirectory` | `Optional<Recipient> find(UUID id)` returns empty | Supplies email address and locale; empty means email is skipped with `recipient_unresolved`, in-app still works |
| `CurrentRecipientProvider` | returns empty, so the API answers `401` | Supplies the caller's id from the project's auth |

**REST API** under `/api/v1/notifications`: list inbox (paged, newest first, `size` 1 to 100), unread count, mark one read, mark all read, dismiss one, get and update preferences. No endpoint creates notifications, and no endpoint accepts a recipient id from the client. Responses use the existing `ApiResponse`/`PageResponse` types and OpenAPI annotations.

## Configuration (`application.yml`)

```
app.notifications: worker-delay-ms, batch-size, lease-seconds, max-attempts, default-locale
app.mail: host, port, username, password, from, starttls   # all from env variables, blank = not configured
```

Mail credentials come from environment variables with empty defaults; none are committed. `docker-compose.yml` is not changed.

## Forge-side changes

1. `templates/_shared/` gains the files above; `templates/minimal/manifest.py` gains the three `EXCLUDES` globs.
2. `cli.py`: `EXPECTED_STRUCTURAL_PATHS` / `expected_structural_paths()` list the new always-present files for `base-layered` (filtered by `EXCLUDES` as today).
3. `README.md` of the template: a "Notifications" section with a `welcome` usage snippet, the three extension points, and the email environment variables.
4. `backend/` README, `QUICK_REFERENCE` and `CHANGELOG` describe the module.
5. No change to `config_schema.py`, the wizard or CLI flags.

## Testing

**Docker-free (local and Forge's own suite):**
- Generated unit tests: `NotificationServiceImpl` (validation, idempotency, inbox, preferences), `DeliveryProcessor` (each skip reason, retry/backoff, failure after max attempts), `DeliveryWorker` (step isolation), `TemplateRenderer`, `EmailSender`/`InAppSender`, `NotificationController` with `@WebMvcTest` (401 with the default provider; behavior with a stub provider). `NotificationQueries` is mocked in these.
- `tests/test_generation.py`: renders both templates; asserts `minimal` has no `notification/` files, no mail starter and no `002` migration; asserts `base-layered` compiles (`test-compile`) and its Docker-free notification tests pass.

**CI-only (generated project, Docker available):** Testcontainers tests for `NotificationQueries` against real Postgres (claim with `SKIP LOCKED` and lease expiry, idempotency, roll-up, inbox paging). These sit beside the existing `ExampleRepositoryTest` and are excluded from `minimal`.

**Coverage gate.** The template's 90% JaCoCo line gate runs in the generated project's CI (`mvn verify`), where the Testcontainers tests also run, so `NotificationQueries` is covered there and the gate is unchanged. Locally `mvn verify` already cannot pass without Docker (existing repository test), so this adds no new local limitation.

## Non-goals

- Push/FCM, device tokens and their endpoints; SMS. (Extension point only.)
- An admin send/cancel/statistics API, scheduled-send UI, "all users" audience and fan-out, UAT handling.
- A users or auth model. Identifying callers and resolving recipient details is the project's job through the two interfaces.
- A message broker (Kafka, RabbitMQ) or exactly-once delivery guarantees. The outbox gives at-least-once delivery to the provider, and idempotency keys prevent duplicate notifications, not duplicate provider sends.
- HTML emails and attachments (plain text only, as in MeowGo).
- Changing MeowGo or adding the module to existing projects.
- Anything for `frontend/` (Forge Web); an inbox UI would be a separate spec.

## Risks and open points for the plan

- `{{ }}` in seed templates collides with Jinja delimiters in the rendered migration and in any template file containing `{{name}}`; those files need `{% raw %}` blocks.
- Spring Boot 4 package and artifact names for the mail starter, `@Scheduled`, `JdbcTemplate` autoconfiguration and `@WebMvcTest` are confirmed against the version in the template's `pom.xml` during planning (MeowGo already builds on Boot 4.1).
- With scheduling enabled, the worker starts on every application start, including tests that load the full context; the plan checks that existing tests are unaffected and that `app.notifications.worker-delay-ms` can disable it for them.
- Migration numbering with the entity-modeling spec (see Dependencies) must be settled before either is planned.
- The `NotificationQueries` SQL is ported from MeowGo with the `all`-audience and push parts removed; the plan lists exactly which methods are dropped so no dead code is generated.
