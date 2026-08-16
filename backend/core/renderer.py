"""Custom Jinja2 tree renderer: applies templating to both file/folder names and file contents."""

import fnmatch
from pathlib import Path

import jinja2

_ENV = jinja2.Environment(undefined=jinja2.StrictUndefined, keep_trailing_newline=True)


class TargetExistsError(Exception):
    """Raised when render_tree's target directory already exists."""

    pass


def _is_excluded(rel_path: Path, excluded: tuple[str, ...]) -> bool:
    rel_posix = rel_path.as_posix()
    return any(fnmatch.fnmatch(rel_posix, pattern) for pattern in excluded)


def _iter_rendered_files(template_dir: Path, context: dict, excluded: tuple[str, ...] = ()):
    """Yield (template_file_path, rendered_relative_path) for every file under template_dir."""
    env = _ENV
    for path in sorted(template_dir.rglob("*")):
        if path.is_dir():
            continue
        rel_path = path.relative_to(template_dir)
        if _is_excluded(rel_path, excluded):
            continue
        rel_parts = [
            env.from_string(part).render(**context)
            if ("{{" in part or "{%" in part)
            else part
            for part in rel_path.parts
        ]
        yield path, Path(*rel_parts)


def resolve_tree(template_dir: Path, context: dict, excluded: tuple[str, ...] = ()) -> list[Path]:
    """Return the sorted list of rendered relative output paths, without writing anything."""
    return sorted(rel for _, rel in _iter_rendered_files(template_dir, context, excluded))


def render_tree(
    template_dir: Path, target_dir: Path, context: dict, excluded: tuple[str, ...] = ()
) -> None:
    """Render template_dir's file/folder names and contents into target_dir."""
    if target_dir.exists():
        raise TargetExistsError(f"Target directory already exists: {target_dir}")

    env = _ENV
    for template_file, rel_path in _iter_rendered_files(template_dir, context, excluded):
        out_path = target_dir / rel_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            content = template_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            out_path.write_bytes(template_file.read_bytes())
            continue
        rendered = env.from_string(content).render(**context)
        out_path.write_text(rendered, encoding="utf-8")
