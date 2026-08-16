from pathlib import Path

import jinja2
import pytest

from forge_web.core.renderer import TargetExistsError, render_tree, resolve_tree


def make_template(tmp_path: Path) -> Path:
    template_dir = tmp_path / "template"
    (template_dir / "{{ project_name }}").mkdir(parents=True)
    (template_dir / "{{ project_name }}" / "hello.txt").write_text(
        "Hello {{ name }}!", encoding="utf-8"
    )
    (template_dir / "static.txt").write_text("no variables here", encoding="utf-8")
    return template_dir


def test_resolve_tree_renders_names_without_writing(tmp_path):
    template_dir = make_template(tmp_path)
    context = {"project_name": "acme", "name": "World"}

    result = resolve_tree(template_dir, context)

    assert result == sorted(
        [Path("acme/hello.txt"), Path("static.txt")]
    )
    assert not (tmp_path / "out").exists()


def test_render_tree_writes_rendered_names_and_contents(tmp_path):
    template_dir = make_template(tmp_path)
    target_dir = tmp_path / "out"
    context = {"project_name": "acme", "name": "World"}

    render_tree(template_dir, target_dir, context)

    rendered_file = target_dir / "acme" / "hello.txt"
    assert rendered_file.read_text(encoding="utf-8") == "Hello World!"
    assert (target_dir / "static.txt").read_text(encoding="utf-8") == "no variables here"


def test_render_tree_supports_slash_producing_directory_tokens(tmp_path):
    template_dir = tmp_path / "template2"
    (template_dir / "src" / "{{ app_display_name }}").mkdir(parents=True)
    (template_dir / "src" / "{{ app_display_name }}" / "App.tsx").write_text(
        "// {{ api_base_url }}", encoding="utf-8"
    )
    target_dir = tmp_path / "out2"
    context = {"app_display_name": "Acme App", "api_base_url": "http://localhost/api"}

    render_tree(template_dir, target_dir, context)

    written = target_dir / "src" / "Acme App" / "App.tsx"
    assert written.read_text(encoding="utf-8") == "// http://localhost/api"


def test_render_tree_raises_on_undefined_context_variable(tmp_path):
    template_dir = tmp_path / "template3"
    template_dir.mkdir()
    (template_dir / "hello.txt").write_text(
        "Hello {{ nonexistent_variable }}!", encoding="utf-8"
    )
    target_dir = tmp_path / "out3"

    with pytest.raises(jinja2.UndefinedError):
        render_tree(template_dir, target_dir, {"name": "World"})


def test_render_tree_copies_binary_file_unchanged(tmp_path):
    template_dir = tmp_path / "template4"
    template_dir.mkdir()
    binary_content = b"\xff\xfe\x00\x01"
    (template_dir / "asset.bin").write_bytes(binary_content)
    target_dir = tmp_path / "out4"

    render_tree(template_dir, target_dir, {})

    assert (target_dir / "asset.bin").read_bytes() == binary_content


def test_render_tree_raises_if_target_exists(tmp_path):
    template_dir = make_template(tmp_path)
    target_dir = tmp_path / "out"
    target_dir.mkdir()

    with pytest.raises(TargetExistsError):
        render_tree(template_dir, target_dir, {"project_name": "acme", "name": "World"})

    assert list(target_dir.iterdir()) == []


def test_resolve_tree_drops_paths_matching_excluded_pattern(tmp_path):
    template_dir = tmp_path / "template5"
    template_dir.mkdir()
    (template_dir / "keep.txt").write_text("keep", encoding="utf-8")
    (template_dir / "drop").mkdir()
    (template_dir / "drop" / "nested.txt").write_text("drop", encoding="utf-8")

    result = resolve_tree(template_dir, {}, excluded=("drop/*",))

    assert result == [Path("keep.txt")]


def test_render_tree_does_not_write_excluded_files(tmp_path):
    template_dir = tmp_path / "template6"
    template_dir.mkdir()
    (template_dir / "keep.txt").write_text("keep", encoding="utf-8")
    (template_dir / "drop").mkdir()
    (template_dir / "drop" / "nested.txt").write_text("drop", encoding="utf-8")
    target_dir = tmp_path / "out6"

    render_tree(template_dir, target_dir, {}, excluded=("drop/*",))

    assert (target_dir / "keep.txt").exists()
    assert not (target_dir / "drop").exists()


def test_excluded_pattern_matches_against_unrendered_path(tmp_path):
    template_dir = tmp_path / "template7"
    (template_dir / "{{ package_path }}" / "example").mkdir(parents=True)
    (template_dir / "{{ package_path }}" / "example" / "Foo.java").write_text(
        "content", encoding="utf-8"
    )
    context = {"package_path": "com/example"}

    result = resolve_tree(
        template_dir, context, excluded=("{{ package_path }}/example/*",)
    )

    assert result == []
