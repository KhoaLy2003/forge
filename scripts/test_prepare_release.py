import pytest

import prepare_release


def _write_package(tmp_path, changelog_body, pyproject_version):
    package_dir = tmp_path / "backend"
    package_dir.mkdir()
    (package_dir / "CHANGELOG.md").write_text(changelog_body, encoding="utf-8")
    (package_dir / "pyproject.toml").write_text(
        f'[project]\nname = "x"\nversion = "{pyproject_version}"\n', encoding="utf-8"
    )
    return package_dir


def test_prepare_release_bumps_version_and_renames_section(tmp_path, monkeypatch):
    package_dir = _write_package(
        tmp_path,
        "# Changelog\n\n## [Unreleased]\n\n- new thing\n\n## 0.2.0 — 2026-08-14\n\nold\n",
        "0.2.0",
    )
    monkeypatch.setattr(prepare_release, "REPO_ROOT", tmp_path)

    assert prepare_release.prepare_release("backend", "0.3.0") == 0

    pyproject_text = (package_dir / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "0.3.0"' in pyproject_text

    changelog_text = (package_dir / "CHANGELOG.md").read_text(encoding="utf-8")
    assert changelog_text.count("## [Unreleased]") == 1
    assert "- new thing" in changelog_text
    assert "## 0.2.0 — 2026-08-14" in changelog_text
    assert "old" in changelog_text
    # New heading present with today's date format (a version + em dash + digits).
    import re

    assert re.search(r"## 0\.3\.0 — \d{4}-\d{2}-\d{2}", changelog_text)


def test_prepare_release_rejects_empty_unreleased_section(tmp_path, monkeypatch, capsys):
    _write_package(
        tmp_path,
        "# Changelog\n\n## [Unreleased]\n\n## 0.1.0 — 2026-08-13\n\nold\n",
        "0.1.0",
    )
    monkeypatch.setattr(prepare_release, "REPO_ROOT", tmp_path)

    assert prepare_release.prepare_release("backend", "0.2.0") == 1
    assert "nothing to release" in capsys.readouterr().err


def test_prepare_release_rejects_non_increasing_version(tmp_path, monkeypatch, capsys):
    _write_package(
        tmp_path,
        "# Changelog\n\n## [Unreleased]\n\n- thing\n",
        "0.2.0",
    )
    monkeypatch.setattr(prepare_release, "REPO_ROOT", tmp_path)

    assert prepare_release.prepare_release("backend", "0.2.0") == 1
    assert "must be greater than" in capsys.readouterr().err


@pytest.mark.parametrize("bad_version", ["1.2", "1.2.3.4", "1.2.x", "v1.2.3"])
def test_parse_version_rejects_malformed_input(bad_version):
    with pytest.raises(ValueError):
        prepare_release._parse_version(bad_version)
