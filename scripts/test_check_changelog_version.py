import check_changelog_version


def _write_package(tmp_path, changelog_body, pyproject_version):
    package_dir = tmp_path / "backend"
    package_dir.mkdir()
    (package_dir / "CHANGELOG.md").write_text(changelog_body, encoding="utf-8")
    (package_dir / "pyproject.toml").write_text(
        f'[project]\nname = "x"\nversion = "{pyproject_version}"\n', encoding="utf-8"
    )
    return package_dir


def test_check_passes_when_versions_match(tmp_path, monkeypatch):
    _write_package(
        tmp_path,
        "# Changelog\n\n## [Unreleased]\n\n## 0.2.0 — 2026-08-14\n\nstuff\n",
        "0.2.0",
    )
    monkeypatch.setattr(check_changelog_version, "REPO_ROOT", tmp_path)
    assert check_changelog_version.check("backend") == 0


def test_check_fails_when_versions_drift(tmp_path, monkeypatch, capsys):
    _write_package(
        tmp_path,
        "# Changelog\n\n## [Unreleased]\n\n## 0.3.0 — 2026-08-15\n\nstuff\n",
        "0.2.0",
    )
    monkeypatch.setattr(check_changelog_version, "REPO_ROOT", tmp_path)
    assert check_changelog_version.check("backend") == 1
    assert "does not match" in capsys.readouterr().err


def test_check_passes_when_no_released_version_yet(tmp_path, monkeypatch):
    _write_package(
        tmp_path,
        "# Changelog\n\n## [Unreleased]\n\n- something\n",
        "0.1.0",
    )
    monkeypatch.setattr(check_changelog_version, "REPO_ROOT", tmp_path)
    assert check_changelog_version.check("backend") == 0
