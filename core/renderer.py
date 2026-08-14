"""Custom Jinja2 tree renderer: applies templating to both file/folder names and file contents."""

from pathlib import Path

import jinja2

_ENV = jinja2.Environment(undefined=jinja2.StrictUndefined)


class TargetExistsError(Exception):
    """Raised when render_tree's target directory already exists."""

    pass


def _iter_rendered_files(template_dir: Path, context: dict):
    """Yield (template_file_path, rendered_relative_path) for every file under template_dir."""
    env = _ENV
    for path in sorted(template_dir.rglob("*")):
        if path.is_dir():
            continue
        rel_parts = [
            env.from_string(part).render(**context)
            if ("{{" in part or "{%" in part)
            else part
            for part in path.relative_to(template_dir).parts
        ]
        yield path, Path(*rel_parts)


def resolve_tree(template_dir: Path, context: dict) -> list[Path]:
    """Return the sorted list of rendered relative output paths, without writing anything."""
    return sorted(rel for _, rel in _iter_rendered_files(template_dir, context))


def render_tree(template_dir: Path, target_dir: Path, context: dict) -> None:
    """Render template_dir's file/folder names and contents into target_dir."""
    if target_dir.exists():
        raise TargetExistsError(f"Target directory already exists: {target_dir}")

    env = _ENV
    for template_file, rel_path in _iter_rendered_files(template_dir, context):
        out_path = target_dir / rel_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            content = template_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            out_path.write_bytes(template_file.read_bytes())
            continue
        rendered = env.from_string(content).render(**context)
        out_path.write_text(rendered, encoding="utf-8")
