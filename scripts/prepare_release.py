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
import subprocess
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


def _check_up_to_date_with_origin_main(repo_root: Path) -> str | None:
    """Return an error message if the local checkout is behind origin/main,
    None if it's up to date or the check can't be meaningfully performed
    (not a git repo, no network, no configured remote — all best-effort:
    this is a safety net, not a hard requirement).

    Rationale: prepare_release.py reads/writes CHANGELOG.md and
    pyproject.toml purely from local disk. If the local checkout is stale
    (missing a just-merged PR's [Unreleased] entry) when this runs, that
    entry silently gets misfiled under the new version heading rather than
    staying in the fresh [Unreleased] section once merged back — a real,
    silent-correctness bug found by simulating concurrent release-prep and
    ordinary PRs. Refusing to run on a stale checkout closes the actual
    root cause instead of trying to detect the malformed output after the
    fact, which isn't reliably possible from a single file snapshot.
    """
    def _run(args: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            args, cwd=repo_root, capture_output=True, text=True, timeout=15
        )

    is_repo = _run(["git", "rev-parse", "--is-inside-work-tree"])
    if is_repo.returncode != 0:
        return None  # not a git checkout (e.g. under test) — nothing to check

    fetch = _run(["git", "fetch", "origin", "main", "--quiet"])
    if fetch.returncode != 0:
        print(
            "::warning::Could not fetch origin/main to check freshness "
            f"(offline? no remote?) — proceeding without this safety check.\n"
            f"{fetch.stderr.strip()}",
            file=sys.stderr,
        )
        return None

    up_to_date = _run(["git", "merge-base", "--is-ancestor", "origin/main", "HEAD"])
    if up_to_date.returncode == 0:
        return None
    if up_to_date.returncode == 1:
        return (
            "Local checkout is behind origin/main. Run `git pull` (or merge/"
            "rebase origin/main) before cutting a release, so this doesn't "
            "silently miss a just-merged [Unreleased] entry."
        )
    # Any other exit code (e.g. no origin/main ref at all) — can't determine.
    return None


def prepare_release(package: str, new_version: str, skip_freshness_check: bool = False) -> int:
    package_dir = REPO_ROOT / package
    pyproject_path = package_dir / "pyproject.toml"
    changelog_path = package_dir / "CHANGELOG.md"

    if not skip_freshness_check:
        staleness = _check_up_to_date_with_origin_main(REPO_ROOT)
        if staleness:
            print(f"::error::{staleness}", file=sys.stderr)
            return 1

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
    parser.add_argument(
        "--skip-freshness-check",
        action="store_true",
        help="Skip the origin/main up-to-date check (e.g. for offline use).",
    )
    args = parser.parse_args()
    return prepare_release(args.package, args.version, args.skip_freshness_check)


if __name__ == "__main__":
    raise SystemExit(main())
