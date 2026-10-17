"""File-only workflow for forge-web: `init` writes forge-web.yaml, `new` reads it and never prompts."""

import builtins

from typer.testing import CliRunner

from forge_web import cli

runner = CliRunner()


def _no_input(*args, **kwargs):
    raise AssertionError("forge-web new must never prompt")


def test_init_writes_starter_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(cli.app, ["init"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "forge-web.yaml").exists()
    assert 'forge-web new' in result.output


def test_init_refuses_to_overwrite(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "forge-web.yaml").write_text("project_name: keep-me\n", encoding="utf-8")

    result = runner.invoke(cli.app, ["init"])

    assert result.exit_code == 1
    assert "already exists" in result.output
    assert (tmp_path / "forge-web.yaml").read_text(encoding="utf-8") == "project_name: keep-me\n"


def test_new_without_file_points_to_init(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(cli.app, ["new"])

    assert result.exit_code == 1
    assert 'Run "forge-web init" first' in result.output
    assert list(tmp_path.iterdir()) == []


def test_new_with_invalid_file_reports_and_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "forge-web.yaml").write_text("project_name: ok-name\n", encoding="utf-8")

    result = runner.invoke(cli.app, ["new"])

    assert result.exit_code == 1
    assert "api_base_url" in result.output
    assert not (tmp_path / "ok-name").exists()


def test_new_rejects_cli_flags(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(cli.app, ["new", "--name", "demo"])

    assert result.exit_code != 0
    assert "No such option" in result.output


def test_new_never_prompts(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(builtins, "input", _no_input)
    (tmp_path / "forge-web.yaml").write_text(
        f"project_name: demo\ntarget_path: {tmp_path.as_posix()}\napi_base_url: http://x/api\n",
        encoding="utf-8",
    )

    result = runner.invoke(cli.app, ["new"], input="n\n")

    assert result.exit_code == 0, result.output
    assert "Cancelled" in result.output
