# Logging

How {{ project_name }} writes logs, and the rules for adding new log lines. It implements Phase 1
(logging foundation) of the cross-project observability standard.

## Where logs go

- Logs are written to **standard output only**. There is no log file, so there is nothing to
  rotate and no disk to fill (standard OBS-06). The platform (container runtime, Kubernetes,
  collector) is responsible for collecting stdout.
- `prod` profile: one JSON object per line in the Elastic Common Schema (ECS) field layout, with
  UTC timestamps and stack traces cut at 4096 characters.
- `dev` profile: a readable text line that includes `request_id`.

## Field mapping

The standard defines conceptual fields; this table is the documented mapping to what is emitted.

| Standard field | Emitted as | Notes |
|---|---|---|
| `timestamp` | `@timestamp` | UTC, ISO-8601 |
| `severity` | `log.level` | `ERROR`, `WARN`, `INFO`, `DEBUG`, `TRACE` |
| `message` | `message` | must not contain secrets or personal data |
| `event.name` | `event.name` | stable identifier, see below |
| `service.name` | `service.name` | from `spring.application.name` (`{{ artifact_id }}`) |
| `service.version` | `service.version` | the Maven project version |
| `deployment.environment.name` | `service.environment` | from `DEPLOYMENT_ENVIRONMENT`, default `production` |
| `request_id` | `request_id` | from the MDC; also `job` for scheduled work |
| `http.request.method` | `http.request.method` | request log only |
| `http.route` | `http.route` | route **template** (`/api/v1/examples/{id}`) or `UNMATCHED`, never the raw path |
| `http.response.status_code` | `http.response.status_code` | request log only |
| `duration_ms` | `duration_ms` | request log only |
| `error.type` | `error.type` | exception class name for handled client errors |
| `exception.stacktrace` | `error.stack_trace` | bounded to 4096 characters |

## Request correlation

`CorrelationIdFilter` reads `X-Correlation-ID`. The header is untrusted input: it is reused only if
it is 1-64 characters of `A-Za-z0-9._-`; otherwise a UUID is generated. The value is stored in the
MDC as `request_id` and echoed on the response. Scheduled work gets the same treatment from
`JobContext.run("job.name", () -> ...)`, which sets `job` and a fresh `request_id` for the run.

`request_id` is an application-level handle. It is **not** a distributed trace id; tracing
(W3C Trace Context) is not part of this project's baseline.

## One request log per request

`RequestLogFilter` writes a single `http.request.completed` event per request: `ERROR` for 5xx or an
escaped exception, `WARN` at or above `app.logging.slow-request-ms` (default 2000), `DEBUG` for the
health probe, `INFO` otherwise. It never reads query strings, headers, cookies or bodies.

## Rules for new log lines

1. Log a failure **once**, at the layer that has the context to explain it. Do not log and rethrow.
2. Give important events a stable `event.name` of the form `domain.entity.action[.outcome]`, for
   example `order.create.failed`. Never put ids, emails or other values in the name.
3. Pass variable data as key-values (`log.atInfo().addKeyValue("order_id", id).log("...")`), not by
   concatenating it into the message.
4. Never log passwords, tokens, API keys, cookies, `Authorization` headers, full request or response
   bodies, query strings, or unnecessary personal data. `SensitiveDataCustomizer` masks values of
   members named like `password`, `secret`, `token`, `authorization`, `cookie` and `api_key`, but it
   is a safety net: it does **not** scan free-text messages.
5. Do not use `ERROR` for expected outcomes such as validation failures or `404`.
6. Do not log inside tight loops or per-item in bulk operations.

## Severity

| Level | Use it for | Do not use it for |
|---|---|---|
| `ERROR` | an operation failed unexpectedly and needs investigation | expected validation outcomes |
| `WARN` | a recoverable or unusual condition worth attention | normal branches |
| `INFO` | important lifecycle and business milestones | every method call |
| `DEBUG` | detail for troubleshooting | always-on production diagnostics |

## Retention

Fill this in for your environment; the standard requires retention to be documented per class.

| Telemetry | Environment | Retention | Owner |
|---|---|---|---|
| Application logs | production | _decide (for example 30 days)_ | |
| Application logs | development | _decide_ | |
| Security / audit events | production | _decide; may need a separate protected store_ | |

## Finding logs for an incident

1. Establish the time window and the symptom.
2. Search your log platform for `service.name:{{ artifact_id }}` in that window.
3. Filter by `log.level:ERROR`, or by `request_id` from a user report or the `X-Correlation-ID`
   response header, to follow one request across lines.
4. Use `event.name` to group related failures.
