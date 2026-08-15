import shutil
import subprocess

import pytest

from forge_web.core.validator import (
    ValidationResult,
    check_no_hardcoded_design_values,
    check_no_spacing_scale_width_collisions,
    check_structure,
    run_build,
    run_typecheck,
)
from pathlib import Path

NPM_AVAILABLE = shutil.which("npm") is not None
NPX_AVAILABLE = shutil.which("npx") is not None


def _install_typescript(tmp_path):
    # Without a locally installed `typescript`, `npx tsc` falls through to
    # npm's auto-install-on-missing-command behavior, which installs a
    # same-named-but-unrelated `tsc` package instead of `typescript` (the
    # package that actually provides the tsc binary).
    (tmp_path / "package.json").write_text(
        '{"name": "typecheck-fixture", "version": "1.0.0", "private": true}',
        encoding="utf-8",
    )
    npm_cmd = shutil.which("npm") or "npm"
    subprocess.run(
        [npm_cmd, "install", "typescript", "--no-audit", "--no-fund"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )


def test_check_structure_passes_when_all_expected_files_exist(tmp_path):
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    result = check_structure(tmp_path, [Path("package.json")])
    assert result == ValidationResult(True, "Structural check passed")


def test_check_structure_fails_and_lists_missing_files(tmp_path):
    result = check_structure(tmp_path, [Path("package.json"), Path("index.html")])
    assert result.passed is False
    assert "package.json" in result.details
    assert "index.html" in result.details


@pytest.mark.skipif(not NPM_AVAILABLE, reason="npm not on PATH")
def test_run_build_passes_for_minimal_project(tmp_path):
    (tmp_path / "package.json").write_text(
        '{"name": "minimal", "version": "1.0.0", "scripts": {"build": "echo built"}}',
        encoding="utf-8",
    )

    result = run_build(tmp_path)

    assert result.passed is True, result.details


@pytest.mark.skipif(not NPM_AVAILABLE, reason="npm not on PATH")
def test_run_build_fails_for_broken_build_script(tmp_path):
    (tmp_path / "package.json").write_text(
        '{"name": "broken", "version": "1.0.0", "scripts": {"build": "exit 1"}}',
        encoding="utf-8",
    )

    result = run_build(tmp_path)

    assert result.passed is False
    assert result.details


@pytest.mark.skipif(not NPM_AVAILABLE, reason="npm not on PATH")
def test_run_build_fails_when_no_package_json(tmp_path):
    result = run_build(tmp_path)

    assert result.passed is False


@pytest.mark.skipif(not NPX_AVAILABLE, reason="npx not on PATH")
def test_run_typecheck_passes_for_valid_typescript(tmp_path):
    _install_typescript(tmp_path)
    (tmp_path / "tsconfig.json").write_text(
        '{"compilerOptions": {"strict": true, "noEmit": true}}', encoding="utf-8"
    )
    (tmp_path / "valid.ts").write_text("const x: number = 1;", encoding="utf-8")

    result = run_typecheck(tmp_path)

    assert result.passed is True, result.details


@pytest.mark.skipif(not NPX_AVAILABLE, reason="npx not on PATH")
def test_run_typecheck_fails_for_type_error(tmp_path):
    _install_typescript(tmp_path)
    (tmp_path / "tsconfig.json").write_text(
        '{"compilerOptions": {"strict": true, "noEmit": true}}', encoding="utf-8"
    )
    (tmp_path / "invalid.ts").write_text(
        'const x: number = "not a number";', encoding="utf-8"
    )

    result = run_typecheck(tmp_path)

    assert result.passed is False
    assert result.details


def test_check_no_hardcoded_design_values_passes_for_tailwind_and_var_usage(tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "component.tsx").write_text(
        'export const X = () => <div className="bg-primary rounded-full" />;',
        encoding="utf-8",
    )
    (src_dir / "styles.css").write_text(
        ".foo { color: var(--color-primary); }", encoding="utf-8"
    )

    result = check_no_hardcoded_design_values(tmp_path)

    assert result.passed is True


def test_check_no_hardcoded_design_values_fails_for_hex_literal(tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "component.tsx").write_text(
        'export const X = () => <div style={{ color: "#0075de" }} />;',
        encoding="utf-8",
    )

    result = check_no_hardcoded_design_values(tmp_path)

    assert result.passed is False
    assert "component.tsx" in result.details


def test_check_no_hardcoded_design_values_ignores_files_outside_src(tmp_path):
    node_modules_dir = tmp_path / "node_modules" / "somedep"
    node_modules_dir.mkdir(parents=True)
    (node_modules_dir / "index.css").write_text(
        ".foo { color: #123456; }", encoding="utf-8"
    )

    result = check_no_hardcoded_design_values(tmp_path)

    assert result.passed is True


def test_check_no_hardcoded_design_values_exempts_theme_css(tmp_path):
    styles_dir = tmp_path / "src" / "styles"
    styles_dir.mkdir(parents=True)
    (styles_dir / "theme.css").write_text(
        "--color-primary: #ff385c;", encoding="utf-8"
    )

    result = check_no_hardcoded_design_values(tmp_path)

    assert result.passed is True


def test_check_no_spacing_scale_width_collisions_fails_for_max_w_sm(tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "component.tsx").write_text(
        'export const X = () => <div className="flex max-w-sm flex-col" />;',
        encoding="utf-8",
    )

    result = check_no_spacing_scale_width_collisions(tmp_path)

    assert result.passed is False
    assert "component.tsx" in result.details
    assert "max-w-sm" in result.details


def test_check_no_spacing_scale_width_collisions_passes_for_arbitrary_value(tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "component.tsx").write_text(
        'export const X = () => <div className="flex max-w-[24rem] flex-col" />;',
        encoding="utf-8",
    )

    result = check_no_spacing_scale_width_collisions(tmp_path)

    assert result.passed is True


def test_check_no_spacing_scale_width_collisions_passes_for_numeric_scale(tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "component.tsx").write_text(
        'export const X = () => <input className="flex h-14 w-full" />;',
        encoding="utf-8",
    )

    result = check_no_spacing_scale_width_collisions(tmp_path)

    assert result.passed is True
