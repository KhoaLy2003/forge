"""Rendered-output checks for the observability parts of the templates (no Maven, no Docker)."""

from pathlib import Path

import yaml


def _read(project: Path, relative: str) -> str:
    return (project / relative).read_text(encoding="utf-8")


def test_base_layered_ci_has_an_observability_config_job(rendered):
    workflow = yaml.safe_load(_read(rendered["base-layered"], ".github/workflows/ci.yml"))

    job = workflow["jobs"]["observability-config"]
    assert job["permissions"] == {"contents": "read"}
    commands = "\n".join(step.get("run", "") for step in job["steps"])
    assert commands.count("--entrypoint promtool") == 2
    assert "check config /etc/prometheus/prometheus.yml" in commands
    assert "check rules /etc/prometheus/alerts.yml" in commands
    assert "docker-compose.observability.yml" in commands
    assert "config -q" in commands


def test_observability_ci_job_uses_no_new_third_party_action(rendered):
    workflow = yaml.safe_load(_read(rendered["base-layered"], ".github/workflows/ci.yml"))

    uses = [step["uses"] for step in workflow["jobs"]["observability-config"]["steps"] if "uses" in step]

    assert len(uses) == 1 and uses[0].startswith("actions/checkout@")
    assert "persist-credentials: false" in _read(rendered["base-layered"], ".github/workflows/ci.yml")


def test_minimal_ci_has_no_observability_job_and_still_parses(rendered):
    workflow = yaml.safe_load(_read(rendered["minimal"], ".github/workflows/ci.yml"))

    assert "observability-config" not in workflow["jobs"]
    assert "build-test" in workflow["jobs"]


def test_minimal_has_logging_baseline_but_no_monitoring_files(rendered):
    minimal = rendered["minimal"]

    assert (minimal / "docs/observability/logging.md").exists()
    assert not (minimal / "docs/observability/runbook.md").exists()
    assert not (minimal / "observability").exists()
    assert not (minimal / "docker-compose.observability.yml").exists()
    assert "micrometer-registry-prometheus" not in _read(minimal, "pom.xml")
    application = _read(minimal, "src/main/resources/application.yml")
    assert "prometheus" not in application and "8081" not in application
    assert "slow-request-ms" in application
    assert "request_id" in application
    assert (minimal / "src/main/java/com/example/demoservice/common/config/RequestLogFilter.java").exists()


def test_base_layered_has_the_monitoring_stack_and_metrics_config(rendered):
    base = rendered["base-layered"]

    assert (base / "docs/observability/runbook.md").exists()
    assert (base / "observability/prometheus/alerts.yml").exists()
    assert "micrometer-registry-prometheus" in _read(base, "pom.xml")
    application = _read(base, "src/main/resources/application.yml")
    assert "include: health,info,prometheus" in application
    assert "8081" in application


def test_prod_profile_enables_structured_ecs_logging_with_the_customizer(rendered):
    for project in rendered.values():
        prod = yaml.safe_load(_read(project, "src/main/resources/application-prod.yml"))

        structured = prod["logging"]["structured"]
        assert structured["format"]["console"] == "ecs"
        assert structured["json"]["stacktrace"]["max-length"] == 4096
        assert structured["json"]["customizer"] == (
            "com.example.demoservice.common.config.SensitiveDataCustomizer"
        )


def test_monitoring_templates_render_literal_template_braces_untouched(rendered):
    dashboard = _read(rendered["base-layered"], "observability/grafana/dashboards/service-overview.json")

    assert "{{status}}" in dashboard
    assert "demo-service" in dashboard
