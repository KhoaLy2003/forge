"""Forge's Typer entry point: wires the wizard, preview, renderer, and validator into `forge new`."""

import shutil
import traceback
from pathlib import Path

import typer

from core.config_schema import ForgeConfig
from core.progress import step
from core.renderer import render_tree, resolve_tree
from core.tree_preview import confirm, format_tree
from core.validator import check_structure, run_compile
from core.wizard import collect_params

app = typer.Typer()


@app.callback()
def callback() -> None:
    """Forge: scaffold a new Spring Boot service."""


TEMPLATE_DIR = Path(__file__).parent / "templates" / "base-layered"

EXPECTED_STRUCTURAL_PATHS = [
    Path("pom.xml"),
    Path("docker-compose.yml"),
    Path(".gitignore"),
    Path("README.md"),
    Path("src/main/resources/application.yml"),
    Path("src/main/resources/db/changelog/db.changelog-master.xml"),
    Path("src/main/resources/db/changelog/001-create-example-table.sql"),
]


def expected_structural_paths(context: dict) -> list[Path]:
    """Build the rendered Java-source paths the template produces for this run's context."""
    package_path = context["package_path"]
    app_class_name = context["app_class_name"]
    java_root = Path("src/main/java") / package_path
    return [
        java_root / f"{app_class_name}Application.java",
        java_root / "entity" / "Example.java",
        java_root / "repository" / "ExampleRepository.java",
        java_root / "service" / "ExampleService.java",
        java_root / "controller" / "ExampleController.java",
    ]


@app.command()
def new(
    project_name: str = typer.Option(None, "--name"),
    target_path: str = typer.Option(None, "--path"),
    group_id: str = typer.Option(None, "--group-id"),
    artifact_id: str = typer.Option(None, "--artifact-id"),
    verbose: bool = typer.Option(False, "--verbose"),
):
    """Scaffold a new Spring Boot project: collect params, preview, render, then validate."""
    overrides = {
        "project_name": project_name,
        "target_path": target_path,
        "group_id": group_id,
        "artifact_id": artifact_id,
    }
    config = collect_params(overrides)

    if config.target_dir.exists():
        typer.echo(f"Error: target directory already exists: {config.target_dir}")
        raise typer.Exit(code=1)

    if not TEMPLATE_DIR.is_dir():
        typer.echo(f"Error: template directory not found: {TEMPLATE_DIR}")
        raise typer.Exit(code=1)

    context = config.template_context()
    tree = resolve_tree(TEMPLATE_DIR, context)
    if not confirm(format_tree(tree)):
        typer.echo("Cancelled.")
        raise typer.Exit(code=0)

    step("Writing project files...", 1, 3)
    try:
        render_tree(TEMPLATE_DIR, config.target_dir, context)
    except Exception as exc:
        typer.echo(f"Error: failed to write project files: {exc}")
        if verbose:
            typer.echo(traceback.format_exc())
        if typer.confirm("Delete the generated folder?", default=False):
            if config.target_dir.exists():
                shutil.rmtree(config.target_dir)
        raise typer.Exit(code=1)

    step("Running structural check...", 2, 3)
    structural = check_structure(
        config.target_dir, EXPECTED_STRUCTURAL_PATHS + expected_structural_paths(context)
    )

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


def main():
    """Console-script entry point."""
    app()


if __name__ == "__main__":
    main()
