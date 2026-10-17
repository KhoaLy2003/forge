"""Template registry: discovers templates/<name>/manifest.py files and filters expected-path lists."""

import fnmatch
import importlib.util
from pathlib import Path

import jinja2

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
SHARED_DIR = TEMPLATES_DIR / "_shared"
ENTITY_DIR = TEMPLATES_DIR / "_entity"
JOIN_DIR = TEMPLATES_DIR / "_join"

# The single shared file that holds deferred FK constraints; its name renders to "" (= not emitted) when
# the context has no constraints changelog.
CONSTRAINTS_CHANGELOG_TEMPLATE = (
    "src/main/resources/db/changelog/{{ constraints_changelog_file if constraints_changelog_file is defined and constraints_changelog_file else '' }}"
)

_ENV = jinja2.Environment(undefined=jinja2.StrictUndefined)


def _load_excludes(manifest_path: Path) -> tuple[str, ...]:
    spec = importlib.util.spec_from_file_location(f"manifest_{manifest_path.parent.name}", manifest_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return tuple(module.EXCLUDES)


def discover_templates() -> dict[str, tuple[str, ...]]:
    """Return {template_name: excludes} for every templates/<name>/manifest.py (excluding _shared)."""
    return {
        manifest_path.parent.name: _load_excludes(manifest_path)
        for manifest_path in sorted(TEMPLATES_DIR.glob("*/manifest.py"))
    }


def dynamic_excludes(context: dict) -> tuple[str, ...]:
    """Context-dependent excludes: with entities, the Example slice (and the constraints changelog when there are
    no deferred FKs); without entities, none."""
    if not context.get("has_entities"):
        # Nothing to add: without entities the constraints file's name renders empty and the renderer
        # skips it, so existing callers that pass no dynamic excludes behave identically.
        return ()
    excludes: tuple[str, ...] = (
        "src/main/java/{{ package_path }}/example/*",
        "src/test/java/{{ package_path }}/example/*",
        "src/main/resources/db/changelog/001-create-example-table.sql",
    )
    if not context.get("constraints_changelog_file"):
        excludes += (CONSTRAINTS_CHANGELOG_TEMPLATE,)
    return excludes


def filter_excluded_paths(paths: list[Path], excluded: tuple[str, ...], context: dict) -> list[Path]:
    """Drop any path matching a rendered exclude pattern; for filtering expected-structural-path lists."""
    rendered_patterns = [
        _ENV.from_string(pattern).render(**context) if ("{{" in pattern or "{%" in pattern) else pattern
        for pattern in excluded
    ]
    return [
        path for path in paths
        if not any(fnmatch.fnmatch(path.as_posix(), pat) for pat in rendered_patterns)
    ]
