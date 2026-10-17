"""Registry of the Prometheus metrics a generated service is known to expose, plus a best-effort
PromQL scanner, so alert rules and dashboards cannot drift from what the application emits."""

import re

# Metrics exposed at /actuator/prometheus by the generated project's default instrumentation
# (Spring MVC, JVM, HikariCP, process) plus Prometheus' own synthetic `up` series.
KNOWN_METRICS: frozenset[str] = frozenset(
    {
        "up",
        "http_server_requests_seconds_count",
        "http_server_requests_seconds_sum",
        "http_server_requests_seconds_bucket",
        "http_server_requests_seconds_max",
        "jvm_memory_used_bytes",
        "jvm_memory_max_bytes",
        "jvm_memory_committed_bytes",
        "jvm_gc_pause_seconds_count",
        "jvm_gc_pause_seconds_sum",
        "jvm_gc_pause_seconds_max",
        "jvm_threads_live_threads",
        "jvm_threads_peak_threads",
        "hikaricp_connections_active",
        "hikaricp_connections_idle",
        "hikaricp_connections_max",
        "hikaricp_connections_pending",
        "hikaricp_connections_timeout_total",
        "process_cpu_usage",
        "process_uptime_seconds",
        "system_cpu_usage",
    }
)

# PromQL functions, aggregations, operators and keywords that look like identifiers but are not
# metric names.
PROMQL_WORDS: frozenset[str] = frozenset(
    {
        "sum", "min", "max", "avg", "count", "group", "stddev", "stdvar", "topk", "bottomk",
        "quantile", "count_values", "rate", "irate", "increase", "delta", "idelta", "deriv",
        "predict_linear", "histogram_quantile", "histogram_count", "histogram_sum",
        "avg_over_time", "min_over_time", "max_over_time", "sum_over_time", "count_over_time",
        "quantile_over_time", "last_over_time", "present_over_time", "absent", "absent_over_time",
        "abs", "ceil", "floor", "round", "clamp", "clamp_min", "clamp_max", "exp", "ln", "log2",
        "log10", "sqrt", "sgn", "sort", "sort_desc", "time", "timestamp", "vector", "scalar",
        "label_replace", "label_join", "changes", "resets", "day_of_week", "day_of_month",
        "hour", "minute", "month", "year",
        "by", "without", "on", "ignoring", "group_left", "group_right", "bool", "offset",
        "and", "or", "unless", "inf", "nan", "start", "end",
    }
)

_STRING = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`[^`]*`')
_LABEL_MATCHERS = re.compile(r"\{[^{}]*\}")
_RANGE = re.compile(r"\[[^\]]*\]")
_GROUPING = re.compile(r"\b(?:by|without|on|ignoring|group_left|group_right)\s*\([^)]*\)")
_OFFSET = re.compile(r"\boffset\s+-?(?:\d+[smhdwy])+")
_VARIABLE = re.compile(r"\$\{?\w+\}?")
_IDENTIFIER = re.compile(r"[a-zA-Z_:][a-zA-Z0-9_:]*")


def extract_metric_names(expr: str) -> set[str]:
    """Return the metric names referenced by a PromQL expression (best effort).

    String literals, label matchers, range selectors, grouping clauses, Grafana variables, numbers,
    functions and keywords are discarded; whatever identifiers remain are metric names. This is a
    token scan, not a PromQL parser, so exotic expressions may need an entry in PROMQL_WORDS.
    """
    text = _STRING.sub('""', expr)
    text = _OFFSET.sub(" ", text)
    text = _VARIABLE.sub(" ", text)
    text = _LABEL_MATCHERS.sub(" ", text)
    text = _RANGE.sub(" ", text)
    text = _GROUPING.sub(" ", text)
    return {
        match.group(0)
        for match in _IDENTIFIER.finditer(text)
        if match.group(0) not in PROMQL_WORDS
    }
