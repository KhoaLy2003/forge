"""Shared generation helpers: the structural-path tables and plan/check helpers used by the CLI and the UI."""

from pathlib import Path

from core.config_schema import ForgeConfig
from core.entity_spec import ProjectFile
from core.templates import discover_templates, dynamic_excludes, filter_excluded_paths
from core.validator import ValidationResult, check_observability, check_structure, run_compile

TEMPLATES = discover_templates()

EXPECTED_STRUCTURAL_PATHS = [
    Path("pom.xml"),
    Path(".github/workflows/ci.yml"),
    Path("docker-compose.yml"),
    Path(".gitignore"),
    Path("README.md"),
    Path("src/main/resources/application.yml"),
    Path("src/main/resources/application-dev.yml"),
    Path("src/main/resources/application-prod.yml"),
    Path("src/main/resources/db/changelog/db.changelog-master.xml"),
    Path("src/main/resources/db/changelog/001-create-example-table.sql"),
    Path("src/main/resources/db/changelog/002-create-notifications.sql"),
    Path("docs/observability/logging.md"),
    # Monitoring files; the minimal template excludes these via its manifest.
    Path("docs/observability/runbook.md"),
    Path("docker-compose.observability.yml"),
    Path("observability/prometheus/prometheus.yml"),
    Path("observability/prometheus/alerts.yml"),
    Path("observability/grafana/provisioning/datasources/datasources.yml"),
    Path("observability/grafana/provisioning/dashboards/dashboards.yml"),
    Path("observability/grafana/dashboards/service-overview.json"),
    Path("observability/loki/loki-config.yml"),
    Path("observability/alloy/config.alloy"),
]


def expected_structural_paths(context: dict) -> list[Path]:
    """Build the rendered Java-source paths the template produces for this run's context."""
    package_path = context["package_path"]
    app_class_name = context["app_class_name"]
    java_root = Path("src/main/java") / package_path
    test_root = Path("src/test/java") / package_path
    common = java_root / "common"
    example = java_root / "example"
    notification = java_root / "notification"
    notification_test = test_root / "notification"
    paths = [
        java_root / f"{app_class_name}Application.java",
        common / "entity" / "BaseEntity.java",
        common / "dto" / "ApiResponse.java",
        common / "dto" / "PageResponse.java",
        common / "dto" / "PaginationMeta.java",
        common / "util" / "PaginationUtils.java",
        common / "util" / "DateTimeUtils.java",
        common / "util" / "SlugUtils.java",
        common / "util" / "JsonUtils.java",
        common / "exception" / "GlobalExceptionHandler.java",
        common / "exception" / "ResourceNotFoundException.java",
        common / "exception" / "ConflictException.java",
        common / "exception" / "ErrorDetails.java",
        common / "exception" / "ValidationErrorDetails.java",
        common / "exception" / "UnauthorizedException.java",
        common / "exception" / "ForbiddenException.java",
        common / "exception" / "BadRequestException.java",
        notification / "Audience.java",
        notification / "ChannelSender.java",
        notification / "config" / "MailConfig.java",
        notification / "CurrentRecipientProvider.java",
        notification / "DeliveryProcessor.java",
        notification / "DeliveryStatus.java",
        notification / "DeliveryWorker.java",
        notification / "dto" / "InboxItemResponse.java",
        notification / "dto" / "PreferencesResponse.java",
        notification / "dto" / "UnreadCountResponse.java",
        notification / "dto" / "UpdatePreferencesRequest.java",
        notification / "EmailSender.java",
        notification / "entity" / "NotificationPreference.java",
        notification / "entity" / "NotificationTemplate.java",
        notification / "NotificationAck.java",
        notification / "NotificationChannel.java",
        notification / "NotificationController.java",
        notification / "NotificationQueries.java",
        notification / "NotificationRequest.java",
        notification / "NotificationService.java",
        notification / "NotificationServiceImpl.java",
        notification / "NotificationStatus.java",
        notification / "Recipient.java",
        notification / "RecipientDirectory.java",
        notification / "repository" / "NotificationPreferenceRepository.java",
        notification / "repository" / "NotificationTemplateRepository.java",
        notification / "TemplateRenderer.java",
        notification_test / "config" / "MailConfigTest.java",
        notification_test / "DeliveryProcessorTest.java",
        notification_test / "DeliveryWorkerTest.java",
        notification_test / "EmailSenderTest.java",
        notification_test / "entity" / "NotificationEntitiesTest.java",
        notification_test / "ExtensionPointDefaultsTest.java",
        notification_test / "NotificationControllerDefaultProviderTest.java",
        notification_test / "NotificationControllerTest.java",
        notification_test / "NotificationQueriesTest.java",
        notification_test / "NotificationServiceImplEnqueueTest.java",
        notification_test / "NotificationServiceImplReadTest.java",
        notification_test / "NotificationTypesTest.java",
        notification_test / "repository" / "NotificationRepositoriesTest.java",
        notification_test / "TemplateRendererTest.java",
        common / "config" / "JpaAuditingConfig.java",
        common / "config" / "OpenApiConfig.java",
        common / "config" / "CorrelationIdFilter.java",
        common / "config" / "RequestLogFilter.java",
        common / "config" / "JobContext.java",
        common / "config" / "SensitiveDataCustomizer.java",
        example / "entity" / "Example.java",
        example / "entity" / "ExampleStatus.java",
        example / "dto" / "CreateExampleRequest.java",
        example / "dto" / "UpdateExampleRequest.java",
        example / "dto" / "ExampleResponse.java",
        example / "mapper" / "ExampleMapper.java",
        example / "repository" / "ExampleRepository.java",
        example / "service" / "ExampleService.java",
        example / "service" / "ExampleServiceImpl.java",
        example / "controller" / "ExampleController.java",
        test_root / "common" / "util" / "PaginationUtilsTest.java",
        test_root / "common" / "util" / "DateTimeUtilsTest.java",
        test_root / "common" / "util" / "SlugUtilsTest.java",
        test_root / "common" / "util" / "JsonUtilsTest.java",
        test_root / "common" / "exception" / "GlobalExceptionHandlerTest.java",
        test_root / "common" / "config" / "CorrelationIdFilterTest.java",
        test_root / "common" / "config" / "RequestLogFilterTest.java",
        test_root / "common" / "config" / "JobContextTest.java",
        test_root / "common" / "config" / "SensitiveDataCustomizerTest.java",
        test_root / "common" / "config" / "StructuredLogFormatTest.java",
        test_root / "common" / "config" / "StructuredLogTestSupport.java",
        test_root / "common" / "config" / "ManagementConfigTest.java",
        test_root / "example" / "repository" / "ExampleRepositoryTest.java",
        test_root / "example" / "mapper" / "ExampleMapperTest.java",
        test_root / "example" / "service" / "ExampleServiceImplTest.java",
        test_root / "example" / "controller" / "ExampleControllerTest.java",
    ]

    changelog = Path("src/main/resources/db/changelog")
    if context.get("has_entities"):
        paths.append(common / "search" / "SearchSpecifications.java")
    for entity in context.get("entities", []):
        main_root = java_root / entity.package
        test_package = test_root / entity.package
        name = entity.name
        paths += [
            main_root / "entity" / f"{name}.java",
            main_root / "repository" / f"{name}Repository.java",
            main_root / "dto" / f"Create{name}Request.java",
            main_root / "dto" / f"Update{name}Request.java",
            main_root / "dto" / f"{name}Filter.java",
            main_root / "dto" / f"{name}Response.java",
            main_root / "mapper" / f"{name}Mapper.java",
            main_root / "service" / f"{name}Service.java",
            main_root / "service" / f"{name}ServiceImpl.java",
            main_root / "controller" / f"{name}Controller.java",
            test_package / "service" / f"{name}ServiceImplTest.java",
            test_package / "mapper" / f"{name}MapperTest.java",
            test_package / "controller" / f"{name}ControllerTest.java",
            test_package / "repository" / f"{name}RepositoryTest.java",
            changelog / entity.changelog_file,
        ]
    for join_table in context.get("join_tables", []):
        paths.append(changelog / join_table.changelog_file)
    if context.get("constraints_changelog_file"):
        paths.append(changelog / context["constraints_changelog_file"])
    return paths


PLACEHOLDERS = {"project_name": "model-check", "group_id": "com.example", "artifact_id": "model-check"}


def build_plan(config: ForgeConfig) -> tuple[dict, tuple[str, ...]]:
    """Return the template context and the excluded globs for this config."""
    context = config.template_context()
    excluded = TEMPLATES[config.template] + dynamic_excludes(context)
    return context, excluded


def structural_paths(context: dict, excluded: tuple[str, ...]) -> list[Path]:
    """Every path the structural check expects, after template exclusions."""
    static_paths = filter_excluded_paths(EXPECTED_STRUCTURAL_PATHS, excluded, context)
    dynamic_paths = filter_excluded_paths(expected_structural_paths(context), excluded, context)
    return static_paths + dynamic_paths


def preview_config(project_file: ProjectFile) -> ForgeConfig:
    """Build a config from a model file, using placeholders for blank project parameters."""
    return ForgeConfig(
        project_name=project_file.project_name or PLACEHOLDERS["project_name"],
        target_path=project_file.target_path or Path("."),
        group_id=project_file.group_id or PLACEHOLDERS["group_id"],
        artifact_id=project_file.artifact_id or PLACEHOLDERS["artifact_id"],
        template=project_file.template or "base-layered",
        entities=project_file.entities,
    )


def run_checks(
    config: ForgeConfig, context: dict, excluded: tuple[str, ...], with_compile: bool
) -> list[tuple[str, ValidationResult]]:
    """Run structure, observability and (optionally) compile checks, stopping at the first failure."""
    results: list[tuple[str, ValidationResult]] = []
    steps = [
        ("structure", lambda: check_structure(config.target_dir, structural_paths(context, excluded))),
        ("observability", lambda: check_observability(config.target_dir, config.include_monitoring)),
    ]
    if with_compile:
        steps.append(("compile", lambda: run_compile(config.target_dir)))
    for name, run in steps:
        result = run()
        results.append((name, result))
        if not result.passed:
            break
    return results
