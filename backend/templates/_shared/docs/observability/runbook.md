# Runbook — {{ project_name }}

Short guide for investigating {{ project_name }}. It covers where telemetry lives, how to look into
the common failures, and who to call. See [`logging.md`](logging.md) for the log format.

## Ownership

| | |
|---|---|
| Owning team | _fill in_ |
| On-call / escalation | _fill in_ |
| Access to production logs and dashboards | _how to request it; who approves_ |

## Where to look

| Signal | Where |
|---|---|
| Logs | stdout of the service, collected by your platform. Locally: Grafana → Explore → Loki |
| Metrics | `GET :8081/actuator/prometheus`, scraped by Prometheus. Locally: http://localhost:9090 |
| Dashboard | Grafana → "{{ artifact_id }} - service overview" (http://localhost:3000 locally) |
| Alerts | `observability/prometheus/alerts.yml` (Prometheus → Alerts) |
| Health | `GET :8081/actuator/health` (liveness and readiness under `/actuator/health/liveness` and `/readiness`) |

The management port (8081) exposes operational data. Publish it only to the monitoring network.

## First steps for any incident

1. Establish the **time window** and the **user impact** (who, what, since when).
2. Open the dashboard: is traffic normal, are errors or latency up, is anything saturated?
3. Check whether a **deployment or configuration change** happened just before the symptom began.
4. Search the logs in the same window: `service.name:{{ artifact_id }}` and `log.level:ERROR`.
   Group by `event.name`. To follow one request, filter by its `request_id` (the value of the
   `X-Correlation-ID` response header).
5. Decide whether this is an **application failure** or a **telemetry failure** (see below).

## Alerts

Thresholds are starting points, not universal defaults. Tune them to your traffic, baseline and
SLOs. Ratio-based alerts produce no data when there is no traffic; for low-traffic services use
absolute counts or longer windows.

### ServiceDown
Prometheus cannot scrape the service for 2 minutes. Check that the process is running, look for
startup errors in the logs, and confirm port 8081 is reachable from Prometheus.

### HighErrorRatio
More than 2% of requests returned 5xx for 5 minutes. Filter logs for `log.level:ERROR`, group by
`event.name`, check the latest deployment and database health.

### HighLatencyP95
p95 latency above 1 second for 10 minutes. Compare with traffic and pool saturation, and look for
`http.request.completed` events at `WARN` (slower than `app.logging.slow-request-ms`).

### JvmHeapSaturation
Heap above 90% for 10 minutes. Check for a traffic or deployment change and for a heap that grows
steadily (a leak).

### DbPoolSaturation
Connection pool above 90% for 5 minutes. Look for slow queries or long transactions and check
database health.

## Application failure or telemetry failure?

- **Metrics missing but the service answers requests:** Prometheus cannot reach port 8081, or the
  management port is not published. Check `up{service="{{ artifact_id }}"}` and the target page.
- **Logs missing but the service answers requests:** the collector or log backend is down, or
  stdout is not being collected. Check the collector's own health before assuming the app is
  silent.
- **Both missing and requests fail:** treat it as an application outage.

## Retention and storage

Local defaults only: Prometheus 15 days, Loki 7 days. Agree production retention per telemetry
class (logs, metrics, audit events) and record it in [`logging.md`](logging.md#retention).

## If you find a secret or personal data in the logs

Do not paste it into chat or tickets. Report it to the owning team and the security contact, find
the code that logged it (search by `event.name` or the message), and fix it. Ask the platform team
to purge the affected log range if policy requires.
