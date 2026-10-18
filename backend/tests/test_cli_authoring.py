"""Tests for the authoring aids: `forge schema`, `validate-model`, `preview`, and the in-memory renderer."""

import json
from pathlib import Path

import jsonschema
import pytest
import yaml
from typer.testing import CliRunner

import cli
from core.generation import build_plan, preview_config
from core.entity_spec import load_forge_yaml
from core.renderer import render_files, render_tree, resolve_tree
from core.schema_export import forge_yaml_schema
from core.templates import ENTITY_DIR, JOIN_DIR, SHARED_DIR

runner = CliRunner()
FIXTURE = Path(__file__).parent / "fixtures" / "entities.forge.yaml"


def _fixture_data():
    return yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))


def _plan():
    config = preview_config(load_forge_yaml(FIXTURE))
    context, excluded = build_plan(config)
    kwargs = dict(excluded=excluded, entities_dir=ENTITY_DIR, join_dir=JOIN_DIR)
    return context, kwargs


def test_render_files_matches_resolve_tree_and_render_tree(tmp_path):
    context, kwargs = _plan()
    files = render_files(SHARED_DIR, context, **kwargs)
    assert list(files) == resolve_tree(SHARED_DIR, context, **kwargs)
    render_tree(SHARED_DIR, tmp_path / "out", context, **kwargs)
    assert files[Path("pom.xml")] == (tmp_path / "out" / "pom.xml").read_text(encoding="utf-8")


def test_schema_accepts_fixture_and_empty_entity_body():
    schema = forge_yaml_schema()
    jsonschema.validate(_fixture_data(), schema)
    jsonschema.validate({"entities": {"Tag": None}}, schema)
    assert "name" not in schema["$defs"]["EntitySpec"]["properties"]


def test_schema_rejects_unknown_field_type():
    data = _fixture_data()
    data["entities"]["Customer"]["fields"]["name"]["type"] = "strng"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(data, forge_yaml_schema())


def test_schema_command_prints_and_writes(tmp_path):
    result = runner.invoke(cli.app, ["schema"])
    assert result.exit_code == 0
    assert json.loads(result.output)["title"] == "forge.yaml"
    out = tmp_path / "schema.json"
    result = runner.invoke(cli.app, ["schema", "--output", str(out)])
    assert result.exit_code == 0 and f"Wrote {out}" in result.output
    assert json.loads(out.read_text(encoding="utf-8"))["title"] == "forge.yaml"


def test_validate_model_lists_changelog_in_order():
    result = runner.invoke(cli.app, ["validate-model", str(FIXTURE)])
    assert result.exit_code == 0
    assert "OK:" in result.output
    context, _ = _plan()
    positions = [result.output.index(name) for name in context["changelog_files"]]
    assert positions == sorted(positions)


def test_validate_model_reports_bad_type_with_path(tmp_path):
    data = {"entities": {"Thing": {"fields": {"x": {"type": "strng"}}}}}
    bad = tmp_path / "bad.yaml"
    bad.write_text(yaml.safe_dump(data), encoding="utf-8")
    result = runner.invoke(cli.app, ["validate-model", str(bad)])
    assert result.exit_code == 1
    assert str(bad) in result.output and "strng" in result.output


def test_validate_model_without_entities(tmp_path):
    empty = tmp_path / "empty.yaml"
    empty.write_text("template: base-layered\n", encoding="utf-8")
    result = runner.invoke(cli.app, ["validate-model", str(empty)])
    assert result.exit_code == 0
    assert "no entities" in result.output


def test_preview_lists_files_and_prints_one(tmp_path):
    listing = runner.invoke(cli.app, ["preview", "--from", str(FIXTURE)])
    assert listing.exit_code == 0 and "pom.xml" in listing.output
    one = runner.invoke(cli.app, ["preview", "--from", str(FIXTURE), "--file", "pom.xml"])
    assert one.exit_code == 0 and "<artifactId>" in one.output
    missing = runner.invoke(cli.app, ["preview", "--from", str(FIXTURE), "--file", "nope.txt"])
    assert missing.exit_code == 1
    assert "no such file in the generated project: nope.txt" in missing.output
    assert not list(tmp_path.iterdir())
