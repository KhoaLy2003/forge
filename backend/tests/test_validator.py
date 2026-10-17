from pathlib import Path

import pytest

from core.validator import ValidationResult, check_structure, run_compile

MINIMAL_POM = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>minimal</artifactId>
  <version>0.0.1-SNAPSHOT</version>
  <properties>
    <maven.compiler.source>21</maven.compiler.source>
    <maven.compiler.target>21</maven.compiler.target>
  </properties>
</project>
"""

MINIMAL_JAVA = """package com.example;

public class Hello {
    public static void main(String[] args) {
        System.out.println("hi");
    }
}
"""


def test_check_structure_passes_when_all_expected_files_exist(tmp_path):
    (tmp_path / "pom.xml").write_text("x", encoding="utf-8")
    result = check_structure(tmp_path, [Path("pom.xml")])
    assert result == ValidationResult(True, "Structural check passed")


def test_check_structure_fails_and_lists_missing_files(tmp_path):
    result = check_structure(tmp_path, [Path("pom.xml"), Path("docker-compose.yml")])
    assert result.passed is False
    assert "pom.xml" in result.details
    assert "docker-compose.yml" in result.details


def test_run_compile_passes_for_a_valid_minimal_maven_project(tmp_path):
    (tmp_path / "pom.xml").write_text(MINIMAL_POM, encoding="utf-8")
    java_dir = tmp_path / "src" / "main" / "java" / "com" / "example"
    java_dir.mkdir(parents=True)
    (java_dir / "Hello.java").write_text(MINIMAL_JAVA, encoding="utf-8")

    result = run_compile(tmp_path)

    assert result.passed is True, result.details


def test_run_compile_fails_for_broken_java_source(tmp_path):
    (tmp_path / "pom.xml").write_text(MINIMAL_POM, encoding="utf-8")
    java_dir = tmp_path / "src" / "main" / "java" / "com" / "example"
    java_dir.mkdir(parents=True)
    (java_dir / "Hello.java").write_text("this is not valid java", encoding="utf-8")

    result = run_compile(tmp_path)

    assert result.passed is False
    assert result.details


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


# --- check_observability ---------------------------------------------------------------------

import json  # noqa: E402

import yaml  # noqa: E402

from core.config_schema import ForgeConfig  # noqa: E402
from core.renderer import render_tree  # noqa: E402
from core.templates import SHARED_DIR, discover_templates  # noqa: E402
from core.validator import check_observability  # noqa: E402

VALID_ALERT = {
    "alert": "ServiceDown",
    "expr": 'up{service="demo"} == 0',
    "for": "2m",
    "labels": {"severity": "critical", "team": "demo"},
    "annotations": {
        "summary": "s",
        "impact": "i",
        "first_checks": "f",
        "runbook": "docs/observability/runbook.md#servicedown",
    },
}


def _write_valid_observability_tree(root: Path, alert: dict | None = None, dashboard: dict | None = None):
    files = {
        "docker-compose.observability.yml": {"services": {}},
        "observability/prometheus/prometheus.yml": {"global": {}},
        "observability/prometheus/alerts.yml": {"groups": [{"name": "g", "rules": [alert or VALID_ALERT]}]},
        "observability/grafana/provisioning/datasources/datasources.yml": {"apiVersion": 1},
        "observability/grafana/provisioning/dashboards/dashboards.yml": {"apiVersion": 1},
        "observability/loki/loki-config.yml": {"auth_enabled": False},
    }
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(content), encoding="utf-8")
    default_dashboard = {
        "panels": [
            {
                "datasource": {"type": "prometheus", "uid": "prometheus"},
                "targets": [{"expr": "up", "datasource": {"type": "prometheus", "uid": "prometheus"}}],
            }
        ]
    }
    dash = root / "observability/grafana/dashboards/service-overview.json"
    dash.parent.mkdir(parents=True, exist_ok=True)
    dash.write_text(json.dumps(dashboard or default_dashboard), encoding="utf-8")
    alloy = root / "observability/alloy/config.alloy"
    alloy.parent.mkdir(parents=True, exist_ok=True)
    alloy.write_text("// alloy\n", encoding="utf-8")
    runbook = root / "docs/observability/runbook.md"
    runbook.parent.mkdir(parents=True, exist_ok=True)
    runbook.write_text("# Runbook\n", encoding="utf-8")


def test_check_observability_passes_immediately_when_monitoring_is_not_included(tmp_path):
    result = check_observability(tmp_path, include_monitoring=False)

    assert result.passed is True


def test_check_observability_passes_for_a_valid_tree(tmp_path):
    _write_valid_observability_tree(tmp_path)

    result = check_observability(tmp_path, include_monitoring=True)

    assert result.passed is True, result.details


def test_check_observability_fails_and_lists_missing_files(tmp_path):
    _write_valid_observability_tree(tmp_path)
    (tmp_path / "observability/loki/loki-config.yml").unlink()

    result = check_observability(tmp_path, include_monitoring=True)

    assert result.passed is False
    assert "observability/loki/loki-config.yml" in result.details


def test_check_observability_fails_on_malformed_yaml(tmp_path):
    _write_valid_observability_tree(tmp_path)
    (tmp_path / "observability/prometheus/prometheus.yml").write_text("a: [unclosed", encoding="utf-8")

    result = check_observability(tmp_path, include_monitoring=True)

    assert result.passed is False
    assert "prometheus.yml" in result.details


def test_check_observability_fails_on_malformed_dashboard_json(tmp_path):
    _write_valid_observability_tree(tmp_path)
    (tmp_path / "observability/grafana/dashboards/service-overview.json").write_text("{nope", encoding="utf-8")

    result = check_observability(tmp_path, include_monitoring=True)

    assert result.passed is False
    assert "service-overview.json" in result.details


def test_check_observability_names_an_unknown_metric_in_an_alert(tmp_path):
    alert = {**VALID_ALERT, "expr": "foo_bar_total > 0"}
    _write_valid_observability_tree(tmp_path, alert=alert)

    result = check_observability(tmp_path, include_monitoring=True)

    assert result.passed is False
    assert "foo_bar_total" in result.details
    assert "ServiceDown" in result.details


def test_check_observability_names_an_unknown_metric_in_a_dashboard_query(tmp_path):
    dashboard = {
        "panels": [
            {
                "title": "Broken",
                "datasource": {"type": "prometheus", "uid": "prometheus"},
                "targets": [{"expr": "made_up_metric_seconds_count"}],
            }
        ]
    }
    _write_valid_observability_tree(tmp_path, dashboard=dashboard)

    result = check_observability(tmp_path, include_monitoring=True)

    assert result.passed is False
    assert "made_up_metric_seconds_count" in result.details


def test_check_observability_ignores_loki_queries_in_the_dashboard(tmp_path):
    dashboard = {
        "panels": [
            {
                "datasource": {"type": "loki", "uid": "loki"},
                "targets": [{"expr": '{service=~".+"} | json | log_level="ERROR"'}],
            }
        ]
    }
    _write_valid_observability_tree(tmp_path, dashboard=dashboard)

    result = check_observability(tmp_path, include_monitoring=True)

    assert result.passed is True, result.details


@pytest.mark.parametrize("missing", ["severity", "team"])
def test_check_observability_requires_severity_and_team_labels_on_alerts(tmp_path, missing):
    labels = {k: v for k, v in VALID_ALERT["labels"].items() if k != missing}
    _write_valid_observability_tree(tmp_path, alert={**VALID_ALERT, "labels": labels})

    result = check_observability(tmp_path, include_monitoring=True)

    assert result.passed is False
    assert missing in result.details


@pytest.mark.parametrize("missing", ["summary", "impact", "first_checks", "runbook"])
def test_check_observability_requires_response_annotations_on_alerts(tmp_path, missing):
    annotations = {k: v for k, v in VALID_ALERT["annotations"].items() if k != missing}
    _write_valid_observability_tree(tmp_path, alert={**VALID_ALERT, "annotations": annotations})

    result = check_observability(tmp_path, include_monitoring=True)

    assert result.passed is False
    assert missing in result.details


def test_check_observability_passes_on_a_freshly_rendered_base_layered_project(tmp_path):
    config = ForgeConfig(
        project_name="demo-service",
        target_path=tmp_path,
        group_id="com.example",
        artifact_id="demo-service",
        template="base-layered",
    )
    render_tree(
        SHARED_DIR,
        config.target_dir,
        config.template_context(),
        excluded=discover_templates()["base-layered"],
    )

    result = check_observability(config.target_dir, include_monitoring=True)

    assert result.passed is True, result.details


# --- run_tests -------------------------------------------------------------------------------

import subprocess  # noqa: E402

from core import validator  # noqa: E402
from core.validator import run_tests  # noqa: E402


class _Completed:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


def test_run_tests_invokes_mvn_with_the_test_filter_in_the_project_dir(tmp_path, monkeypatch):
    seen = {}

    def fake_run(cmd, **kwargs):
        seen["cmd"], seen["kwargs"] = cmd, kwargs
        return _Completed(0)

    monkeypatch.setattr(validator.subprocess, "run", fake_run)

    result = run_tests(tmp_path, "FooTest,BarTest")

    assert result.passed is True
    assert seen["cmd"][1:] == ["-q", "test", "-Dtest=FooTest,BarTest"]
    assert seen["kwargs"]["cwd"] == tmp_path
    assert seen["kwargs"]["timeout"] == 300


def test_run_tests_reports_failure_with_maven_output(tmp_path, monkeypatch):
    monkeypatch.setattr(
        validator.subprocess, "run", lambda *a, **k: _Completed(1, "out text", "err text")
    )

    result = run_tests(tmp_path, "FooTest")

    assert result.passed is False
    assert "FooTest" in result.message
    assert "out text" in result.details and "err text" in result.details


def test_run_tests_reports_missing_mvn(tmp_path, monkeypatch):
    def missing(*args, **kwargs):
        raise FileNotFoundError("mvn")

    monkeypatch.setattr(validator.subprocess, "run", missing)

    result = run_tests(tmp_path, "FooTest")

    assert result.passed is False
    assert "mvn" in result.message


def test_run_tests_reports_timeout(tmp_path, monkeypatch):
    def slow(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="mvn", timeout=5)

    monkeypatch.setattr(validator.subprocess, "run", slow)

    result = run_tests(tmp_path, "FooTest", timeout=5)

    assert result.passed is False
    assert "timed out after 5s" in result.message
