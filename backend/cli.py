"""Forge's Typer entry point: `forge init` writes forge.yaml, `forge new` generates the project it describes."""

import shutil
import sys
import traceback
from pathlib import Path

import typer

from core.progress import step
from core.project_config import CONFIG_FILENAME, MissingConfigError, build_config, write_starter
from core.renderer import render_tree, resolve_tree
from core.templates import (
    ENTITY_DIR,
    JOIN_DIR,
    SHARED_DIR,
    discover_templates,
    dynamic_excludes,
    filter_excluded_paths,
)
from core.tree_preview import confirm, format_tree
from core.validator import check_observability, check_structure, run_compile

app = typer.Typer()


@app.callback()
def callback() -> None:
    """Forge: scaffold a new Spring Boot service."""


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
    for entity in context.get("entities", []):
        main_root = java_root / entity.package
        test_package = test_root / entity.package
        name = entity.name
        paths += [
            main_root / "entity" / f"{name}.java",
            main_root / "repository" / f"{name}Repository.java",
            main_root / "dto" / f"Create{name}Request.java",
            main_root / "dto" / f"Update{name}Request.java",
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


@app.command()
def init(verbose: bool = typer.Option(False, "--verbose")):
    """Write a commented forge.yaml into the current folder. Edit it, then run `forge new`."""
    path = Path.cwd() / CONFIG_FILENAME
    try:
        write_starter(path)
    except FileExistsError as exc:
        typer.echo(f"Error: {exc}")
        raise typer.Exit(code=1)
    typer.echo(f"Created {path}. Edit it, then run \"forge new\".")


@app.command()
def new(verbose: bool = typer.Option(False, "--verbose")):
    """Generate the project described by ./forge.yaml: preview, render, then validate."""
    path = Path.cwd() / CONFIG_FILENAME
    try:
        config = build_config(path)
    except MissingConfigError:
        typer.echo(f'No {CONFIG_FILENAME} found in {Path.cwd()}. Run "forge init" first.')
        raise typer.Exit(code=1)
    except ValueError as exc:
        typer.echo(f"Error: {exc}")
        raise typer.Exit(code=1)

    typer.echo(f"Config:   {path}")
    typer.echo(f"Project:  {config.project_name}")
    typer.echo(f"Target:   {config.target_dir}")
    typer.echo(f"Group:    {config.group_id}")
    typer.echo(f"Artifact: {config.artifact_id}")
    typer.echo(f"Template: {config.template}")

    if config.target_dir.exists():
        typer.echo(f"Error: target directory already exists: {config.target_dir}")
        raise typer.Exit(code=1)

    if not SHARED_DIR.is_dir():
        typer.echo(f"Error: template directory not found: {SHARED_DIR}")
        raise typer.Exit(code=1)

    context = config.template_context()
    excluded = TEMPLATES[config.template] + dynamic_excludes(context)
    tree = resolve_tree(
        SHARED_DIR, context, excluded=excluded, entities_dir=ENTITY_DIR, join_dir=JOIN_DIR
    )
    if not confirm(format_tree(tree)):
        typer.echo("Cancelled.")
        raise typer.Exit(code=0)

    step("Writing project files...", 1, 4)
    try:
        render_tree(
            SHARED_DIR,
            config.target_dir,
            context,
            excluded=excluded,
            entities_dir=ENTITY_DIR,
            join_dir=JOIN_DIR,
        )
    except Exception as exc:
        typer.echo(f"Error: failed to write project files: {exc}")
        if verbose:
            typer.echo(traceback.format_exc())
        if typer.confirm("Delete the generated folder?", default=False):
            if config.target_dir.exists():
                shutil.rmtree(config.target_dir)
        raise typer.Exit(code=1)

    step("Running structural check...", 2, 4)
    static_paths = filter_excluded_paths(EXPECTED_STRUCTURAL_PATHS, excluded, context)
    dynamic_paths = filter_excluded_paths(expected_structural_paths(context), excluded, context)
    structural = check_structure(config.target_dir, static_paths + dynamic_paths)

    observability = None
    if structural.passed:
        step("Running observability check...", 3, 4)
        observability = check_observability(config.target_dir, config.include_monitoring)

    compile_result = None
    if structural.passed and observability.passed:
        step("Running compile check...", 4, 4)
        compile_result = run_compile(config.target_dir)

    failure = next(
        (
            result
            for result in (structural, observability, compile_result)
            if result is not None and not result.passed
        ),
        None,
    )
    if failure is not None:
        typer.echo(f"Validation failed: {failure.message}\n{failure.details}")
        if typer.confirm("Delete the generated folder?", default=False):
            shutil.rmtree(config.target_dir)
        raise typer.Exit(code=1)

    typer.echo("Project generated successfully!")
    typer.echo(f"cd {config.target_dir}")
    typer.echo("docker compose up -d")
    typer.echo("mvn spring-boot:run")


def main():  # pragma: no cover
    """Console-script entry point."""
    # The tree preview uses Unicode box-drawing characters; Windows consoles
    # commonly default to a non-UTF-8 codepage (e.g. cp1252), which raises
    # UnicodeEncodeError on print() otherwise.
    for stream in (sys.stdout, sys.stderr):
        if getattr(stream, "encoding", None) and stream.encoding.lower() != "utf-8":
            stream.reconfigure(encoding="utf-8", errors="replace")
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
