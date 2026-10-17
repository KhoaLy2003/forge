from core.observability_metrics import KNOWN_METRICS, extract_metric_names


def test_extracts_the_metric_from_a_simple_selector():
    assert extract_metric_names('up{service="demo"} == 0') == {"up"}


def test_extracts_metrics_from_a_nested_histogram_quantile_expression():
    expr = (
        "histogram_quantile(0.95, "
        'sum by (le) (rate(http_server_requests_seconds_bucket{service="demo"}[5m]))) > 1'
    )

    assert extract_metric_names(expr) == {"http_server_requests_seconds_bucket"}


def test_label_names_values_and_grouping_clauses_are_not_metrics():
    expr = (
        'sum by (status, uri) (rate(http_server_requests_seconds_count{service="demo",status=~"5.."}[5m]))'
    )

    assert extract_metric_names(expr) == {"http_server_requests_seconds_count"}


def test_ratio_of_two_metrics_returns_both():
    expr = (
        'hikaricp_connections_active{service="demo"} / hikaricp_connections_max{service="demo"} > 0.9'
    )

    assert extract_metric_names(expr) == {"hikaricp_connections_active", "hikaricp_connections_max"}


def test_ignores_grafana_variables_and_numbers():
    expr = "rate(process_cpu_usage[$__rate_interval]) * 100"

    assert extract_metric_names(expr) == {"process_cpu_usage"}


def test_unknown_metric_is_reported_as_a_metric_name():
    assert extract_metric_names("foo_bar_total > 0") == {"foo_bar_total"}


def test_multiline_expression_with_offset_and_boolean_modifiers():
    expr = """
      sum(rate(http_server_requests_seconds_count[5m] offset 1h))
        > bool
      sum(rate(http_server_requests_seconds_count[5m]))
    """

    assert extract_metric_names(expr) == {"http_server_requests_seconds_count"}


def test_known_metrics_cover_every_metric_the_shipped_alerts_and_dashboard_use():
    for name in (
        "up",
        "http_server_requests_seconds_count",
        "http_server_requests_seconds_sum",
        "http_server_requests_seconds_bucket",
        "jvm_memory_used_bytes",
        "jvm_memory_max_bytes",
        "hikaricp_connections_active",
        "hikaricp_connections_max",
        "process_cpu_usage",
    ):
        assert name in KNOWN_METRICS
