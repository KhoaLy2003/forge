# tests/test_generation.py
from pathlib import Path

from cli import EXPECTED_STRUCTURAL_PATHS, TEMPLATE_DIR, expected_structural_paths
from core.config_schema import ForgeConfig
from core.renderer import render_tree
from core.validator import check_structure, run_compile


def test_generated_project_passes_structural_and_compile_checks(tmp_path):
    config = ForgeConfig(
        project_name="demo-service",
        target_path=tmp_path,
        group_id="com.example",
        artifact_id="demo-service",
    )

    render_tree(TEMPLATE_DIR, config.target_dir, config.template_context())

    structural = check_structure(config.target_dir, EXPECTED_STRUCTURAL_PATHS)
    assert structural.passed, structural.details

    dynamic_paths = expected_structural_paths(config.template_context())
    dynamic_structural = check_structure(config.target_dir, dynamic_paths)
    assert dynamic_structural.passed, dynamic_structural.details

    compile_result = run_compile(config.target_dir)
    assert compile_result.passed, compile_result.details

    app_file = (
        config.target_dir
        / "src/main/java/com/example/demoservice/DemoServiceApplication.java"
    )
    assert app_file.exists()
