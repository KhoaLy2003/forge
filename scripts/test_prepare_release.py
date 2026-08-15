import subprocess

import pytest

import prepare_release


def _git(repo_dir, *args):
    subprocess.run(["git", "-C", str(repo_dir), *args], check=True, capture_output=True)


def _init_remote_and_clone(tmp_path):
    """Bare `remote.git` plus a `local` clone with one commit on main, both
    pushed. Returns (remote_dir, local_dir).
    """
    remote_dir = tmp_path / "remote.git"
    local_dir = tmp_path / "local"
    _git(tmp_path, "init", "--bare", "-b", "main", str(remote_dir))
    _git(tmp_path, "clone", str(remote_dir), str(local_dir))
    _git(local_dir, "config", "user.email", "test@example.com")
    _git(local_dir, "config", "user.name", "Test")
    (local_dir / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(local_dir, "add", "seed.txt")
    _git(local_dir, "commit", "-m", "seed")
    _git(local_dir, "push", "origin", "main")
    return remote_dir, local_dir


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


def test_freshness_check_returns_none_for_non_git_directory(tmp_path):
    assert prepare_release._check_up_to_date_with_origin_main(tmp_path) is None


def test_freshness_check_passes_when_up_to_date(tmp_path):
    _, local_dir = _init_remote_and_clone(tmp_path)
    assert prepare_release._check_up_to_date_with_origin_main(local_dir) is None


def test_freshness_check_detects_stale_checkout(tmp_path):
    remote_dir, local_dir = _init_remote_and_clone(tmp_path)

    # A second clone represents the maintainer's checkout that's about to go stale.
    stale_dir = tmp_path / "stale"
    _git(tmp_path, "clone", str(remote_dir), str(stale_dir))

    # Someone else's PR merges to the real origin/main after the clone...
    _git(local_dir, "config", "user.email", "test@example.com")
    _git(local_dir, "config", "user.name", "Test")
    (local_dir / "other.txt").write_text("other PR\n", encoding="utf-8")
    _git(local_dir, "add", "other.txt")
    _git(local_dir, "commit", "-m", "a PR the stale checkout doesn't have")
    _git(local_dir, "push", "origin", "main")

    message = prepare_release._check_up_to_date_with_origin_main(stale_dir)
    assert message is not None
    assert "behind origin/main" in message


def test_prepare_release_blocks_on_stale_checkout(tmp_path, monkeypatch, capsys):
    remote_dir, local_dir = _init_remote_and_clone(tmp_path)
    stale_dir = tmp_path / "stale"
    _git(tmp_path, "clone", str(remote_dir), str(stale_dir))
    _git(local_dir, "config", "user.email", "test@example.com")
    _git(local_dir, "config", "user.name", "Test")
    (local_dir / "other.txt").write_text("other PR\n", encoding="utf-8")
    _git(local_dir, "add", "other.txt")
    _git(local_dir, "commit", "-m", "a PR the stale checkout doesn't have")
    _git(local_dir, "push", "origin", "main")

    _write_package(
        stale_dir,
        "# Changelog\n\n## [Unreleased]\n\n- thing\n",
        "0.2.0",
    )
    monkeypatch.setattr(prepare_release, "REPO_ROOT", stale_dir)

    assert prepare_release.prepare_release("backend", "0.3.0") == 1
    assert "behind origin/main" in capsys.readouterr().err


def test_prepare_release_skip_freshness_check_bypasses_staleness(tmp_path, monkeypatch):
    remote_dir, local_dir = _init_remote_and_clone(tmp_path)
    stale_dir = tmp_path / "stale"
    _git(tmp_path, "clone", str(remote_dir), str(stale_dir))
    _git(local_dir, "config", "user.email", "test@example.com")
    _git(local_dir, "config", "user.name", "Test")
    (local_dir / "other.txt").write_text("other PR\n", encoding="utf-8")
    _git(local_dir, "add", "other.txt")
    _git(local_dir, "commit", "-m", "a PR the stale checkout doesn't have")
    _git(local_dir, "push", "origin", "main")

    _write_package(
        stale_dir,
        "# Changelog\n\n## [Unreleased]\n\n- thing\n",
        "0.2.0",
    )
    monkeypatch.setattr(prepare_release, "REPO_ROOT", stale_dir)

    assert prepare_release.prepare_release("backend", "0.3.0", skip_freshness_check=True) == 0
