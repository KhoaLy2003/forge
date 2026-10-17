from pathlib import Path

import jinja2
import pytest

from core.renderer import TargetExistsError, render_tree, resolve_tree


def make_template(tmp_path: Path) -> Path:
    template_dir = tmp_path / "template"
    (template_dir / "{{ group_id }}").mkdir(parents=True)
    (template_dir / "{{ group_id }}" / "hello.txt").write_text(
        "Hello {{ name }}!", encoding="utf-8"
    )
    (template_dir / "static.txt").write_text("no variables here", encoding="utf-8")
    return template_dir


def test_resolve_tree_renders_names_without_writing(tmp_path):
    template_dir = make_template(tmp_path)
    context = {"group_id": "acme", "name": "World"}

    result = resolve_tree(template_dir, context)

    assert result == sorted(
        [Path("acme/hello.txt"), Path("static.txt")]
    )
    assert not (tmp_path / "out").exists()


def test_render_tree_writes_rendered_names_and_contents(tmp_path):
    template_dir = make_template(tmp_path)
    target_dir = tmp_path / "out"
    context = {"group_id": "acme", "name": "World"}

    render_tree(template_dir, target_dir, context)

    rendered_file = target_dir / "acme" / "hello.txt"
    assert rendered_file.read_text(encoding="utf-8") == "Hello World!"
    assert (target_dir / "static.txt").read_text(encoding="utf-8") == "no variables here"


def test_render_tree_supports_slash_producing_directory_tokens(tmp_path):
    template_dir = tmp_path / "template2"
    (template_dir / "src" / "{{ package_path }}").mkdir(parents=True)
    (template_dir / "src" / "{{ package_path }}" / "App.java").write_text(
        "package {{ base_package }};", encoding="utf-8"
    )
    target_dir = tmp_path / "out2"
    context = {"package_path": "com/example/demo", "base_package": "com.example.demo"}

    render_tree(template_dir, target_dir, context)

    written = target_dir / "src" / "com" / "example" / "demo" / "App.java"
    assert written.read_text(encoding="utf-8") == "package com.example.demo;"


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
        render_tree(template_dir, target_dir, {"group_id": "acme", "name": "World"})

    assert list(target_dir.iterdir()) == []


def make_exclude_template(tmp_path: Path) -> Path:
    template_dir = tmp_path / "exclude_template"
    template_dir.mkdir()
    (template_dir / "keep.txt").write_text("keep", encoding="utf-8")
    (template_dir / "drop").mkdir()
    (template_dir / "drop" / "nested.txt").write_text("drop", encoding="utf-8")
    return template_dir


def test_resolve_tree_drops_paths_matching_excluded_pattern(tmp_path):
    template_dir = make_exclude_template(tmp_path)

    result = resolve_tree(template_dir, {}, excluded=("drop/*",))

    assert result == [Path("keep.txt")]


def test_render_tree_does_not_write_excluded_files(tmp_path):
    template_dir = make_exclude_template(tmp_path)
    target_dir = tmp_path / "out_exclude"

    render_tree(template_dir, target_dir, {}, excluded=("drop/*",))

    assert (target_dir / "keep.txt").exists()
    assert not (target_dir / "drop").exists()


def test_excluded_pattern_matches_against_unrendered_path(tmp_path):
    template_dir = tmp_path / "unrendered_template"
    (template_dir / "{{ package_path }}" / "example").mkdir(parents=True)
    (template_dir / "{{ package_path }}" / "example" / "Foo.java").write_text(
        "package {{ base_package }};", encoding="utf-8"
    )
    context = {"package_path": "com/example/demo", "base_package": "com.example.demo"}

    result = resolve_tree(
        template_dir, context, excluded=("{{ package_path }}/example/*",)
    )

    assert result == []


# --- entity fan-out -------------------------------------------------------------------------


def make_entity_slice(tmp_path: Path, name: str = "entity_slice") -> Path:
    slice_dir = tmp_path / name
    (slice_dir / "{{ entity.package }}").mkdir(parents=True)
    (slice_dir / "{{ entity.package }}" / "{{ entity.name }}.txt").write_text(
        "class {{ entity.name }} in {{ project }}", encoding="utf-8"
    )
    return slice_dir


def _entities(*names):
    from types import SimpleNamespace

    return [SimpleNamespace(name=n, package=n.lower()) for n in names]


def test_no_entities_output_equals_call_without_entities_dir(tmp_path):
    template_dir = make_template(tmp_path)
    slice_dir = make_entity_slice(tmp_path)
    context = {"group_id": "acme", "name": "World", "has_entities": False, "entities": []}

    assert resolve_tree(template_dir, context, entities_dir=slice_dir) == resolve_tree(template_dir, context)
    empty = {"group_id": "acme", "name": "World", "has_entities": True, "entities": []}
    assert resolve_tree(template_dir, empty, entities_dir=slice_dir) == resolve_tree(template_dir, empty)


def test_missing_has_entities_key_is_treated_as_false(tmp_path):
    template_dir = make_template(tmp_path)
    slice_dir = make_entity_slice(tmp_path)
    context = {"group_id": "acme", "name": "World"}

    assert resolve_tree(template_dir, context, entities_dir=slice_dir) == resolve_tree(template_dir, context)


def test_entities_dir_none_ignores_entities(tmp_path):
    template_dir = make_template(tmp_path)
    context = {
        "group_id": "acme", "name": "World", "has_entities": True,
        "entities": _entities("Customer"),
    }

    assert resolve_tree(template_dir, context, entities_dir=None) == resolve_tree(template_dir, context)


def test_missing_entities_dir_is_tolerated(tmp_path):
    template_dir = make_template(tmp_path)
    context = {
        "group_id": "acme", "name": "World", "has_entities": True,
        "entities": _entities("Customer"),
    }

    result = resolve_tree(template_dir, context, entities_dir=tmp_path / "nope")

    assert result == resolve_tree(template_dir, context)


def test_three_entities_render_three_slices_with_entity_context(tmp_path):
    template_dir = make_template(tmp_path)
    slice_dir = make_entity_slice(tmp_path)
    context = {
        "group_id": "acme", "name": "World", "project": "demo", "has_entities": True,
        "entities": _entities("Customer", "Order", "Item"),
    }
    target_dir = tmp_path / "out_entities"

    render_tree(template_dir, target_dir, context, entities_dir=slice_dir)

    for n in ("Customer", "Order", "Item"):
        text = (target_dir / n.lower() / f"{n}.txt").read_text(encoding="utf-8")
        assert text == f"class {n} in demo"
    assert (target_dir / "acme" / "hello.txt").read_text(encoding="utf-8") == "Hello World!"


def test_resolve_tree_and_render_tree_agree_with_entities(tmp_path):
    template_dir = make_template(tmp_path)
    slice_dir = make_entity_slice(tmp_path)
    context = {
        "group_id": "acme", "name": "World", "project": "demo", "has_entities": True,
        "entities": _entities("Customer", "Order"),
    }
    target_dir = tmp_path / "out_agree"

    resolved = resolve_tree(template_dir, context, entities_dir=slice_dir)
    render_tree(template_dir, target_dir, context, entities_dir=slice_dir)

    written = sorted(p.relative_to(target_dir) for p in target_dir.rglob("*") if p.is_file())
    assert resolved == written == sorted(resolved)
    assert len(resolved) == 4


def test_collision_between_entities_raises_value_error_naming_path_and_entities(tmp_path):
    template_dir = make_template(tmp_path)
    slice_dir = tmp_path / "collide_slice"
    slice_dir.mkdir()
    (slice_dir / "fixed.txt").write_text("x", encoding="utf-8")
    context = {
        "group_id": "acme", "name": "World", "has_entities": True,
        "entities": _entities("Customer", "Order"),
    }

    for call in (
        lambda: resolve_tree(template_dir, context, entities_dir=slice_dir),
        lambda: render_tree(template_dir, tmp_path / "out_collide", context, entities_dir=slice_dir),
    ):
        with pytest.raises(ValueError) as exc:
            call()
        message = str(exc.value)
        assert "fixed.txt" in message and "Customer" in message and "Order" in message
    assert not (tmp_path / "out_collide").exists()


def test_collision_between_shared_and_entity_raises_value_error(tmp_path):
    template_dir = make_template(tmp_path)
    slice_dir = tmp_path / "collide_slice2"
    slice_dir.mkdir()
    (slice_dir / "static.txt").write_text("x", encoding="utf-8")
    context = {
        "group_id": "acme", "name": "World", "has_entities": True,
        "entities": _entities("Customer"),
    }

    with pytest.raises(ValueError, match="static.txt"):
        resolve_tree(template_dir, context, entities_dir=slice_dir)


# --- join-table fan-out and empty names ------------------------------------------------------


def make_join_slice(tmp_path: Path, name: str = "join_slice") -> Path:
    slice_dir = tmp_path / name
    slice_dir.mkdir()
    (slice_dir / "{{ join_table.name }}.sql").write_text(
        "join {{ join_table.name }} in {{ project }}", encoding="utf-8"
    )
    return slice_dir


def _joins(*names):
    from types import SimpleNamespace

    return [SimpleNamespace(name=n) for n in names]


def test_join_dir_renders_once_per_join_table(tmp_path):
    template_dir = make_template(tmp_path)
    join_dir = make_join_slice(tmp_path)
    context = {
        "group_id": "acme", "name": "World", "project": "demo", "has_entities": True,
        "entities": [], "join_tables": _joins("a_b", "c_d"),
    }
    target_dir = tmp_path / "out_join"

    resolved = resolve_tree(template_dir, context, join_dir=join_dir)
    render_tree(template_dir, target_dir, context, join_dir=join_dir)

    assert (target_dir / "a_b.sql").read_text(encoding="utf-8") == "join a_b in demo"
    assert (target_dir / "c_d.sql").read_text(encoding="utf-8") == "join c_d in demo"
    written = sorted(p.relative_to(target_dir) for p in target_dir.rglob("*") if p.is_file())
    assert resolved == written
    assert len(resolved) == 4


def test_join_dir_is_ignored_without_entities_or_without_the_dir(tmp_path):
    template_dir = make_template(tmp_path)
    join_dir = make_join_slice(tmp_path)
    off = {"group_id": "acme", "name": "World", "has_entities": False, "join_tables": _joins("a_b")}
    on = {"group_id": "acme", "name": "World", "has_entities": True, "join_tables": _joins("a_b")}

    assert resolve_tree(template_dir, off, join_dir=join_dir) == resolve_tree(template_dir, off)
    assert resolve_tree(template_dir, on, join_dir=None) == resolve_tree(template_dir, on)
    assert resolve_tree(template_dir, on, join_dir=tmp_path / "nope") == resolve_tree(template_dir, on)


def test_join_table_collision_raises_value_error(tmp_path):
    template_dir = make_template(tmp_path)
    join_dir = tmp_path / "join_collide"
    join_dir.mkdir()
    (join_dir / "fixed.txt").write_text("x", encoding="utf-8")
    context = {
        "group_id": "acme", "name": "World", "has_entities": True,
        "entities": [], "join_tables": _joins("a_b", "c_d"),
    }

    with pytest.raises(ValueError, match="fixed.txt") as exc:
        resolve_tree(template_dir, context, join_dir=join_dir)
    assert "a_b" in str(exc.value) and "c_d" in str(exc.value)


def test_file_whose_name_renders_empty_is_not_emitted(tmp_path):
    template_dir = make_template(tmp_path)
    (template_dir / "{{ optional if optional else '' }}").write_text("only sometimes", encoding="utf-8")
    base = {"group_id": "acme", "name": "World"}

    without = resolve_tree(template_dir, {**base, "optional": None})
    with_it = resolve_tree(template_dir, {**base, "optional": "extra.txt"})

    assert Path("extra.txt") in with_it
    assert len(with_it) == len(without) + 1
    target = tmp_path / "out_empty"
    render_tree(template_dir, target, {**base, "optional": None})
    assert sorted(p.name for p in target.rglob("*") if p.is_file()) == ["hello.txt", "static.txt"]
