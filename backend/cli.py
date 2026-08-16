"""Forge's Typer entry point: wires the wizard, preview, renderer, and validator into `forge new`."""

import shutil
import sys
import traceback
from pathlib import Path

import typer
from pydantic import ValidationError

from core.config_schema import ForgeConfig
from core.progress import step
from core.renderer import render_tree, resolve_tree
from core.templates import SHARED_DIR, discover_templates, filter_excluded_paths
from core.tree_preview import confirm, format_tree
from core.validator import check_structure, run_compile
from core.wizard import collect_params

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
]


def expected_structural_paths(context: dict) -> list[Path]:
    """Build the rendered Java-source paths the template produces for this run's context."""
    package_path = context["package_path"]
    app_class_name = context["app_class_name"]
    java_root = Path("src/main/java") / package_path
    test_root = Path("src/test/java") / package_path
    common = java_root / "common"
    example = java_root / "example"
    return [
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
        common / "config" / "JpaAuditingConfig.java",
        common / "config" / "OpenApiConfig.java",
        common / "config" / "CorrelationIdFilter.java",
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
        test_root / "example" / "repository" / "ExampleRepositoryTest.java",
        test_root / "example" / "mapper" / "ExampleMapperTest.java",
        test_root / "example" / "service" / "ExampleServiceImplTest.java",
        test_root / "example" / "controller" / "ExampleControllerTest.java",
    ]


@app.command()
def new(
    project_name: str = typer.Option(None, "--name"),
    target_path: str = typer.Option(None, "--path"),
    group_id: str = typer.Option(None, "--group-id"),
    artifact_id: str = typer.Option(None, "--artifact-id"),
    template: str = typer.Option("base-layered", "--template"),
    verbose: bool = typer.Option(False, "--verbose"),
):
    """Scaffold a new Spring Boot project: collect params, preview, render, then validate."""
    overrides = {
        "project_name": project_name,
        "target_path": target_path,
        "group_id": group_id,
        "artifact_id": artifact_id,
        "template": template,
    }
    try:
        config = collect_params(overrides)
    except ValidationError as exc:
        typer.echo(f"Error: {exc}")
        raise typer.Exit(code=1)

    if config.target_dir.exists():
        typer.echo(f"Error: target directory already exists: {config.target_dir}")
        raise typer.Exit(code=1)

    if not SHARED_DIR.is_dir():
        typer.echo(f"Error: template directory not found: {SHARED_DIR}")
        raise typer.Exit(code=1)

    excluded = TEMPLATES[config.template]

    context = config.template_context()
    tree = resolve_tree(SHARED_DIR, context, excluded=excluded)
    if not confirm(format_tree(tree)):
        typer.echo("Cancelled.")
        raise typer.Exit(code=0)

    step("Writing project files...", 1, 3)
    try:
        render_tree(SHARED_DIR, config.target_dir, context, excluded=excluded)
    except Exception as exc:
        typer.echo(f"Error: failed to write project files: {exc}")
        if verbose:
            typer.echo(traceback.format_exc())
        if typer.confirm("Delete the generated folder?", default=False):
            if config.target_dir.exists():
                shutil.rmtree(config.target_dir)
        raise typer.Exit(code=1)

    step("Running structural check...", 2, 3)
    static_paths = filter_excluded_paths(EXPECTED_STRUCTURAL_PATHS, excluded, context)
    dynamic_paths = filter_excluded_paths(expected_structural_paths(context), excluded, context)
    structural = check_structure(config.target_dir, static_paths + dynamic_paths)

    compile_result = None
    if structural.passed:
        step("Running compile check...", 3, 3)
        compile_result = run_compile(config.target_dir)

    failure = structural if not structural.passed else (
        compile_result if compile_result and not compile_result.passed else None
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
