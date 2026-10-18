from pathlib import Path

from typer.testing import CliRunner

import cli
from core.generation import TEMPLATES
from core.templates import SEARCH_PACKAGE_TEMPLATE
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


def _invoke_new(tmp_path, template, input_text="y\n"):
    return runner.invoke(
        cli.app,
        [
            "new",
            "--name", "demo-service",
            "--path", str(tmp_path),
            "--group-id", "com.example",
            "--artifact-id", "demo-service",
            "--template", template,
        ],
        input=input_text,
    )


def test_new_runs_observability_check_between_structure_and_compile(tmp_path, monkeypatch):
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

    result = _invoke_new(tmp_path, "base-layered")

    assert result.exit_code == 0, result.output
    assert calls == [("observability", True), ("compile",)]
    assert "[3/4] Running observability check..." in result.output
    assert "[4/4] Running compile check..." in result.output


def test_new_passes_include_monitoring_false_for_minimal(tmp_path, monkeypatch):
    seen = []
    monkeypatch.setattr(
        cli,
        "check_observability",
        lambda target_dir, include_monitoring: seen.append(include_monitoring)
        or ValidationResult(True, "ok"),
    )
    monkeypatch.setattr(cli, "run_compile", lambda target_dir: ValidationResult(True, "ok"))

    result = _invoke_new(tmp_path, "minimal")

    assert result.exit_code == 0, result.output
    assert seen == [False]


def test_new_aborts_before_compile_when_observability_check_fails(tmp_path, monkeypatch):
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

    result = _invoke_new(tmp_path, "base-layered", input_text="y\ny\n")

    assert result.exit_code == 1
    assert "Validation failed: Observability check failed" in result.output
    assert "unknown metric foo" in result.output
    assert compiled == []
    assert not (tmp_path / "demo-service").exists()


def test_new_passes_entity_dir_and_merges_dynamic_excludes(tmp_path, monkeypatch):
    from core.templates import ENTITY_DIR

    seen = {}
    real_resolve, real_render = cli.resolve_tree, cli.render_tree

    def spy_resolve(*args, **kwargs):
        seen["resolve"] = kwargs
        return real_resolve(*args, **kwargs)

    def spy_render(*args, **kwargs):
        seen["render"] = kwargs
        return real_render(*args, **kwargs)

    real_context = cli.ForgeConfig.template_context

    def ctx_with_entities(self):
        return {**real_context(self), "has_entities": True, "entities": []}

    monkeypatch.setattr(cli, "resolve_tree", spy_resolve)
    monkeypatch.setattr(cli, "render_tree", spy_render)
    monkeypatch.setattr(cli.ForgeConfig, "template_context", ctx_with_entities)
    monkeypatch.setattr(cli, "run_compile", lambda target_dir: ValidationResult(True, "ok"))

    result = _invoke_new(tmp_path, "minimal")

    assert result.exit_code == 0, result.output
    for key in ("resolve", "render"):
        assert seen[key]["entities_dir"] == ENTITY_DIR
        assert TEMPLATES["minimal"] == seen[key]["excluded"][: len(TEMPLATES["minimal"])]
        assert any("example" in pattern for pattern in seen[key]["excluded"][len(TEMPLATES["minimal"]):])
    project = tmp_path / "demo-service"
    assert not (project / "src/main/resources/db/changelog/001-create-example-table.sql").exists()
    assert not list(project.rglob("ExampleController.java"))


def test_new_without_entities_excludes_only_the_search_helpers_on_top_of_the_template(tmp_path, monkeypatch):
    seen = {}
    real_render = cli.render_tree

    def spy_render(*args, **kwargs):
        seen.update(kwargs)
        return real_render(*args, **kwargs)

    monkeypatch.setattr(cli, "render_tree", spy_render)
    monkeypatch.setattr(cli, "run_compile", lambda target_dir: ValidationResult(True, "ok"))

    result = _invoke_new(tmp_path, "base-layered")

    assert result.exit_code == 0, result.output
    # without entities the only dynamic exclude is the search helper package, which only entity filters use
    assert seen["excluded"] == TEMPLATES["base-layered"] + (SEARCH_PACKAGE_TEMPLATE,)
    assert list((tmp_path / "demo-service").rglob("ExampleController.java"))
