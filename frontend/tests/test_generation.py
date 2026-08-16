import pytest

from forge_web.cli import EXPECTED_STRUCTURAL_PATHS
from forge_web.core.config_schema import ForgeWebConfig
from forge_web.core.renderer import render_tree
from forge_web.core.templates import SHARED_DIR, discover_templates, filter_excluded_paths
from forge_web.core.validator import (
    check_no_hardcoded_design_values,
    check_no_spacing_scale_width_collisions,
    check_structure,
    run_build,
    run_typecheck,
)


@pytest.mark.parametrize("template_name", sorted(discover_templates()))
def test_generated_project_builds_and_typechecks(tmp_path, template_name):
    config = ForgeWebConfig(
        project_name="test-dashboard",
        target_path=tmp_path / template_name,
        api_base_url="http://localhost:8080/api",
        template=template_name,
    )
    excluded = discover_templates()[template_name]
    context = config.template_context()

    render_tree(SHARED_DIR, config.target_dir, context, excluded=excluded)

    static_paths = filter_excluded_paths(EXPECTED_STRUCTURAL_PATHS, excluded, context)
    structural = check_structure(config.target_dir, static_paths)
    assert structural.passed, structural.details

    build = run_build(config.target_dir)
    assert build.passed, build.details

    typecheck = run_typecheck(config.target_dir)
    assert typecheck.passed, typecheck.details

    tokens = check_no_hardcoded_design_values(config.target_dir)
    assert tokens.passed, tokens.details

    collisions = check_no_spacing_scale_width_collisions(config.target_dir)
    assert collisions.passed, collisions.details

    if template_name == "minimal":
        assert not (config.target_dir / "src" / "lib" / "api-client").exists()
        nav_sidebar = (
            config.target_dir / "src" / "components" / "common" / "nav-sidebar.tsx"
        ).read_text(encoding="utf-8")
        assert "/dashboard" not in nav_sidebar
