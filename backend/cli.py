"""Forge's Typer entry point: wires the wizard, preview, renderer, and validator into `forge new`."""

import json
import secrets
import shutil
import socket
import sys
import threading
import traceback
import webbrowser
from pathlib import Path

import typer
from pydantic import ValidationError

try:  # Typer >= 0.27 vendors Click; a standalone click may also be installed but is not the one Typer uses
    from typer._click.core import ParameterSource
except ImportError:  # pragma: no cover - older Typer depends on the real click package
    from click.core import ParameterSource

from core.config_schema import ForgeConfig
from core.progress import step
from core.renderer import render_files, render_tree, resolve_tree
from core.generation import build_plan, preview_config, structural_paths
from core.schema_export import forge_yaml_schema
from core.templates import ENTITY_DIR, JOIN_DIR, SHARED_DIR
from core.tree_preview import confirm, format_tree
from core.validator import check_observability, check_structure, run_compile
from core.entity_spec import load_forge_yaml
from core.wizard import collect_entities, collect_params, needs_prompt, save_forge_yaml

app = typer.Typer()


@app.callback()
def callback() -> None:
    """Forge: scaffold a new Spring Boot service."""


@app.command()
def new(
    ctx: typer.Context,
    project_name: str = typer.Option(None, "--name"),
    target_path: str = typer.Option(None, "--path"),
    group_id: str = typer.Option(None, "--group-id"),
    artifact_id: str = typer.Option(None, "--artifact-id"),
    template: str = typer.Option("base-layered", "--template"),
    from_file: Path = typer.Option(
        None, "--from", help="forge.yaml with project parameters and/or entities (CLI flags win over it)."
    ),
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
    file_entities: dict = {}
    if from_file is not None:
        try:
            project_file = load_forge_yaml(from_file)
        except ValueError as exc:
            typer.echo(f"Error: {exc}")
            raise typer.Exit(code=1)
        # precedence: explicit CLI flag > value from the file > wizard prompt
        for key in ("project_name", "target_path", "group_id", "artifact_id"):
            if overrides[key] is None and getattr(project_file, key) is not None:
                overrides[key] = str(getattr(project_file, key))
        # --template has a hardcoded default, so "given on the command line" comes from Click, not the value
        template_given = ctx.get_parameter_source("template") == ParameterSource.COMMANDLINE
        if not template_given and project_file.template is not None:
            overrides["template"] = project_file.template
        file_entities = project_file.entities
        overrides["entities"] = file_entities

    interactive = needs_prompt(overrides)
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

    # The entity step only runs in an interactive run: a flag-complete or --from-complete invocation never gets it.
    model_entered = interactive and config.template == "base-layered" and not file_entities
    if model_entered:
        entities = collect_entities()
        if entities:
            try:
                config = ForgeConfig(**{**config.model_dump(), "entities": entities})
            except ValidationError as exc:
                typer.echo(f"Error: {exc}")
                raise typer.Exit(code=1)

    context, excluded = build_plan(config)
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
    structural = check_structure(config.target_dir, structural_paths(context, excluded))

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
    if model_entered and config.entities and typer.confirm("Save the model as forge.yaml?", default=False):
        saved_to = config.target_dir / "forge.yaml"
        save_forge_yaml(config, saved_to)
        typer.echo(f"Saved {saved_to}")
    typer.echo(f"cd {config.target_dir}")
    typer.echo("docker compose up -d")
    typer.echo("mvn spring-boot:run")


def _load_model_config(path: Path, template: str | None = None) -> ForgeConfig:
    """Load a forge.yaml and build a placeholder-filled config; exit 1 with `Error: ...` on any problem."""
    try:
        project_file = load_forge_yaml(path)
        if template is not None:
            project_file.template = template
        return preview_config(project_file)
    except (ValueError, ValidationError) as exc:
        typer.echo(f"Error: {exc}")
        raise typer.Exit(code=1)


@app.command()
def schema(
    output: Path = typer.Option(None, "--output", help="Write the schema to this file instead of stdout."),
):
    """Print the JSON Schema for forge.yaml (add `# yaml-language-server: $schema=<path>` for editor completion)."""
    text = json.dumps(forge_yaml_schema(), indent=2)
    if output is None:
        typer.echo(text)
        return
    output.write_text(text + "\n", encoding="utf-8")
    typer.echo(f"Wrote {output}")


@app.command("validate-model")
def validate_model(file: Path = typer.Argument(..., help="forge.yaml to check.")):
    """Validate a forge.yaml model without writing anything."""
    config = _load_model_config(file)
    context = config.template_context()
    if not config.has_entities:
        typer.echo("OK: no entities (the Example slice will be generated)")
        return
    typer.echo(f"OK: {len(config.entities)} entities, {len(context['join_tables'])} join tables")
    typer.echo("Liquibase changelog order:")
    for name in context["changelog_files"]:
        typer.echo(f"  {name}")


@app.command()
def preview(
    ctx: typer.Context,
    from_file: Path = typer.Option(..., "--from", help="forge.yaml to preview."),
    template: str = typer.Option("base-layered", "--template"),
    file: str = typer.Option(None, "--file", help="Print this generated file's content (posix path)."),
):
    """Show the files a forge.yaml would generate, or one file's content. Nothing is written."""
    template_given = ctx.get_parameter_source("template") == ParameterSource.COMMANDLINE
    config = _load_model_config(from_file, template if template_given else None)
    context, excluded = build_plan(config)
    try:
        if file is None:
            tree = resolve_tree(
                SHARED_DIR, context, excluded=excluded, entities_dir=ENTITY_DIR, join_dir=JOIN_DIR
            )
            typer.echo(format_tree(tree))
            return
        files = render_files(
            SHARED_DIR, context, excluded=excluded, entities_dir=ENTITY_DIR, join_dir=JOIN_DIR
        )
    except ValueError as exc:
        typer.echo(f"Error: {exc}")
        raise typer.Exit(code=1)
    rel = Path(file)
    if rel not in files:
        typer.echo(f"Error: no such file in the generated project: {file}")
        raise typer.Exit(code=1)
    if files[rel] is None:
        typer.echo(f"Error: {file} is a binary file")
        raise typer.Exit(code=1)
    typer.echo(files[rel], nl=False)


@app.command()
def ui(
    port: int = typer.Option(0, "--port", help="Port to bind on 127.0.0.1 (0 picks a free one)."),
    no_browser: bool = typer.Option(False, "--no-browser"),
):
    """Open the local web UI for editing and generating a project."""
    try:
        import uvicorn

        from core.ui.server import create_app
    except ImportError:
        typer.echo('Error: the UI needs extra dependencies: pip install "forge[ui]"')
        raise typer.Exit(code=1)
    if port == 0:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
    token = secrets.token_urlsafe(16)
    url = f"http://127.0.0.1:{port}/?token={token}"
    typer.echo(url)
    if not no_browser:
        threading.Timer(0.5, webbrowser.open, [url]).start()
    uvicorn.run(create_app(token), host="127.0.0.1", port=port, log_level="warning")


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
