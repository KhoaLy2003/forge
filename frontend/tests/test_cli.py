import os
from pathlib import Path

import yaml
from typer.testing import CliRunner

from forge_web import cli
from forge_web.core.validator import ValidationResult

runner = CliRunner()

API_BASE_URL = "http://localhost:8080/api"


def _invoke_new(folder, *, name, target, template=None, verbose=False, input_text=None):
    """Write forge-web.yaml into ``folder`` and run `forge-web new` from that folder."""
    data = {"project_name": name, "target_path": str(target), "api_base_url": API_BASE_URL}
    if template is not None:
        data["template"] = template
    (folder / "forge-web.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
    args = ["new"] + (["--verbose"] if verbose else [])
    previous = os.getcwd()
    os.chdir(folder)
    try:
        return runner.invoke(cli.app, args, input=input_text)
    finally:
        os.chdir(previous)


def test_new_aborts_if_target_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "SHARED_DIR", cli.SHARED_DIR)
    existing = tmp_path / "my-dashboard"
    existing.mkdir()

    result = _invoke_new(tmp_path, name="my-dashboard", target=str(tmp_path), template="base")

    assert result.exit_code == 1
    assert "already exists" in result.output


def test_new_errors_if_template_dir_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "SHARED_DIR", tmp_path / "does-not-exist")

    result = _invoke_new(tmp_path, name="my-dashboard", target=str(tmp_path), template="base")

    assert result.exit_code == 1
    assert "template directory not found" in result.output


def test_new_errors_on_unknown_template(tmp_path):
    result = _invoke_new(tmp_path, name="my-dashboard", target=str(tmp_path), template="does-not-exist")

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

    result = _invoke_new(tmp_path, name="my-dashboard", target=str(tmp_path / "out"), template="base", input_text="y\n")

    assert result.exit_code == 0, result.output
    assert (tmp_path / "out" / "my-dashboard" / "package.json").exists()
    assert "Project generated successfully" in result.output


def test_new_defaults_template_when_file_omits_it(tmp_path, monkeypatch):
    """A forge-web.yaml without a template key generates the default 'base' template."""
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

    result = _invoke_new(tmp_path, name="my-dashboard", target=str(tmp_path / "out"), input_text="y\n")

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

    result = _invoke_new(tmp_path, name="my-dashboard", target=str(tmp_path / "out"), template="base", input_text="y\n")

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
        result = _invoke_new(tmp_path, name="my-dashboard", target=str(tmp_path / "out"), template="base", input_text="n\n")
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

    result = _invoke_new(tmp_path, name="my-dashboard", target=str(tmp_path / "out"), template="minimal", input_text="y\n")

    target_dir = tmp_path / "out" / "my-dashboard"
    assert result.exit_code == 0, result.output
    assert not (target_dir / "src" / "lib" / "api-client").exists()


def test_new_deletes_folder_on_render_failure_when_confirmed(tmp_path, monkeypatch):
    template_dir = make_fixture_template(tmp_path / "src")
    monkeypatch.setattr(cli, "SHARED_DIR", template_dir)

    def raise_on_render(*args, **kwargs):
        (tmp_path / "out" / "my-dashboard").mkdir(parents=True)
        raise RuntimeError("boom")

    monkeypatch.setattr(cli, "render_tree", raise_on_render)

    result = _invoke_new(tmp_path, name="my-dashboard", target=str(tmp_path / "out"), verbose=True, input_text="y\ny\n")

    assert result.exit_code == 1
    assert "failed to write project files" in result.output
    assert "Traceback" in result.output
    assert not (tmp_path / "out" / "my-dashboard").exists()


def test_new_reports_build_failure(tmp_path, monkeypatch):
    template_dir = make_fixture_template(tmp_path / "src")
    monkeypatch.setattr(cli, "SHARED_DIR", template_dir)
    monkeypatch.setattr(cli, "EXPECTED_STRUCTURAL_PATHS", [Path("package.json")])
    monkeypatch.setattr(
        cli, "run_build", lambda target_dir: ValidationResult(False, "build failed")
    )

    result = _invoke_new(tmp_path, name="my-dashboard", target=str(tmp_path / "out"), input_text="y\nn\n")

    assert result.exit_code == 1
    assert "Validation failed" in result.output
    assert (tmp_path / "out" / "my-dashboard").exists()


def test_new_reports_typecheck_failure(tmp_path, monkeypatch):
    template_dir = make_fixture_template(tmp_path / "src")
    monkeypatch.setattr(cli, "SHARED_DIR", template_dir)
    monkeypatch.setattr(cli, "EXPECTED_STRUCTURAL_PATHS", [Path("package.json")])
    monkeypatch.setattr(
        cli, "run_build", lambda target_dir: ValidationResult(True, "ok")
    )
    monkeypatch.setattr(
        cli, "run_typecheck", lambda target_dir: ValidationResult(False, "typecheck failed")
    )

    result = _invoke_new(tmp_path, name="my-dashboard", target=str(tmp_path / "out"), input_text="y\nn\n")

    assert result.exit_code == 1
    assert "Validation failed" in result.output


def test_new_reports_hardcoded_design_values_failure(tmp_path, monkeypatch):
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
        lambda target_dir: ValidationResult(False, "hardcoded value found"),
    )

    result = _invoke_new(tmp_path, name="my-dashboard", target=str(tmp_path / "out"), input_text="y\nn\n")

    assert result.exit_code == 1
    assert "Validation failed" in result.output


def test_new_reports_spacing_scale_collision_failure(tmp_path, monkeypatch):
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
    monkeypatch.setattr(
        cli,
        "check_no_spacing_scale_width_collisions",
        lambda target_dir: ValidationResult(False, "collision found"),
    )

    result = _invoke_new(tmp_path, name="my-dashboard", target=str(tmp_path / "out"), input_text="y\nn\n")

    assert result.exit_code == 1
    assert "Validation failed" in result.output
