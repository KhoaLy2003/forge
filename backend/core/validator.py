"""Post-generation validation: structural file checks and a real `mvn compile` shell-out."""

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import yaml

from core.observability_metrics import KNOWN_METRICS, extract_metric_names


@dataclass
class ValidationResult:
    """The outcome of one validation check."""

    passed: bool
    message: str
    details: str = ""


def check_structure(target_dir: Path, expected_paths: list[Path]) -> ValidationResult:
    """Check that every expected relative path exists under target_dir."""
    missing = [str(p) for p in expected_paths if not (target_dir / p).exists()]
    if missing:
        return ValidationResult(
            False, "Structural check failed: missing files", "\n".join(missing)
        )
    return ValidationResult(True, "Structural check passed")


def run_compile(target_dir: Path, timeout: int = 300) -> ValidationResult:
    """Run mvn test-compile in target_dir (compiles main and test sources, without executing tests) and report whether it succeeded."""
    mvn_cmd = shutil.which("mvn") or "mvn"
    try:
        result = subprocess.run(
            [mvn_cmd, "-q", "test-compile"],
            cwd=target_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return ValidationResult(False, "mvn executable not found on PATH")
    except subprocess.TimeoutExpired:
        return ValidationResult(False, f"mvn test-compile timed out after {timeout}s")

    if result.returncode != 0:
        return ValidationResult(
            False, "mvn test-compile failed", result.stdout + result.stderr
        )
    return ValidationResult(True, "Compile check passed")


def run_tests(target_dir: Path, test_filter: str, timeout: int = 300) -> ValidationResult:
    """Run `mvn test -Dtest=<test_filter>` in target_dir and report whether those tests passed.

    Intended for Docker-free unit tests of a generated project; a filter naming a class that does
    not exist fails, because Maven reports "no tests matching".
    """
    mvn_cmd = shutil.which("mvn") or "mvn"
    try:
        result = subprocess.run(
            [mvn_cmd, "-q", "test", f"-Dtest={test_filter}"],
            cwd=target_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return ValidationResult(False, "mvn executable not found on PATH")
    except subprocess.TimeoutExpired:
        return ValidationResult(False, f"mvn test timed out after {timeout}s")

    if result.returncode != 0:
        return ValidationResult(
            False, f"mvn test failed for {test_filter}", result.stdout + result.stderr
        )
    return ValidationResult(True, "Tests passed")


OBSERVABILITY_FILES = [
    Path("docker-compose.observability.yml"),
    Path("observability/prometheus/prometheus.yml"),
    Path("observability/prometheus/alerts.yml"),
    Path("observability/grafana/provisioning/datasources/datasources.yml"),
    Path("observability/grafana/provisioning/dashboards/dashboards.yml"),
    Path("observability/grafana/dashboards/service-overview.json"),
    Path("observability/loki/loki-config.yml"),
    Path("observability/alloy/config.alloy"),
    Path("docs/observability/runbook.md"),
]

_ALERT_LABELS = ("severity", "team")
_ALERT_ANNOTATIONS = ("summary", "impact", "first_checks", "runbook")


def _unknown_metrics(expr: str) -> list[str]:
    return sorted(extract_metric_names(expr) - KNOWN_METRICS)


def _check_alerts(alerts_path: Path, problems: list[str]) -> None:
    document = yaml.safe_load(alerts_path.read_text(encoding="utf-8")) or {}
    for group in document.get("groups", []):
        for rule in group.get("rules", []):
            name = rule.get("alert") or rule.get("record") or "<unnamed rule>"
            for metric in _unknown_metrics(str(rule.get("expr", ""))):
                problems.append(f"alerts.yml: rule {name} references unknown metric {metric}")
            if "alert" not in rule:
                continue
            labels, annotations = rule.get("labels") or {}, rule.get("annotations") or {}
            for label in _ALERT_LABELS:
                if not labels.get(label):
                    problems.append(f"alerts.yml: alert {name} is missing label {label}")
            for annotation in _ALERT_ANNOTATIONS:
                if not annotations.get(annotation):
                    problems.append(f"alerts.yml: alert {name} is missing annotation {annotation}")


def _datasource_type(node: dict, default: str = "prometheus") -> str:
    datasource = node.get("datasource")
    if isinstance(datasource, dict):
        return str(datasource.get("type", default)).lower()
    if isinstance(datasource, str):
        return "loki" if "loki" in datasource.lower() else default
    return default


def _iter_panels(panels: list):
    for panel in panels:
        yield panel
        yield from _iter_panels(panel.get("panels", []))


def _check_dashboard(dashboard_path: Path, problems: list[str]) -> None:
    dashboard = json.loads(dashboard_path.read_text(encoding="utf-8"))
    panels = list(dashboard.get("panels", []))
    for row in dashboard.get("rows", []):
        panels.extend(row.get("panels", []))
    for panel in _iter_panels(panels):
        panel_type = _datasource_type(panel)
        for target in panel.get("targets", []):
            if _datasource_type(target, panel_type) != "prometheus" or "expr" not in target:
                continue
            title = panel.get("title", "<untitled panel>")
            for metric in _unknown_metrics(str(target["expr"])):
                problems.append(
                    f"service-overview.json: panel {title!r} references unknown metric {metric}"
                )


def check_observability(target_dir: Path, include_monitoring: bool) -> ValidationResult:
    """Docker-free static checks of the generated monitoring files.

    Verifies the files exist, the YAML/JSON parses, and that every metric referenced by an alert
    rule or a Prometheus dashboard query is one the application is known to expose. Alloy's own
    syntax is only checked for existence. Returns a passing result when the template ships no
    monitoring files.
    """
    if not include_monitoring:
        return ValidationResult(True, "Observability check skipped (monitoring not included)")

    problems = [f"missing file: {p.as_posix()}" for p in OBSERVABILITY_FILES if not (target_dir / p).exists()]
    if problems:
        return ValidationResult(False, "Observability check failed", "\n".join(problems))

    for path in OBSERVABILITY_FILES:
        if path.suffix in (".yml", ".yaml"):
            try:
                yaml.safe_load((target_dir / path).read_text(encoding="utf-8"))
            except yaml.YAMLError as exc:
                problems.append(f"{path.as_posix()}: invalid YAML: {exc}")
        elif path.suffix == ".json":
            try:
                json.loads((target_dir / path).read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                problems.append(f"{path.as_posix()}: invalid JSON: {exc}")
    if problems:
        return ValidationResult(False, "Observability check failed", "\n".join(problems))

    _check_alerts(target_dir / "observability/prometheus/alerts.yml", problems)
    _check_dashboard(target_dir / "observability/grafana/dashboards/service-overview.json", problems)
    if problems:
        return ValidationResult(False, "Observability check failed", "\n".join(problems))
    return ValidationResult(True, "Observability check passed")
