# tests/test_generation.py
import pytest

from cli import EXPECTED_STRUCTURAL_PATHS, expected_structural_paths
from core.config_schema import ForgeConfig
from core.renderer import render_tree
from core.templates import SHARED_DIR, discover_templates, filter_excluded_paths
from core.validator import check_structure, run_compile


@pytest.mark.parametrize("template_name", sorted(discover_templates()))
def test_generated_project_passes_structural_and_compile_checks(tmp_path, template_name):
    config = ForgeConfig(
        project_name="demo-service",
        target_path=tmp_path / template_name,
        group_id="com.example",
        artifact_id="demo-service",
        template=template_name,
    )
    excluded = discover_templates()[template_name]
    context = config.template_context()

    render_tree(SHARED_DIR, config.target_dir, context, excluded=excluded)

    static_paths = filter_excluded_paths(EXPECTED_STRUCTURAL_PATHS, excluded, context)
    dynamic_paths = filter_excluded_paths(expected_structural_paths(context), excluded, context)
    structural = check_structure(config.target_dir, static_paths + dynamic_paths)
    assert structural.passed, structural.details

    compile_result = run_compile(config.target_dir)
    assert compile_result.passed, compile_result.details

    if template_name == "minimal":
        assert not (config.target_dir / "src/main/resources/db/changelog").exists()
