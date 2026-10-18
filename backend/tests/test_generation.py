# tests/test_generation.py
import pytest

from core.generation import EXPECTED_STRUCTURAL_PATHS, expected_structural_paths
from core.config_schema import ForgeConfig
from core.renderer import render_tree
from core.templates import SHARED_DIR, discover_templates, filter_excluded_paths
from core.validator import check_observability, check_structure, run_compile, run_tests

# Docker-free generated unit tests covering the observability baseline (no database needed).
LOGGING_TESTS = [
    "CorrelationIdFilterTest",
    "RequestLogFilterTest",
    "JobContextTest",
    "SensitiveDataCustomizerTest",
    "StructuredLogFormatTest",
    "GlobalExceptionHandlerTest",
]

# Docker-free notification-module unit tests (base-layered only). NotificationQueriesTest needs a
# real PostgreSQL and runs in the generated project's CI instead.
NOTIFICATION_TESTS = [
    "TemplateRendererTest",
    "NotificationTypesTest",
    "NotificationEntitiesTest",
    "NotificationRepositoriesTest",
    "NotificationServiceImplEnqueueTest",
    "NotificationServiceImplReadTest",
    "EmailSenderTest",
    "ExtensionPointDefaultsTest",
    "MailConfigTest",
    "DeliveryProcessorTest",
    "DeliveryWorkerTest",
    "NotificationControllerTest",
    "NotificationControllerDefaultProviderTest",
]


@pytest.mark.parametrize("template_name", sorted(discover_templates()))
def test_generated_project_passes_structural_and_compile_checks(tmp_path, template_name):
    config = ForgeConfig(
        project_name="demo-service",
        target_path=tmp_path / template_name,
        group_id="com.example",
        artifact_id="demo-service",
        template=template_name,
    )
    excluded = discover_templates()[template_name]
    context = config.template_context()

    render_tree(SHARED_DIR, config.target_dir, context, excluded=excluded)

    static_paths = filter_excluded_paths(EXPECTED_STRUCTURAL_PATHS, excluded, context)
    dynamic_paths = filter_excluded_paths(expected_structural_paths(context), excluded, context)
    structural = check_structure(config.target_dir, static_paths + dynamic_paths)
    assert structural.passed, structural.details

    observability = check_observability(config.target_dir, config.include_monitoring)
    assert observability.passed, observability.details

    compile_result = run_compile(config.target_dir)
    assert compile_result.passed, compile_result.details

    tests = list(LOGGING_TESTS)
    if config.include_monitoring:
        tests.append("ManagementConfigTest")
    if config.use_liquibase:
        tests.extend(NOTIFICATION_TESTS)
    test_result = run_tests(config.target_dir, ",".join(tests))
    assert test_result.passed, test_result.details

    if template_name == "minimal":
        assert not (config.target_dir / "src/main/resources/db/changelog").exists()


def test_minimal_template_has_logging_baseline_but_no_monitoring(tmp_path):
    config = ForgeConfig(
        project_name="demo-service",
        target_path=tmp_path,
        group_id="com.example",
        artifact_id="demo-service",
        template="minimal",
    )
    render_tree(
        SHARED_DIR,
        config.target_dir,
        config.template_context(),
        excluded=discover_templates()["minimal"],
    )

    assert (config.target_dir / "docs/observability/logging.md").exists()
    assert not (config.target_dir / "docs/observability/runbook.md").exists()
    assert not (config.target_dir / "observability").exists()
    assert not (config.target_dir / "docker-compose.observability.yml").exists()
    assert "micrometer-registry-prometheus" not in (config.target_dir / "pom.xml").read_text(
        encoding="utf-8"
    )


def test_minimal_template_has_no_notification_module(tmp_path):
    config = ForgeConfig(
        project_name="demo-service",
        target_path=tmp_path,
        group_id="com.example",
        artifact_id="demo-service",
        template="minimal",
    )
    render_tree(
        SHARED_DIR,
        config.target_dir,
        config.template_context(),
        excluded=discover_templates()["minimal"],
    )

    java = config.target_dir / "src/main/java/com/example/demoservice"
    tests = config.target_dir / "src/test/java/com/example/demoservice"
    assert not (java / "notification").exists()
    assert not (tests / "notification").exists()
    assert not (config.target_dir / "src/main/resources/db/changelog").exists()
    assert "spring-boot-starter-mail" not in (config.target_dir / "pom.xml").read_text(encoding="utf-8")
    # UnauthorizedException is shared infrastructure and stays in both templates.
    assert (java / "common/exception/UnauthorizedException.java").exists()
