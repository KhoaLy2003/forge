from pathlib import Path

import pytest

from core.templates import discover_templates

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def test_every_template_directory_has_a_manifest():
    template_dirs = {p.name for p in TEMPLATES_DIR.iterdir() if p.is_dir() and not p.name.startswith("_")}
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


def test_dynamic_excludes_empty_without_entities():
    from core.templates import dynamic_excludes

    assert dynamic_excludes({}) == ()
    assert dynamic_excludes({"has_entities": False}) == ()


def test_dynamic_excludes_with_entities_remove_exactly_the_example_slice():
    from core.templates import SHARED_DIR, dynamic_excludes, filter_excluded_paths

    context = {"has_entities": True, "package_path": "com/example/demo", "app_class_name": "Demo"}
    excludes = dynamic_excludes(context)
    assert excludes
    shared = [p.relative_to(SHARED_DIR) for p in SHARED_DIR.rglob("*") if p.is_file()]
    rendered = [
        Path(*[part.replace("{{ package_path }}", "com/example/demo").replace("{{ app_class_name }}", "Demo") for part in p.parts])
        for p in shared
    ]
    removed = set(rendered) - set(filter_excluded_paths(rendered, excludes, context))
    expected = {
        p for p in rendered
        if p.as_posix().startswith(("src/main/java/com/example/demo/example/", "src/test/java/com/example/demo/example/"))
    } | {Path("src/main/resources/db/changelog/001-create-example-table.sql")}
    assert removed == expected
    assert len(removed) >= 10


def test_dynamic_excludes_work_in_resolve_tree_on_real_shared_tree():
    from core.renderer import resolve_tree
    from core.templates import SHARED_DIR, dynamic_excludes

    from core.config_schema import ForgeConfig

    cfg = ForgeConfig(project_name="demo", target_path=Path("."), group_id="com.example", artifact_id="demo")
    ctx = {**cfg.template_context(), "has_entities": True, "entities": []}
    with_ex = resolve_tree(SHARED_DIR, ctx)
    without = resolve_tree(SHARED_DIR, ctx, excluded=dynamic_excludes(ctx))
    marker = "com/example/demo/example/"
    assert any(marker in p.as_posix() for p in with_ex)
    assert not any(marker in p.as_posix() for p in without)
    assert Path("src/main/resources/db/changelog/001-create-example-table.sql") not in without
