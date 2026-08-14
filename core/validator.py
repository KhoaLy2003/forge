"""Post-generation validation: structural file checks and a real `mvn compile` shell-out."""

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


def run_compile(target_dir: Path, timeout: int = 300) -> ValidationResult:
    """Run `mvn compile` in target_dir and report whether it succeeded."""
    mvn_cmd = shutil.which("mvn") or "mvn"
    try:
        result = subprocess.run(
            [mvn_cmd, "-q", "compile"],
            cwd=target_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return ValidationResult(False, "mvn executable not found on PATH")
    except subprocess.TimeoutExpired:
        return ValidationResult(False, f"mvn compile timed out after {timeout}s")

    if result.returncode != 0:
        return ValidationResult(
            False, "mvn compile failed", result.stdout + result.stderr
        )
    return ValidationResult(True, "Compile check passed")
