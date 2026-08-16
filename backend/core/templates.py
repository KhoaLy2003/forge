"""Template registry: discovers templates/<name>/manifest.py files and filters expected-path lists."""

import fnmatch
import importlib.util
from pathlib import Path

import jinja2

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
SHARED_DIR = TEMPLATES_DIR / "_shared"

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
