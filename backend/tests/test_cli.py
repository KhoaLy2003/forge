from pathlib import Path

import pytest
from typer.testing import CliRunner

import cli
from core.config_schema import ForgeConfig
from core.validator import ValidationResult

runner = CliRunner()

PROJECT_FILE = """\
project_name: demo-service
target_path: {target}
group_id: com.example
artifact_id: demo-service
{extra}"""


def _project_file(folder: Path, template: str | None = None, extra: str = "") -> Path:
    """Write a forge.yaml into ``folder`` whose target is ``folder`` (generated project: folder/demo-service)."""
    if template is not None:
        extra += f"template: {template}\n"
    path = folder / "forge.yaml"
    path.write_text(PROJECT_FILE.format(target=folder.as_posix(), extra=extra), encoding="utf-8")
    return path


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    """Run the CLI from tmp_path, so ``forge new`` finds tmp_path/forge.yaml."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _stub_compile(monkeypatch, result=None):
    monkeypatch.setattr(cli, "run_compile", lambda target_dir: result or ValidationResult(True, "ok"))


def _invoke_new(input_text="y\n"):
    return runner.invoke(cli.app, ["new"], input=input_text)


def test_new_aborts_if_target_exists(workdir, monkeypatch):
    _stub_compile(monkeypatch)
    _project_file(workdir, "base-layered")
    (workdir / "demo-service").mkdir()

    result = _invoke_new()

    assert result.exit_code == 1
    assert "already exists" in result.output


def test_new_generates_project_on_confirm(workdir, monkeypatch):
    _stub_compile(monkeypatch)
    _project_file(workdir)

    result = _invoke_new()

    assert result.exit_code == 0, result.output
    assert (workdir / "demo-service" / "pom.xml").exists()
    assert "Project generated successfully" in result.output


def test_new_defaults_template_when_file_omits_it(workdir, monkeypatch):
    _stub_compile(monkeypatch)
    _project_file(workdir)  # no template key

    result = _invoke_new()

    assert result.exit_code == 0, result.output
    assert (workdir / "demo-service" / "src/main/resources/db/changelog").exists()


def test_new_cancels_on_no_confirm(workdir):
    _project_file(workdir, "base-layered")

    result = _invoke_new(input_text="n\n")

    assert result.exit_code == 0
    assert not (workdir / "demo-service").exists()
    assert "Cancelled" in result.output


def test_new_errors_if_template_dir_missing(workdir, monkeypatch):
    monkeypatch.setattr(cli, "SHARED_DIR", workdir / "does-not-exist")
    _project_file(workdir, "base-layered")

    result = _invoke_new()

    assert result.exit_code == 1
    assert "template directory not found" in result.output


def test_new_prompts_to_delete_on_render_failure(workdir, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("disk full")

    monkeypatch.setattr(cli, "render_tree", boom)
    _project_file(workdir, "base-layered")

    result = _invoke_new(input_text="y\ny\n")

    assert result.exit_code == 1
    assert not (workdir / "demo-service").exists()
    assert "disk full" in result.output


def test_new_prompts_to_delete_on_validation_failure(workdir, monkeypatch):
    _stub_compile(monkeypatch, ValidationResult(False, "mvn compile failed", "boom"))
    _project_file(workdir, "base-layered")

    result = _invoke_new(input_text="y\ny\n")

    assert result.exit_code == 1
    assert "Validation failed" in result.output
    assert not (workdir / "demo-service").exists()


def test_new_with_minimal_template_excludes_liquibase_changelog(workdir, monkeypatch):
    _stub_compile(monkeypatch)
    _project_file(workdir, "minimal")

    result = _invoke_new()

    assert result.exit_code == 0, result.output
    assert (workdir / "demo-service" / "pom.xml").exists()
    assert not (workdir / "demo-service" / "src/main/resources/db/changelog").exists()


def test_new_rejects_unknown_template_in_file(workdir):
    _project_file(workdir, "does-not-exist")

    result = _invoke_new()

    assert result.exit_code == 1
    assert not (workdir / "demo-service").exists()
    assert "base-layered" in result.output and "minimal" in result.output


def test_new_runs_observability_check_between_structure_and_compile(workdir, monkeypatch):
    calls = []
    monkeypatch.setattr(
        cli,
        "check_observability",
        lambda target_dir, include_monitoring: calls.append(("observability", include_monitoring))
        or ValidationResult(True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "run_compile",
        lambda target_dir: calls.append(("compile",)) or ValidationResult(True, "ok"),
    )
    _project_file(workdir, "base-layered")

    result = _invoke_new()

    assert result.exit_code == 0, result.output
    assert calls == [("observability", True), ("compile",)]
    assert "[3/4] Running observability check..." in result.output
    assert "[4/4] Running compile check..." in result.output


def test_new_passes_include_monitoring_false_for_minimal(workdir, monkeypatch):
    seen = []
    monkeypatch.setattr(
        cli,
        "check_observability",
        lambda target_dir, include_monitoring: seen.append(include_monitoring)
        or ValidationResult(True, "ok"),
    )
    _stub_compile(monkeypatch)
    _project_file(workdir, "minimal")

    result = _invoke_new()

    assert result.exit_code == 0, result.output
    assert seen == [False]


def test_new_aborts_before_compile_when_observability_check_fails(workdir, monkeypatch):
    compiled = []
    monkeypatch.setattr(
        cli,
        "check_observability",
        lambda target_dir, include_monitoring: ValidationResult(
            False, "Observability check failed", "alerts.yml: rule X references unknown metric foo"
        ),
    )
    monkeypatch.setattr(
        cli,
        "run_compile",
        lambda target_dir: compiled.append(True) or ValidationResult(True, "ok"),
    )
    _project_file(workdir, "base-layered")

    result = _invoke_new(input_text="y\ny\n")

    assert result.exit_code == 1
    assert "Validation failed: Observability check failed" in result.output
    assert "unknown metric foo" in result.output
    assert compiled == []
    assert not (workdir / "demo-service").exists()


def test_new_passes_entity_dir_and_merges_dynamic_excludes(workdir, monkeypatch):
    from core.templates import ENTITY_DIR

    seen = {}
    real_resolve, real_render = cli.resolve_tree, cli.render_tree

    def spy_resolve(*args, **kwargs):
        seen["resolve"] = kwargs
        return real_resolve(*args, **kwargs)

    def spy_render(*args, **kwargs):
        seen["render"] = kwargs
        return real_render(*args, **kwargs)

    real_context = ForgeConfig.template_context

    def ctx_with_entities(self):
        return {**real_context(self), "has_entities": True, "entities": []}

    monkeypatch.setattr(cli, "resolve_tree", spy_resolve)
    monkeypatch.setattr(cli, "render_tree", spy_render)
    monkeypatch.setattr(ForgeConfig, "template_context", ctx_with_entities)
    _stub_compile(monkeypatch)
    _project_file(workdir, "minimal")

    result = _invoke_new()

    assert result.exit_code == 0, result.output
    for key in ("resolve", "render"):
        assert seen[key]["entities_dir"] == ENTITY_DIR
        assert cli.TEMPLATES["minimal"] == seen[key]["excluded"][: len(cli.TEMPLATES["minimal"])]
        assert any("example" in pattern for pattern in seen[key]["excluded"][len(cli.TEMPLATES["minimal"]):])
    project = workdir / "demo-service"
    assert not (project / "src/main/resources/db/changelog/001-create-example-table.sql").exists()
    assert not list(project.rglob("ExampleController.java"))


def test_new_without_entities_passes_only_template_excludes(workdir, monkeypatch):
    seen = {}
    real_render = cli.render_tree

    def spy_render(*args, **kwargs):
        seen.update(kwargs)
        return real_render(*args, **kwargs)

    monkeypatch.setattr(cli, "render_tree", spy_render)
    _stub_compile(monkeypatch)
    _project_file(workdir, "base-layered")

    result = _invoke_new()

    assert result.exit_code == 0, result.output
    assert seen["excluded"] == cli.TEMPLATES["base-layered"]
    assert list((workdir / "demo-service").rglob("ExampleController.java"))
