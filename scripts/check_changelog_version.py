"""Fail if CHANGELOG.md's first released version heading doesn't match
pyproject.toml's version.

Usage:
    python scripts/check_changelog_version.py --package backend
    python scripts/check_changelog_version.py --package frontend
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from changelog_lib import first_version_heading, read_pyproject_version

REPO_ROOT = Path(__file__).parent.parent


def check(package: str) -> int:
    package_dir = REPO_ROOT / package
    pyproject_version = read_pyproject_version(package_dir / "pyproject.toml")
    changelog_text = (package_dir / "CHANGELOG.md").read_text(encoding="utf-8")
    changelog_version = first_version_heading(changelog_text)

    if changelog_version is None:
        # No released version heading yet (only `[Unreleased]` exists) —
        # nothing to compare against.
        print(f"{package}: no released CHANGELOG heading yet. OK.")
        return 0

    if changelog_version != pyproject_version:
        print(
            f"::error::{package}/CHANGELOG.md's top version heading "
            f"('{changelog_version}') does not match {package}/pyproject.toml's "
            f"version ('{pyproject_version}'). Run scripts/prepare_release.py, "
            f"or fix the drift manually, before merging.",
            file=sys.stderr,
        )
        return 1

    print(f"{package}: CHANGELOG.md ({changelog_version}) matches pyproject.toml. OK.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True, choices=["backend", "frontend"])
    args = parser.parse_args()
    return check(args.package)


if __name__ == "__main__":
    raise SystemExit(main())
