from pathlib import Path

from typer.testing import CliRunner

import cli
from core.validator import ValidationResult

runner = CliRunner()


def test_new_aborts_if_target_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "SHARED_DIR", cli.SHARED_DIR)
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
            "--template", "base-layered",
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
            "--template", "base-layered",
        ],
        input="y\n",
    )

    assert result.exit_code == 0, result.output
    assert (tmp_path / "demo-service" / "pom.xml").exists()
    assert "Project generated successfully" in result.output


def test_new_defaults_template_when_flag_omitted(tmp_path, monkeypatch):
    """A flag-complete invocation that omits --template must still run non-interactively
    to completion (no wizard prompt for template) — regression test for a bug where
    --template had no default and always fell through to a blocking wizard prompt."""
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
    assert (tmp_path / "demo-service" / "src/main/resources/db/changelog").exists()


def test_new_cancels_on_no_confirm(tmp_path):
    result = runner.invoke(
        cli.app,
        [
            "new",
            "--name", "demo-service",
            "--path", str(tmp_path),
            "--group-id", "com.example",
            "--artifact-id", "demo-service",
            "--template", "base-layered",
        ],
        input="n\n",
    )

    assert result.exit_code == 0
    assert not (tmp_path / "demo-service").exists()
    assert "Cancelled" in result.output


def test_new_errors_if_template_dir_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "SHARED_DIR", tmp_path / "does-not-exist")

    result = runner.invoke(
        cli.app,
        [
            "new",
            "--name", "demo-service",
            "--path", str(tmp_path),
            "--group-id", "com.example",
            "--artifact-id", "demo-service",
            "--template", "base-layered",
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
            "--template", "base-layered",
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
            "--template", "base-layered",
        ],
        input="y\ny\n",
    )

    assert result.exit_code == 1
    assert "Validation failed" in result.output
    assert not (tmp_path / "demo-service").exists()


def test_new_with_minimal_template_excludes_liquibase_changelog(tmp_path, monkeypatch):
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
            "--template", "minimal",
        ],
        input="y\n",
    )

    assert result.exit_code == 0, result.output
    assert (tmp_path / "demo-service" / "pom.xml").exists()
    assert not (tmp_path / "demo-service" / "src/main/resources/db/changelog").exists()


def test_new_rejects_unknown_template(tmp_path):
    result = runner.invoke(
        cli.app,
        [
            "new",
            "--name", "demo-service",
            "--path", str(tmp_path),
            "--group-id", "com.example",
            "--artifact-id", "demo-service",
            "--template", "does-not-exist",
        ],
    )

    assert result.exit_code != 0
    assert not (tmp_path / "demo-service").exists()
    assert "base-layered" in result.output and "minimal" in result.output
