from pathlib import Path

from typer.testing import CliRunner

from forge_web import cli
from forge_web.core.validator import ValidationResult

runner = CliRunner()


def test_new_aborts_if_target_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "SHARED_DIR", cli.SHARED_DIR)
    existing = tmp_path / "my-dashboard"
    existing.mkdir()

    result = runner.invoke(
        cli.app,
        [
            "new",
            "--name", "my-dashboard",
            "--path", str(tmp_path),
            "--api-base-url", "http://localhost:8080/api",
            "--template", "base",
        ],
    )

    assert result.exit_code == 1
    assert "already exists" in result.output


def test_new_errors_if_template_dir_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "SHARED_DIR", tmp_path / "does-not-exist")

    result = runner.invoke(
        cli.app,
        [
            "new",
            "--name", "my-dashboard",
            "--path", str(tmp_path),
            "--api-base-url", "http://localhost:8080/api",
            "--template", "base",
        ],
    )

    assert result.exit_code == 1
    assert "template directory not found" in result.output


def test_new_errors_on_unknown_template(tmp_path):
    result = runner.invoke(
        cli.app,
        [
            "new",
            "--name", "my-dashboard",
            "--path", str(tmp_path),
            "--api-base-url", "http://localhost:8080/api",
            "--template", "does-not-exist",
        ],
    )

    assert result.exit_code != 0
    assert "base" in result.output and "minimal" in result.output


def make_fixture_template(tmp_path: Path) -> Path:
    template_dir = tmp_path / "fixture_template"
    template_dir.mkdir(parents=True)
    (template_dir / "package.json").write_text(
        '{"name": "{{ project_name }}"}', encoding="utf-8"
    )
    (template_dir / ".env.example").write_text(
        "VITE_APP_NAME={{ app_display_name }}\n"
        "VITE_API_MODE=false\n"
        "VITE_API_BASE_URL={{ api_base_url }}\n",
        encoding="utf-8",
    )
    return template_dir


def test_new_generates_project_on_confirm(tmp_path, monkeypatch):
    template_dir = make_fixture_template(tmp_path / "src")
    monkeypatch.setattr(cli, "SHARED_DIR", template_dir)
    monkeypatch.setattr(cli, "EXPECTED_STRUCTURAL_PATHS", [Path("package.json")])
    monkeypatch.setattr(
        cli, "run_build", lambda target_dir: ValidationResult(True, "ok")
    )
    monkeypatch.setattr(
        cli, "run_typecheck", lambda target_dir: ValidationResult(True, "ok")
    )
    monkeypatch.setattr(
        cli,
        "check_no_hardcoded_design_values",
        lambda target_dir: ValidationResult(True, "ok"),
    )

    result = runner.invoke(
        cli.app,
        [
            "new",
            "--name", "my-dashboard",
            "--path", str(tmp_path / "out"),
            "--api-base-url", "http://localhost:8080/api",
            "--template", "base",
        ],
        input="y\n",
    )

    assert result.exit_code == 0, result.output
    assert (tmp_path / "out" / "my-dashboard" / "package.json").exists()
    assert "Project generated successfully" in result.output


def test_new_defaults_template_when_flag_omitted(tmp_path, monkeypatch):
    """A flag-complete invocation that omits --template must still run non-interactively
    to completion (no wizard prompt for template) — regression test for a bug where
    --template had no default and always fell through to a blocking wizard prompt."""
    template_dir = make_fixture_template(tmp_path / "src")
    monkeypatch.setattr(cli, "SHARED_DIR", template_dir)
    monkeypatch.setattr(cli, "EXPECTED_STRUCTURAL_PATHS", [Path("package.json")])
    monkeypatch.setattr(
        cli, "run_build", lambda target_dir: ValidationResult(True, "ok")
    )
    monkeypatch.setattr(
        cli, "run_typecheck", lambda target_dir: ValidationResult(True, "ok")
    )
    monkeypatch.setattr(
        cli,
        "check_no_hardcoded_design_values",
        lambda target_dir: ValidationResult(True, "ok"),
    )

    result = runner.invoke(
        cli.app,
        [
            "new",
            "--name", "my-dashboard",
            "--path", str(tmp_path / "out"),
            "--api-base-url", "http://localhost:8080/api",
        ],
        input="y\n",
    )

    assert result.exit_code == 0, result.output
    assert (tmp_path / "out" / "my-dashboard" / "package.json").exists()


def test_new_generates_dot_env_from_env_example(tmp_path, monkeypatch):
    template_dir = make_fixture_template(tmp_path / "src")
    monkeypatch.setattr(cli, "SHARED_DIR", template_dir)
    monkeypatch.setattr(cli, "EXPECTED_STRUCTURAL_PATHS", [Path("package.json")])
    monkeypatch.setattr(
        cli, "run_build", lambda target_dir: ValidationResult(True, "ok")
    )
    monkeypatch.setattr(
        cli, "run_typecheck", lambda target_dir: ValidationResult(True, "ok")
    )
    monkeypatch.setattr(
        cli,
        "check_no_hardcoded_design_values",
        lambda target_dir: ValidationResult(True, "ok"),
    )

    result = runner.invoke(
        cli.app,
        [
            "new",
            "--name", "my-dashboard",
            "--path", str(tmp_path / "out"),
            "--api-base-url", "http://localhost:8080/api",
            "--template", "base",
        ],
        input="y\n",
    )

    assert result.exit_code == 0, result.output
    target_dir = tmp_path / "out" / "my-dashboard"
    env_example = target_dir / ".env.example"
    env_file = target_dir / ".env"
    assert env_example.exists()
    assert env_file.exists()
    assert env_file.read_text(encoding="utf-8") == env_example.read_text(
        encoding="utf-8"
    )


def test_new_cancels_on_no_confirm(tmp_path):
    template_dir = make_fixture_template(tmp_path / "src")

    from forge_web import cli as cli_module

    original_shared_dir = cli_module.SHARED_DIR
    cli_module.SHARED_DIR = template_dir
    try:
        result = runner.invoke(
            cli_module.app,
            [
                "new",
                "--name", "my-dashboard",
                "--path", str(tmp_path / "out"),
                "--api-base-url", "http://localhost:8080/api",
                "--template", "base",
            ],
            input="n\n",
        )
    finally:
        cli_module.SHARED_DIR = original_shared_dir

    assert result.exit_code == 0
    assert not (tmp_path / "out" / "my-dashboard").exists()
    assert "Cancelled" in result.output


def test_new_with_minimal_template_excludes_api_client(tmp_path, monkeypatch):
    monkeypatch.setattr(
        cli, "run_build", lambda target_dir: ValidationResult(True, "ok")
    )
    monkeypatch.setattr(
        cli, "run_typecheck", lambda target_dir: ValidationResult(True, "ok")
    )
    monkeypatch.setattr(
        cli,
        "check_no_hardcoded_design_values",
        lambda target_dir: ValidationResult(True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_no_spacing_scale_width_collisions",
        lambda target_dir: ValidationResult(True, "ok"),
    )

    result = runner.invoke(
        cli.app,
        [
            "new",
            "--name", "my-dashboard",
            "--path", str(tmp_path / "out"),
            "--api-base-url", "http://localhost:8080/api",
            "--template", "minimal",
        ],
        input="y\n",
    )

    target_dir = tmp_path / "out" / "my-dashboard"
    assert result.exit_code == 0, result.output
    assert not (target_dir / "src" / "lib" / "api-client").exists()
