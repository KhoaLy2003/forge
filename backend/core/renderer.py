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
        if any(part == "" for part in rel_parts):
            # A name that renders to nothing means "emit no file" (e.g. an optional changelog).
            continue
        yield path, Path(*rel_parts)


def _entity_contexts(context: dict, entities_dir: Path | None) -> list[tuple[str, dict]]:
    """Return (entity name, per-entity context) pairs when the fan-out pass applies, else []."""
    if not context.get("has_entities") or entities_dir is None or not entities_dir.is_dir():
        return []
    return [
        (str(entity.name), {**context, "entity": entity})
        for entity in context.get("entities", [])
    ]


def _join_contexts(context: dict, join_dir: Path | None) -> list[tuple[str, dict]]:
    """Return (join table name, per-join-table context) pairs when the join fan-out applies, else []."""
    if not context.get("has_entities") or join_dir is None or not join_dir.is_dir():
        return []
    return [
        (str(join_table.name), {**context, "join_table": join_table})
        for join_table in context.get("join_tables", [])
    ]


def _plan(
    template_dir: Path,
    context: dict,
    excluded: tuple[str, ...],
    entities_dir: Path | None,
    join_dir: Path | None = None,
):
    """Return [(template_file, rendered_rel_path, context_for_contents)] for the whole output.

    Raises ValueError if two sources (shared tree / entity slices / join-table slices) render to the
    same path.
    """
    plan = []
    owners: dict[Path, str] = {}

    def add(source_dir: Path, ctx: dict, owner: str) -> None:
        for template_file, rel_path in _iter_rendered_files(source_dir, ctx, excluded):
            if rel_path in owners:
                raise ValueError(
                    f"Rendered path collision: {rel_path.as_posix()} produced by "
                    f"{owners[rel_path]} and {owner}"
                )
            owners[rel_path] = owner
            plan.append((template_file, rel_path, ctx))

    add(template_dir, context, "the shared template")
    for entity_name, entity_ctx in _entity_contexts(context, entities_dir):
        add(entities_dir, entity_ctx, f"entity {entity_name}")
    for join_name, join_ctx in _join_contexts(context, join_dir):
        add(join_dir, join_ctx, f"join table {join_name}")
    return plan


def resolve_tree(
    template_dir: Path,
    context: dict,
    excluded: tuple[str, ...] = (),
    entities_dir: Path | None = None,
    join_dir: Path | None = None,
) -> list[Path]:
    """Return the sorted list of rendered relative output paths, without writing anything."""
    return sorted(rel for _, rel, _ in _plan(template_dir, context, excluded, entities_dir, join_dir))


def render_tree(
    template_dir: Path,
    target_dir: Path,
    context: dict,
    excluded: tuple[str, ...] = (),
    entities_dir: Path | None = None,
    join_dir: Path | None = None,
) -> None:
    """Render template_dir (plus one entities_dir slice per entity and one join_dir slice per
    many-to-many join table) into target_dir."""
    if target_dir.exists():
        raise TargetExistsError(f"Target directory already exists: {target_dir}")

    env = _ENV
    for template_file, rel_path, ctx in _plan(
        template_dir, context, excluded, entities_dir, join_dir
    ):
        out_path = target_dir / rel_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            content = template_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            out_path.write_bytes(template_file.read_bytes())
            continue
        rendered = env.from_string(content).render(**ctx)
        out_path.write_text(rendered, encoding="utf-8")
