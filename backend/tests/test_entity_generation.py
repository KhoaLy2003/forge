"""End-to-end checks for entity-driven generation (real Maven, no Docker, no database)."""

import shutil
import subprocess
from pathlib import Path

import pytest

from core.generation import EXPECTED_STRUCTURAL_PATHS, expected_structural_paths
from core.config_schema import ForgeConfig
from core.entity_spec import load_forge_yaml
from core.renderer import render_tree
from core.templates import (
    ENTITY_DIR,
    JOIN_DIR,
    SHARED_DIR,
    discover_templates,
    dynamic_excludes,
    filter_excluded_paths,
)
from core.validator import check_observability, check_structure, run_compile, run_tests

FIXTURE = Path(__file__).parent / "fixtures" / "entities.forge.yaml"

# Everything except the Testcontainers-backed classes, which need Docker and run in the generated
# project's CI (NotificationQueriesTest and every generated *RepositoryTest).
DOCKER_FREE_TESTS = "!*RepositoryTest,!NotificationQueriesTest"


def _config(tmp_path: Path) -> ForgeConfig:
    project = load_forge_yaml(FIXTURE)
    return ForgeConfig(
        project_name="demo-service",
        target_path=tmp_path,
        group_id="com.example",
        artifact_id="demo-service",
        entities=project.entities,
    )


def _excluded(config: ForgeConfig, context: dict) -> tuple[str, ...]:
    return discover_templates()[config.template] + dynamic_excludes(context)


def test_structural_paths_list_every_entity_file_and_changelog():
    config = _config(Path("."))
    context = config.template_context()

    paths = {p.as_posix() for p in expected_structural_paths(context)}

    base = "src/main/java/com/example/demoservice"
    tests = "src/test/java/com/example/demoservice"
    for entity in context["entities"]:
        name, package = entity.name, entity.package
        for kind in (
            f"entity/{name}.java",
            f"repository/{name}Repository.java",
            f"dto/Create{name}Request.java",
            f"dto/Update{name}Request.java",
            f"dto/{name}Response.java",
            f"mapper/{name}Mapper.java",
            f"service/{name}Service.java",
            f"service/{name}ServiceImpl.java",
            f"controller/{name}Controller.java",
        ):
            assert f"{base}/{package}/{kind}" in paths, kind
        for kind in (
            f"service/{name}ServiceImplTest.java",
            f"mapper/{name}MapperTest.java",
            f"controller/{name}ControllerTest.java",
            f"repository/{name}RepositoryTest.java",
        ):
            assert f"{tests}/{package}/{kind}" in paths, kind
        assert f"src/main/resources/db/changelog/{entity.changelog_file}" in paths
    for join_table in context["join_tables"]:
        assert f"src/main/resources/db/changelog/{join_table.changelog_file}" in paths
    assert (
        f"src/main/resources/db/changelog/{context['constraints_changelog_file']}" in paths
    )


def test_structural_paths_without_entities_are_unchanged():
    config = ForgeConfig(
        project_name="demo-service",
        target_path=Path("."),
        group_id="com.example",
        artifact_id="demo-service",
    )

    paths = {p.as_posix() for p in expected_structural_paths(config.template_context())}

    assert not any("customer" in p for p in paths)
    assert not any("add-constraints" in p for p in paths)
    assert any("/example/" in p and p.endswith("Example.java") for p in paths)


def test_the_example_slice_is_not_expected_once_entities_exist():
    config = _config(Path("."))
    context = config.template_context()
    excluded = _excluded(config, context)

    paths = filter_excluded_paths(
        EXPECTED_STRUCTURAL_PATHS + expected_structural_paths(context), excluded, context
    )

    posix = {p.as_posix() for p in paths}
    assert "src/main/resources/db/changelog/001-create-example-table.sql" not in posix
    assert not any(p.startswith("src/main/java/com/example/demoservice/example/") for p in posix)


@pytest.fixture(scope="module")
def generated(tmp_path_factory) -> tuple[ForgeConfig, dict]:
    tmp_path = tmp_path_factory.mktemp("entities")
    config = _config(tmp_path)
    context = config.template_context()
    render_tree(
        SHARED_DIR,
        config.target_dir,
        context,
        excluded=_excluded(config, context),
        entities_dir=ENTITY_DIR,
        join_dir=JOIN_DIR,
    )
    return config, context


def test_generated_entity_project_has_no_example_slice_and_a_full_changelog(generated):
    config, context = generated
    root = config.target_dir

    assert not (root / "src/main/java/com/example/demoservice/example").exists()
    assert not (root / "src/main/resources/db/changelog/001-create-example-table.sql").exists()
    master = (root / "src/main/resources/db/changelog/db.changelog-master.xml").read_text(
        encoding="utf-8"
    )
    positions = [master.index(name) for name in context["changelog_files"]]
    assert positions == sorted(positions), "changelogs must be included in dependency order"
    for name in context["changelog_files"]:
        assert (root / "src/main/resources/db/changelog" / name).is_file(), name


def test_generated_entity_project_passes_all_local_checks(generated):
    config, context = generated
    excluded = _excluded(config, context)

    static_paths = filter_excluded_paths(EXPECTED_STRUCTURAL_PATHS, excluded, context)
    dynamic_paths = filter_excluded_paths(expected_structural_paths(context), excluded, context)
    structural = check_structure(config.target_dir, static_paths + dynamic_paths)
    assert structural.passed, structural.details

    observability = check_observability(config.target_dir, config.include_monitoring)
    assert observability.passed, observability.details

    compiled = run_compile(config.target_dir)
    assert compiled.passed, compiled.details

    unit_tests = run_tests(config.target_dir, DOCKER_FREE_TESTS, timeout=600)
    assert unit_tests.passed, unit_tests.details


def test_generated_entity_project_is_spotless_clean(generated):
    config, _ = generated
    mvn = shutil.which("mvn") or "mvn"

    result = subprocess.run(
        [mvn, "-q", "spotless:check"],
        cwd=config.target_dir,
        capture_output=True,
        text=True,
        timeout=600,
    )

    assert result.returncode == 0, result.stdout + result.stderr
