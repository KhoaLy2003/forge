"""Tests for the file-only workflow: `forge init` writes forge.yaml, `forge new` reads it and never prompts."""

import builtins

import yaml
from typer.testing import CliRunner

import cli
from core.validator import ValidationResult

runner = CliRunner()


def _no_input(*args, **kwargs):
    raise AssertionError("forge new must never prompt")


def _stub_checks(monkeypatch):
    monkeypatch.setattr(cli, "run_compile", lambda target_dir: ValidationResult(True, "ok"))


def test_init_writes_starter_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(cli.app, ["init"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "forge.yaml").exists()
    assert "forge new" in result.output


def test_init_refuses_to_overwrite(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "forge.yaml").write_text("project_name: keep-me\n", encoding="utf-8")

    result = runner.invoke(cli.app, ["init"])

    assert result.exit_code == 1
    assert "already exists" in result.output
    assert (tmp_path / "forge.yaml").read_text(encoding="utf-8") == "project_name: keep-me\n"


def test_new_without_file_points_to_init(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(cli.app, ["new"])

    assert result.exit_code == 1
    assert 'Run "forge init" first' in result.output
    assert list(tmp_path.iterdir()) == []


def test_new_with_invalid_file_reports_and_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "forge.yaml").write_text("project_name: ok-name\n", encoding="utf-8")

    result = runner.invoke(cli.app, ["new"])

    assert result.exit_code == 1
    assert "group_id" in result.output
    assert not (tmp_path / "ok-name").exists()


def test_new_rejects_cli_flags(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(cli.app, ["new", "--name", "demo"])

    assert result.exit_code != 0
    assert "No such option" in result.output


def test_new_never_prompts_even_when_file_is_complete(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(builtins, "input", _no_input)
    _stub_checks(monkeypatch)
    (tmp_path / "forge.yaml").write_text(
        yaml.safe_dump(
            {
                "project_name": "demo-service",
                "target_path": str(tmp_path),
                "group_id": "com.example",
                "artifact_id": "demo-service",
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(cli.app, ["new"], input="y\n")

    assert result.exit_code == 0, result.output
    assert (tmp_path / "demo-service" / "pom.xml").exists()


def test_file_entities_reach_the_render_context(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _stub_checks(monkeypatch)
    (tmp_path / "forge.yaml").write_text(
        yaml.safe_dump(
            {
                "project_name": "demo-service",
                "target_path": str(tmp_path),
                "group_id": "com.example",
                "artifact_id": "demo-service",
                "entities": {"Customer": {"fields": {"name": {"type": "string", "length": 100}}}},
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(cli.app, ["new"], input="y\n")

    assert result.exit_code == 0, result.output
    assert not list((tmp_path / "demo-service").rglob("ExampleController.java"))
    assert list((tmp_path / "demo-service").rglob("Customer.java"))


def test_file_entities_with_minimal_template_is_an_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "forge.yaml").write_text(
        yaml.safe_dump(
            {
                "project_name": "demo-service",
                "target_path": str(tmp_path),
                "group_id": "com.example",
                "artifact_id": "demo-service",
                "template": "minimal",
                "entities": {"Customer": {"fields": {"name": {"type": "string"}}}},
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(cli.app, ["new"], input="y\n")

    assert result.exit_code == 1
    assert not (tmp_path / "demo-service").exists()
