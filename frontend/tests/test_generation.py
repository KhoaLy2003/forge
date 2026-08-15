from pathlib import Path

from forge_web.cli import EXPECTED_STRUCTURAL_PATHS, TEMPLATE_DIR
from forge_web.core.config_schema import ForgeWebConfig
from forge_web.core.renderer import render_tree
from forge_web.core.validator import (
    check_no_hardcoded_design_values,
    check_structure,
    run_build,
    run_typecheck,
)


def test_generated_project_builds_and_typechecks(tmp_path):
    config = ForgeWebConfig(
        project_name="test-dashboard",
        target_path=tmp_path,
        api_base_url="http://localhost:8080/api",
    )
    render_tree(TEMPLATE_DIR, config.target_dir, config.template_context())

    structural = check_structure(config.target_dir, EXPECTED_STRUCTURAL_PATHS)
    assert structural.passed, structural.details

    build = run_build(config.target_dir)
    assert build.passed, build.details

    typecheck = run_typecheck(config.target_dir)
    assert typecheck.passed, typecheck.details

    tokens = check_no_hardcoded_design_values(config.target_dir)
    assert tokens.passed, tokens.details
