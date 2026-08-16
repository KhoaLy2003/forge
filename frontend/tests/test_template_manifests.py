import fnmatch
from pathlib import Path

import pytest

from forge_web.core.templates import discover_templates

TEMPLATES_DIR = Path(__file__).parent.parent / "forge_web" / "templates"


def test_every_template_directory_has_a_manifest():
    template_dirs = {p.name for p in TEMPLATES_DIR.iterdir() if p.is_dir() and p.name != "_shared"}
    assert set(discover_templates()) == template_dirs


@pytest.mark.parametrize("name", ["base", "minimal"])
def test_each_exclude_pattern_matches_at_least_one_shared_file(name):
    excludes = discover_templates()[name]
    shared_files = [
        str(p.relative_to(TEMPLATES_DIR / "_shared").as_posix())
        for p in (TEMPLATES_DIR / "_shared").rglob("*")
        if p.is_file()
    ]
    for pattern in excludes:
        assert any(fnmatch.fnmatch(f, pattern) for f in shared_files), f"pattern {pattern!r} matched nothing"


def test_filter_excluded_paths_drops_matching_paths():
    from forge_web.core.templates import filter_excluded_paths

    paths = [Path("src/lib/api-client/index.ts"), Path("keep.txt")]
    excluded = ("src/lib/api-client/*",)
    result = filter_excluded_paths(paths, excluded, {})
    assert result == [Path("keep.txt")]
