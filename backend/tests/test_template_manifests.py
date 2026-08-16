from pathlib import Path

import pytest

from core.templates import discover_templates

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def test_every_template_directory_has_a_manifest():
    template_dirs = {p.name for p in TEMPLATES_DIR.iterdir() if p.is_dir() and p.name != "_shared"}
    assert set(discover_templates()) == template_dirs


@pytest.mark.parametrize("name", ["base-layered", "minimal"])
def test_each_exclude_pattern_matches_at_least_one_shared_file(name):
    excludes = discover_templates()[name]
    shared_files = [str(p.relative_to(TEMPLATES_DIR / "_shared").as_posix()) for p in (TEMPLATES_DIR / "_shared").rglob("*") if p.is_file()]
    import fnmatch
    for pattern in excludes:
        assert any(fnmatch.fnmatch(f, pattern) for f in shared_files), f"pattern {pattern!r} matched nothing"


def test_filter_excluded_paths_renders_pattern_placeholders_before_matching():
    from core.templates import filter_excluded_paths
    paths = [Path("src/test/java/com/example/demo/example/repository/ExampleRepositoryTest.java"), Path("keep.txt")]
    excluded = ("src/test/java/{{ package_path }}/example/repository/ExampleRepositoryTest.java",)
    result = filter_excluded_paths(paths, excluded, {"package_path": "com/example/demo"})
    assert result == [Path("keep.txt")]
