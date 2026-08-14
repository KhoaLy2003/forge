from pathlib import Path

from typer.testing import CliRunner

import cli
from core.validator import ValidationResult

runner = CliRunner()


def test_new_aborts_if_target_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "TEMPLATE_DIR", cli.TEMPLATE_DIR)
    existing = tmp_path / "demo-service"
    existing.mkdir()

    result = runner.invoke(
        cli.app,
        [
            "new",
            "--name", "demo-service",
            "--path", str(tmp_path),
            "--group-id", "com.example",
            "--artifact-id", "demo-service",
        ],
    )

    assert result.exit_code == 1
    assert "already exists" in result.output


def test_new_generates_project_on_confirm(tmp_path, monkeypatch):
    monkeypatch.setattr(
        cli, "run_compile", lambda target_dir: ValidationResult(True, "ok")
    )

    result = runner.invoke(
        cli.app,
        [
            "new",
            "--name", "demo-service",
            "--path", str(tmp_path),
            "--group-id", "com.example",
            "--artifact-id", "demo-service",
        ],
        input="y\n",
    )

    assert result.exit_code == 0, result.output
    assert (tmp_path / "demo-service" / "pom.xml").exists()
    assert "Project generated successfully" in result.output


def test_new_cancels_on_no_confirm(tmp_path):
    result = runner.invoke(
        cli.app,
        [
            "new",
            "--name", "demo-service",
            "--path", str(tmp_path),
            "--group-id", "com.example",
            "--artifact-id", "demo-service",
        ],
        input="n\n",
    )

    assert result.exit_code == 0
    assert not (tmp_path / "demo-service").exists()
    assert "Cancelled" in result.output


def test_new_errors_if_template_dir_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "TEMPLATE_DIR", tmp_path / "does-not-exist")

    result = runner.invoke(
        cli.app,
        [
            "new",
            "--name", "demo-service",
            "--path", str(tmp_path),
            "--group-id", "com.example",
            "--artifact-id", "demo-service",
        ],
    )

    assert result.exit_code == 1
    assert "template directory not found" in result.output


def test_new_prompts_to_delete_on_render_failure(tmp_path, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("disk full")

    monkeypatch.setattr(cli, "render_tree", boom)

    result = runner.invoke(
        cli.app,
        [
            "new",
            "--name", "demo-service",
            "--path", str(tmp_path),
            "--group-id", "com.example",
            "--artifact-id", "demo-service",
        ],
        input="y\ny\n",
    )

    assert result.exit_code == 1
    assert not (tmp_path / "demo-service").exists()
    assert "disk full" in result.output


def test_new_prompts_to_delete_on_validation_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(
        cli,
        "run_compile",
        lambda target_dir: ValidationResult(False, "mvn compile failed", "boom"),
    )

    result = runner.invoke(
        cli.app,
        [
            "new",
            "--name", "demo-service",
            "--path", str(tmp_path),
            "--group-id", "com.example",
            "--artifact-id", "demo-service",
        ],
        input="y\ny\n",
    )

    assert result.exit_code == 1
    assert "Validation failed" in result.output
    assert not (tmp_path / "demo-service").exists()
