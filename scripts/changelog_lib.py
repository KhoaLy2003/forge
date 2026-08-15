"""Shared parsing helpers for CHANGELOG.md / pyproject.toml version handling.

Both packages' CHANGELOG.md follow the same Keep-a-Changelog-style shape:

    # Changelog

    ## [Unreleased]

    - ...bullets, no version number, no date...

    ## 1.2.3 — 2026-08-15

    - ...released entries...

The `[Unreleased]` heading is always present and always first; a real
version heading (`## X.Y.Z — YYYY-MM-DD`) never carries a date until it's
actually been renamed at release time by `prepare_release.py`.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

UNRELEASED_HEADING = "## [Unreleased]"
VERSION_HEADING_RE = re.compile(r"^## (\d+\.\d+\.\d+)(?: — .*)?$", re.MULTILINE)
PYPROJECT_VERSION_RE = re.compile(r'^version = "([^"]+)"$', re.MULTILINE)


def read_pyproject_version(pyproject_path: Path) -> str:
    with pyproject_path.open("rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


def write_pyproject_version(pyproject_path: Path, new_version: str) -> None:
    text = pyproject_path.read_text(encoding="utf-8")
    new_text, count = PYPROJECT_VERSION_RE.subn(
        f'version = "{new_version}"', text, count=1
    )
    if count != 1:
        raise ValueError(f'No `version = "..."` line found in {pyproject_path}')
    pyproject_path.write_text(new_text, encoding="utf-8")


def first_version_heading(changelog_text: str) -> str | None:
    """Return the first `## X.Y.Z` heading's version, skipping `[Unreleased]`.

    Returns None if the changelog has no released version heading yet (e.g.
    right after init, before anything has ever been cut).
    """
    match = VERSION_HEADING_RE.search(changelog_text)
    return match.group(1) if match else None


def unreleased_bounds(changelog_text: str) -> tuple[int, int]:
    """Return the (start, end) char offsets of the `[Unreleased]` section body
    (the text strictly between its heading line and the next version heading,
    or end-of-file). Raises ValueError if there's no `[Unreleased]` heading.
    """
    heading_start = changelog_text.find(UNRELEASED_HEADING)
    if heading_start == -1:
        raise ValueError(f"No '{UNRELEASED_HEADING}' heading found")
    body_start = heading_start + len(UNRELEASED_HEADING)
    next_heading = VERSION_HEADING_RE.search(changelog_text, pos=body_start)
    body_end = next_heading.start() if next_heading else len(changelog_text)
    return body_start, body_end


def unreleased_section(changelog_text: str) -> str:
    """Return the raw, trimmed body of the `[Unreleased]` section, or ''."""
    try:
        start, end = unreleased_bounds(changelog_text)
    except ValueError:
        return ""
    return changelog_text[start:end].strip()


def rename_unreleased(changelog_text: str, new_heading: str) -> str:
    """Return changelog text with `[Unreleased]`'s body moved under
    `new_heading`, and a fresh empty `[Unreleased]` section inserted above it.
    """
    start, end = unreleased_bounds(changelog_text)
    body = changelog_text[start:end].strip()
    rest = changelog_text[end:]
    return f"{UNRELEASED_HEADING}\n\n{new_heading}\n\n{body}\n\n{rest}"
