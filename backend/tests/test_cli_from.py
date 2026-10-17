"""Tests for `forge new --from forge.yaml` and the wizard's entity step / forge.yaml saving."""

from pathlib import Path

import yaml
from typer.testing import CliRunner

import cli
from core.entity_spec import load_forge_yaml
from core.validator import ValidationResult

runner = CliRunner()

CUSTOMER = {
    "Customer": {"fields": {"name": {"type": "string", "length": 100, "required": True}}},
}


def _write_yaml(path, data):
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _full_file(tmp_path, **extra):
    data = {
        "project_name": "demo-service",
        "target_path": str(tmp_path),
        "group_id": "com.example",
        "artifact_id": "demo-service",
        **extra,
    }
    return _write_yaml(tmp_path / "forge.yaml", data)


def _stub_compile(monkeypatch):
    monkeypatch.setattr(cli, "run_compile", lambda target_dir: ValidationResult(True, "ok"))


def _spy_context(monkeypatch, seen):
    """Capture the render context and stop before anything is written (answer 'n' at the confirm)."""

    def spy_resolve(root, context, **kwargs):
        seen["context"] = context
        return [Path("pom.xml")]

    monkeypatch.setattr(cli, "resolve_tree", spy_resolve)


# ----------------------------------------------------------------------------- --from


def test_from_file_supplies_all_parameters_without_prompting(tmp_path, monkeypatch):
    _stub_compile(monkeypatch)
    out = tmp_path / "out"
    out.mkdir()
    file = _full_file(tmp_path, target_path=str(out))

    result = runner.invoke(cli.app, ["new", "--from", str(file)], input="y\n")

    assert result.exit_code == 0, result.output
    assert (out / "demo-service" / "pom.xml").exists()
    assert "Add an entity?" not in result.output


def test_cli_flag_overrides_file_value(tmp_path, monkeypatch):
    _stub_compile(monkeypatch)
    file = _full_file(tmp_path)

    result = runner.invoke(cli.app, ["new", "--from", str(file), "--name", "other-service"], input="y\n")

    assert result.exit_code == 0, result.output
    assert (tmp_path / "other-service" / "pom.xml").exists()
    assert not (tmp_path / "demo-service").exists()


def test_file_template_wins_over_the_default(tmp_path, monkeypatch):
    _stub_compile(monkeypatch)
    file = _full_file(tmp_path, template="minimal")

    result = runner.invoke(cli.app, ["new", "--from", str(file)], input="y\n")

    assert result.exit_code == 0, result.output
    assert not (tmp_path / "demo-service" / "src/main/resources/db/changelog").exists()


def test_explicit_template_flag_wins_over_file_template(tmp_path, monkeypatch):
    _stub_compile(monkeypatch)
    file = _full_file(tmp_path, template="minimal")

    result = runner.invoke(
        cli.app, ["new", "--from", str(file), "--template", "base-layered"], input="y\n"
    )

    assert result.exit_code == 0, result.output
    assert (tmp_path / "demo-service" / "src/main/resources/db/changelog").exists()


def test_explicit_flag_equal_to_the_default_still_wins_over_file(tmp_path, monkeypatch):
    """Whether the flag was given is decided by Click's parameter source, not by comparing values."""
    seen = {}
    _spy_context(monkeypatch, seen)
    file = _full_file(tmp_path, template="minimal")

    result = runner.invoke(
        cli.app, ["new", "--from", str(file), "--template", "base-layered"], input="n\n"
    )

    assert result.exit_code == 0, result.output
    assert seen["context"]["template"] == "base-layered"


def test_file_entities_reach_the_render_context(tmp_path, monkeypatch):
    seen = {}
    _spy_context(monkeypatch, seen)
    file = _full_file(tmp_path, entities=CUSTOMER)

    result = runner.invoke(cli.app, ["new", "--from", str(file)], input="n\n")

    assert result.exit_code == 0, result.output
    assert seen["context"]["has_entities"] is True
    assert [e.name for e in seen["context"]["entities"]] == ["Customer"]
    assert "Add an entity?" not in result.output


def test_file_entities_with_minimal_template_is_an_error(tmp_path):
    file = _full_file(tmp_path, template="minimal", entities=CUSTOMER)

    result = runner.invoke(cli.app, ["new", "--from", str(file)], input="y\n")

    assert result.exit_code == 1
    assert "base-layered" in result.output
    assert not (tmp_path / "demo-service").exists()


def test_explicit_minimal_flag_with_file_entities_is_an_error(tmp_path):
    file = _full_file(tmp_path, entities=CUSTOMER)

    result = runner.invoke(cli.app, ["new", "--from", str(file), "--template", "minimal"])

    assert result.exit_code == 1
    assert not (tmp_path / "demo-service").exists()


def test_missing_from_file_reports_path_and_writes_nothing(tmp_path):
    missing = tmp_path / "nope.yaml"

    result = runner.invoke(
        cli.app, ["new", "--from", str(missing), "--name", "demo-service", "--path", str(tmp_path)]
    )

    assert result.exit_code == 1
    assert str(missing) in result.output
    assert not (tmp_path / "demo-service").exists()


def test_invalid_yaml_reports_path_and_exits_1(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("entities: [unclosed\n", encoding="utf-8")

    result = runner.invoke(cli.app, ["new", "--from", str(bad)])

    assert result.exit_code == 1
    assert str(bad) in result.output


def test_invalid_entity_set_reports_all_messages_and_writes_nothing(tmp_path):
    file = _full_file(
        tmp_path,
        entities={
            "Order": {"fields": {"total": {"type": "int"}}},
            "Product": {"relations": {"owner": {"type": "many-to-one", "target": "Ghost"}}},
        },
    )

    result = runner.invoke(cli.app, ["new", "--from", str(file)], input="y\n")

    assert result.exit_code == 1
    assert "reserved SQL word" in result.output
    assert "Ghost" in result.output
    assert not (tmp_path / "demo-service").exists()


def test_unknown_key_in_file_exits_1_with_path(tmp_path):
    file = _full_file(tmp_path, colour="blue")

    result = runner.invoke(cli.app, ["new", "--from", str(file)])

    assert result.exit_code == 1
    assert str(file) in result.output and "colour" in result.output


# ----------------------------------------------------------------------------- regressions


def test_flag_complete_invocation_never_prompts_for_entities(tmp_path, monkeypatch):
    """Regression (modelled on the --template one): a fully flag-complete run answers only the confirm
    prompt. A new entity prompt would consume it or hit EOF and break CI and scripts."""
    _stub_compile(monkeypatch)

    result = runner.invoke(
        cli.app,
        ["new", "--name", "demo-service", "--path", str(tmp_path),
         "--group-id", "com.example", "--artifact-id", "demo-service", "--template", "base-layered"],
        input="y\n",
    )

    assert result.exit_code == 0, result.output
    assert "Add an entity?" not in result.output
    assert "forge.yaml" not in result.output


def test_flag_complete_invocation_omitting_template_never_prompts_for_entities(tmp_path, monkeypatch):
    _stub_compile(monkeypatch)

    result = runner.invoke(
        cli.app,
        ["new", "--name", "demo-service", "--path", str(tmp_path),
         "--group-id", "com.example", "--artifact-id", "demo-service"],
        input="y\n",
    )

    assert result.exit_code == 0, result.output
    assert "Add an entity?" not in result.output
    assert "forge.yaml" not in result.output


# ----------------------------------------------------------------------------- wizard entity step


def _interactive_input(tmp_path, *entity_answers, confirm="n"):
    lines = ["demo-service", str(tmp_path), "com.example", "demo-service", *entity_answers, confirm]
    return "\n".join(lines) + "\n"


def test_interactive_run_offers_entity_step(tmp_path, monkeypatch):
    seen = {}
    _spy_context(monkeypatch, seen)
    answers = _interactive_input(tmp_path, "y", "Customer", "y", "name", "string", "100", "y", "n", "n")

    result = runner.invoke(cli.app, ["new"], input=answers)

    assert result.exit_code == 0, result.output
    assert "Add an entity?" in result.output
    assert [e.name for e in seen["context"]["entities"]] == ["Customer"]


def test_interactive_run_declining_entities_keeps_the_example_slice(tmp_path, monkeypatch):
    seen = {}
    _spy_context(monkeypatch, seen)

    result = runner.invoke(cli.app, ["new"], input=_interactive_input(tmp_path, "n"))

    assert result.exit_code == 0, result.output
    assert seen["context"]["has_entities"] is False
    assert "Save the model" not in result.output


def test_interactive_run_with_minimal_template_skips_entity_step(tmp_path, monkeypatch):
    seen = {}
    _spy_context(monkeypatch, seen)

    result = runner.invoke(cli.app, ["new", "--template", "minimal"], input=_interactive_input(tmp_path))

    assert result.exit_code == 0, result.output
    assert "Add an entity?" not in result.output


def test_interactive_run_with_file_entities_skips_entity_step(tmp_path, monkeypatch):
    seen = {}
    _spy_context(monkeypatch, seen)
    file = _write_yaml(tmp_path / "m.yaml", {"entities": CUSTOMER})

    result = runner.invoke(cli.app, ["new", "--from", str(file)], input=_interactive_input(tmp_path))

    assert result.exit_code == 0, result.output
    assert "Add an entity?" not in result.output
    assert [e.name for e in seen["context"]["entities"]] == ["Customer"]


def _stub_generation(monkeypatch):
    """Stand in for rendering and validation so saving can be tested independently of the entity templates."""

    def fake_render(root, target, context, **kwargs):
        Path(target).mkdir(parents=True)

    monkeypatch.setattr(cli, "render_tree", fake_render)
    monkeypatch.setattr(cli, "resolve_tree", lambda *a, **k: [Path("pom.xml")])
    monkeypatch.setattr(cli, "check_structure", lambda *a, **k: ValidationResult(True, "ok"))
    monkeypatch.setattr(cli, "check_observability", lambda *a, **k: ValidationResult(True, "ok"))
    monkeypatch.setattr(cli, "run_compile", lambda target_dir: ValidationResult(True, "ok"))


def test_interactive_run_saves_forge_yaml_into_the_generated_project(tmp_path, monkeypatch):
    _stub_generation(monkeypatch)
    answers = _interactive_input(
        tmp_path, "y", "Customer", "y", "name", "string", "100", "y", "n", "n", confirm="y\ny"
    )

    result = runner.invoke(cli.app, ["new"], input=answers)

    assert result.exit_code == 0, result.output
    assert "Save the model as forge.yaml?" in result.output
    saved = load_forge_yaml(tmp_path / "demo-service" / "forge.yaml")
    assert list(saved.entities) == ["Customer"]
    assert saved.entities["Customer"].fields["name"].length == 100
    assert saved.project_name == "demo-service"


def test_interactive_run_can_decline_saving_forge_yaml(tmp_path, monkeypatch):
    _stub_generation(monkeypatch)
    answers = _interactive_input(tmp_path, "y", "Customer", "n", "n", confirm="y\nn")

    result = runner.invoke(cli.app, ["new"], input=answers)

    assert result.exit_code == 0, result.output
    assert not (tmp_path / "demo-service" / "forge.yaml").exists()


def test_forge_yaml_is_not_offered_when_generation_fails(tmp_path, monkeypatch):
    _stub_generation(monkeypatch)
    monkeypatch.setattr(
        cli, "run_compile", lambda target_dir: ValidationResult(False, "mvn compile failed", "boom")
    )
    answers = _interactive_input(tmp_path, "y", "Customer", "n", "n", confirm="y\nn")

    result = runner.invoke(cli.app, ["new"], input=answers)

    assert result.exit_code == 1
    assert "Save the model" not in result.output
