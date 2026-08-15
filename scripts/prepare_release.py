"""Cut a release: atomically rename `## [Unreleased]` to a versioned heading,
insert a fresh empty `[Unreleased]` section above it, and bump
pyproject.toml's version to match. Edits files only — review and commit/PR
the result through the normal workflow; this script does not touch git.

Usage:
    python scripts/prepare_release.py --package backend --version 0.3.0
"""

from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path

from changelog_lib import (
    read_pyproject_version,
    rename_unreleased,
    unreleased_section,
    write_pyproject_version,
)

REPO_ROOT = Path(__file__).parent.parent


def _parse_version(version: str) -> tuple[int, int, int]:
    parts = version.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise ValueError(f"'{version}' is not a plain X.Y.Z version")
    return tuple(int(p) for p in parts)  # type: ignore[return-value]


def prepare_release(package: str, new_version: str) -> int:
    package_dir = REPO_ROOT / package
    pyproject_path = package_dir / "pyproject.toml"
    changelog_path = package_dir / "CHANGELOG.md"

    current_version = read_pyproject_version(pyproject_path)
    if _parse_version(new_version) <= _parse_version(current_version):
        print(
            f"::error::New version '{new_version}' must be greater than the "
            f"current pyproject.toml version '{current_version}'.",
            file=sys.stderr,
        )
        return 1

    changelog_text = changelog_path.read_text(encoding="utf-8")
    body = unreleased_section(changelog_text)
    if not body:
        print(
            f"::error::{changelog_path} has no '[Unreleased]' section, or it's "
            "empty — nothing to release.",
            file=sys.stderr,
        )
        return 1

    today = datetime.date.today().isoformat()
    new_heading = f"## {new_version} — {today}"

    new_changelog = rename_unreleased(changelog_text, new_heading)
    changelog_path.write_text(new_changelog, encoding="utf-8")

    try:
        write_pyproject_version(pyproject_path, new_version)
    except ValueError as e:
        print(f"::error::{e}", file=sys.stderr)
        return 1

    print(
        f"{package}: bumped {current_version} -> {new_version}, renamed "
        f"[Unreleased] to '{new_heading}', and inserted a fresh empty "
        "[Unreleased] section. Review the diff and commit/PR it normally."
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True, choices=["backend", "frontend"])
    parser.add_argument("--version", required=True, help="New version, e.g. 0.3.0")
    args = parser.parse_args()
    return prepare_release(args.package, args.version)


if __name__ == "__main__":
    raise SystemExit(main())
