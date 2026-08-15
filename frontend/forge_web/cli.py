"""Forge Web's Typer entry point: wires the wizard, preview, renderer, and validator into `forge-web new`."""

import shutil
import sys
import traceback
from pathlib import Path

import typer

from forge_web.core.config_schema import ForgeWebConfig
from forge_web.core.progress import step
from forge_web.core.renderer import render_tree, resolve_tree
from forge_web.core.tree_preview import confirm, format_tree
from forge_web.core.validator import (
    check_no_hardcoded_design_values,
    check_no_spacing_scale_width_collisions,
    check_structure,
    run_build,
    run_typecheck,
)
from forge_web.core.wizard import collect_params

app = typer.Typer()


@app.callback()
def callback() -> None:
    """Forge Web: scaffold a new Vite + React + TypeScript + Shadcn project."""


TEMPLATE_DIR = Path(__file__).parent / "templates" / "base"

EXPECTED_STRUCTURAL_PATHS: list[Path] = [
    Path("package.json"),
    Path("tsconfig.json"),
    Path("tsconfig.node.json"),
    Path("vite.config.ts"),
    Path("index.html"),
    Path(".env.example"),
    Path(".gitignore"),
    Path("README.md"),
    Path("src/main.tsx"),
    Path("src/App.tsx"),
    Path("src/vite-env.d.ts"),
    Path("src/lib/utils.ts"),
    Path("src/lib/utils/format.ts"),
    Path("src/lib/hooks/use-items.ts"),
    Path("src/lib/api-client/types.ts"),
    Path("src/lib/api-client/api-client.ts"),
    Path("src/lib/api-client/mock-client.ts"),
    Path("src/lib/api-client/real-client.ts"),
    Path("src/lib/api-client/index.ts"),
    Path("src/styles/theme.css"),
    Path("src/components/ui/button.tsx"),
    Path("src/components/ui/input.tsx"),
    Path("src/components/ui/label.tsx"),
    Path("src/components/ui/card.tsx"),
    Path("src/components/ui/badge.tsx"),
    Path("src/components/ui/skeleton.tsx"),
    Path("src/components/ui/table.tsx"),
    Path("src/components/ui/data-table.tsx"),
    Path("src/components/ui/tabs.tsx"),
    Path("src/components/ui/select.tsx"),
    Path("src/components/ui/dialog.tsx"),
    Path("src/components/ui/alert-dialog.tsx"),
    Path("src/components/ui/dropdown-menu.tsx"),
    Path("src/components/ui/sonner.tsx"),
    Path("src/components/ui/form.tsx"),
    Path("src/components/ui/avatar.tsx"),
    Path("src/components/common/app-shell.tsx"),
    Path("src/components/common/nav-sidebar.tsx"),
    Path("src/pages/landing/landing-page.tsx"),
    Path("src/pages/dashboard/dashboard-page.tsx"),
    Path("src/pages/dashboard/item-form.tsx"),
    Path("src/pages/showcase/component-showcase-page.tsx"),
    Path("src/pages/static/not-found-page.tsx"),
    Path("src/pages/static/error-page.tsx"),
    Path("src/pages/static/loading-page.tsx"),
    Path("src/pages/static/empty-state.tsx"),
]


@app.command()
def new(
    project_name: str = typer.Option(None, "--name"),
    target_path: str = typer.Option(None, "--path"),
    api_base_url: str = typer.Option(None, "--api-base-url"),
    verbose: bool = typer.Option(False, "--verbose"),
):
    """Scaffold a new frontend project: collect params, preview, render, then validate."""
    overrides = {
        "project_name": project_name,
        "target_path": target_path,
        "api_base_url": api_base_url,
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

    step("Writing project files...", 1, 4)
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

    env_example = config.target_dir / ".env.example"
    if env_example.exists():
        shutil.copy(env_example, config.target_dir / ".env")

    step("Running structural check...", 2, 4)
    structural = check_structure(config.target_dir, EXPECTED_STRUCTURAL_PATHS)

    build_result = None
    typecheck_result = None
    tokens_result = None
    collision_result = None
    if structural.passed:
        step("Running build check...", 3, 4)
        build_result = run_build(config.target_dir)

    if structural.passed and build_result and build_result.passed:
        step("Running typecheck and design-token checks...", 4, 4)
        typecheck_result = run_typecheck(config.target_dir)
        if typecheck_result.passed:
            tokens_result = check_no_hardcoded_design_values(config.target_dir)
        if typecheck_result.passed and tokens_result and tokens_result.passed:
            collision_result = check_no_spacing_scale_width_collisions(config.target_dir)

    failure = None
    if not structural.passed:
        failure = structural
    elif build_result and not build_result.passed:
        failure = build_result
    elif typecheck_result and not typecheck_result.passed:
        failure = typecheck_result
    elif tokens_result and not tokens_result.passed:
        failure = tokens_result
    elif collision_result and not collision_result.passed:
        failure = collision_result

    if failure is not None:
        typer.echo(f"Validation failed: {failure.message}\n{failure.details}")
        if typer.confirm("Delete the generated folder?", default=False):
            shutil.rmtree(config.target_dir)
        raise typer.Exit(code=1)

    typer.echo("Project generated successfully!")
    typer.echo(f"cd {config.target_dir}")
    typer.echo("npm run dev")


def main():
    """Console-script entry point."""
    # The tree preview uses Unicode box-drawing characters; Windows consoles
    # commonly default to a non-UTF-8 codepage (e.g. cp1252), which raises
    # UnicodeEncodeError on print() otherwise.
    for stream in (sys.stdout, sys.stderr):
        if getattr(stream, "encoding", None) and stream.encoding.lower() != "utf-8":
            stream.reconfigure(encoding="utf-8", errors="replace")
    app()


if __name__ == "__main__":
    main()
