import tomllib

import pytest

from changelog_lib import (
    UNRELEASED_HEADING,
    first_version_heading,
    read_pyproject_version,
    rename_unreleased,
    unreleased_section,
    write_pyproject_version,
)

SAMPLE_CHANGELOG = """# Changelog

## [Unreleased]

- one new thing
- another new thing

## 0.2.0 — 2026-08-14

- old entry

## 0.1.0 — 2026-08-13

Initial release.
"""

EMPTY_UNRELEASED_CHANGELOG = """# Changelog

## [Unreleased]

## 0.1.0 — 2026-08-13

Initial release.
"""

NO_PRIOR_VERSION_CHANGELOG = """# Changelog

## [Unreleased]

- first thing ever
"""


def test_first_version_heading_skips_unreleased():
    assert first_version_heading(SAMPLE_CHANGELOG) == "0.2.0"


def test_first_version_heading_returns_none_when_no_released_version():
    assert first_version_heading(NO_PRIOR_VERSION_CHANGELOG) is None


def test_unreleased_section_extracts_body():
    body = unreleased_section(SAMPLE_CHANGELOG)
    assert body == "- one new thing\n- another new thing"


def test_unreleased_section_empty_when_no_bullets():
    assert unreleased_section(EMPTY_UNRELEASED_CHANGELOG) == ""


def test_unreleased_section_empty_when_no_heading():
    assert unreleased_section("# Changelog\n\n## 0.1.0 — 2026-08-13\n") == ""


def test_rename_unreleased_moves_body_and_inserts_fresh_section():
    result = rename_unreleased(SAMPLE_CHANGELOG, "## 0.3.0 — 2026-08-16")

    assert result.startswith(f"{UNRELEASED_HEADING}\n\n## 0.3.0 — 2026-08-16\n\n")
    assert "- one new thing\n- another new thing" in result
    # Old entries are preserved, unchanged, after the newly renamed section.
    assert "## 0.2.0 — 2026-08-14" in result
    assert "## 0.1.0 — 2026-08-13" in result
    # Exactly one [Unreleased] heading remains (the fresh empty one).
    assert result.count(UNRELEASED_HEADING) == 1
    # The new section is genuinely empty (no leftover body before the next heading).
    assert unreleased_section(result) == ""


def test_read_pyproject_version(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "x"\nversion = "1.2.3"\n', encoding="utf-8")
    assert read_pyproject_version(pyproject) == "1.2.3"


def test_write_pyproject_version_round_trips(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "x"\nversion = "1.2.3"\ndependencies = []\n', encoding="utf-8"
    )

    write_pyproject_version(pyproject, "1.3.0")

    assert read_pyproject_version(pyproject) == "1.3.0"
    # Untouched lines survive, and the file stays valid TOML.
    text = pyproject.read_text(encoding="utf-8")
    assert 'name = "x"' in text
    with pyproject.open("rb") as f:
        tomllib.load(f)


def test_write_pyproject_version_raises_when_no_version_line(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "x"\n', encoding="utf-8")

    with pytest.raises(ValueError):
        write_pyproject_version(pyproject, "1.3.0")
