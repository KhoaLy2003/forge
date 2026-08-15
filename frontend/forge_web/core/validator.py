"""Post-generation validation: structural checks, npm build/typecheck shell-outs, and a design-token grep check."""

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ValidationResult:
    """The outcome of one validation check."""

    passed: bool
    message: str
    details: str = ""


def check_structure(target_dir: Path, expected_paths: list[Path]) -> ValidationResult:
    """Check that every expected relative path exists under target_dir."""
    missing = [str(p) for p in expected_paths if not (target_dir / p).exists()]
    if missing:
        return ValidationResult(
            False, "Structural check failed: missing files", "\n".join(missing)
        )
    return ValidationResult(True, "Structural check passed")


def run_build(target_dir: Path, timeout: int = 300) -> ValidationResult:
    """Run `npm install && npm run build` in target_dir."""
    npm_cmd = shutil.which("npm") or "npm"
    for args, label in ([["install"], "npm install"], [["run", "build"], "npm run build"]):
        try:
            result = subprocess.run(
                [npm_cmd, *args],
                cwd=target_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except FileNotFoundError:
            return ValidationResult(False, "npm executable not found on PATH")
        except subprocess.TimeoutExpired:
            return ValidationResult(False, f"{label} timed out after {timeout}s")
        if result.returncode != 0:
            return ValidationResult(False, f"{label} failed", result.stdout + result.stderr)
    return ValidationResult(True, "Build check passed")


def run_typecheck(target_dir: Path, timeout: int = 120) -> ValidationResult:
    """Run `npx tsc --noEmit` in target_dir."""
    npx_cmd = shutil.which("npx") or "npx"
    try:
        result = subprocess.run(
            [npx_cmd, "tsc", "--noEmit"],
            cwd=target_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return ValidationResult(False, "npx executable not found on PATH")
    except subprocess.TimeoutExpired:
        return ValidationResult(False, f"tsc --noEmit timed out after {timeout}s")
    if result.returncode != 0:
        return ValidationResult(False, "tsc --noEmit failed", result.stdout + result.stderr)
    return ValidationResult(True, "Typecheck passed")


HEX_COLOR_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")


def check_no_hardcoded_design_values(target_dir: Path) -> ValidationResult:
    """Fail if any hex color literal appears in .tsx/.ts/.css files under src/, outside theme.css."""
    offenders = []
    src_dir = target_dir / "src"
    for path in src_dir.rglob("*"):
        if path.suffix not in (".tsx", ".ts", ".css") or path.name == "theme.css":
            continue
        text = path.read_text(encoding="utf-8")
        if HEX_COLOR_RE.search(text):
            offenders.append(str(path.relative_to(target_dir)))
    if offenders:
        return ValidationResult(
            False, "Hardcoded design values found outside theme.css", "\n".join(offenders)
        )
    return ValidationResult(True, "Design token check passed")


# Tailwind v4 derives width/max-width/min-width/height utilities (`w-*`,
# `max-w-*`, `min-w-*`, `h-*`, `min-h-*`) from the SAME `--spacing-<key>`
# custom properties used by `p-*`/`gap-*`/etc. Any of these keys defined in
# theme.css's spacing scale (xxs/xs/sm/md/base/lg/xl/xxl/section) silently
# shadows Tailwind's own named max-width scale (e.g. `max-w-sm` normally
# means "24rem", but resolves to our 8px `--spacing-sm` token instead) —
# this produces a working build with no type/lint error, only a broken
# layout at runtime. Use an arbitrary value (`max-w-[24rem]`) instead.
SPACING_SCALE_KEYS = (
    "xxs", "xs", "sm", "md", "base", "lg", "xl", "xxl", "section",
)
WIDTH_UTILITY_COLLISION_RE = re.compile(
    r"\b(?:max-w|min-w|w|max-h|min-h|h)-(" + "|".join(SPACING_SCALE_KEYS) + r")\b"
)


def check_no_spacing_scale_width_collisions(target_dir: Path) -> ValidationResult:
    """Fail if a width/height utility uses one of theme.css's spacing-scale key names."""
    offenders = []
    src_dir = target_dir / "src"
    for path in src_dir.rglob("*"):
        if path.suffix not in (".tsx", ".ts") :
            continue
        text = path.read_text(encoding="utf-8")
        match = WIDTH_UTILITY_COLLISION_RE.search(text)
        if match:
            offenders.append(f"{path.relative_to(target_dir)}: {match.group(0)}")
    if offenders:
        return ValidationResult(
            False,
            "Width/height utility collides with a spacing-scale token name "
            "(use an arbitrary value like max-w-[24rem] instead)",
            "\n".join(offenders),
        )
    return ValidationResult(True, "Width utility collision check passed")
