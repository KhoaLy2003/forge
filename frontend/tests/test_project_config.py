from pathlib import Path

import pytest

from forge_web.core.project_config import MissingConfigError, build_config, write_starter

VALID = """\
project_name: my-dashboard
target_path: {target}
api_base_url: http://localhost:8080/api
"""


def _write(folder: Path, text: str) -> Path:
    path = folder / "forge-web.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_complete_file_builds_config(tmp_path):
    config = build_config(_write(tmp_path, VALID.format(target=tmp_path.as_posix())))
    assert config.project_name == "my-dashboard"
    assert config.api_base_url == "http://localhost:8080/api"
    assert config.template == "base"


def test_template_minimal_is_honored(tmp_path):
    text = VALID.format(target=tmp_path.as_posix()) + "template: minimal\n"
    assert build_config(_write(tmp_path, text)).template == "minimal"


def test_target_path_is_resolved(tmp_path):
    config = build_config(_write(tmp_path, VALID.format(target="./sub")))
    assert config.target_path.is_absolute()


def test_missing_required_key_is_named(tmp_path):
    text = VALID.format(target=tmp_path.as_posix()).replace("api_base_url: http://localhost:8080/api\n", "")
    with pytest.raises(ValueError, match="api_base_url"):
        build_config(_write(tmp_path, text))


def test_empty_file_lists_all_required_keys(tmp_path):
    with pytest.raises(ValueError) as exc:
        build_config(_write(tmp_path, ""))
    for key in ("project_name", "target_path", "api_base_url"):
        assert key in str(exc.value)


def test_unknown_key_is_rejected_by_name(tmp_path):
    text = VALID.format(target=tmp_path.as_posix()) + "apiBaseUrl: http://x\n"
    with pytest.raises(ValueError, match="apiBaseUrl"):
        build_config(_write(tmp_path, text))


def test_invalid_project_name_is_rejected(tmp_path):
    text = VALID.format(target=tmp_path.as_posix()).replace("my-dashboard", "My_Dash", 1)
    with pytest.raises(ValueError, match="project_name"):
        build_config(_write(tmp_path, text))


def test_invalid_template_is_rejected(tmp_path):
    text = VALID.format(target=tmp_path.as_posix()) + "template: nope\n"
    with pytest.raises(ValueError, match="template"):
        build_config(_write(tmp_path, text))


def test_missing_file_raises_missing_config_error(tmp_path):
    with pytest.raises(MissingConfigError):
        build_config(tmp_path / "forge-web.yaml")


def test_starter_is_valid_once_placeholders_are_set(tmp_path):
    path = tmp_path / "forge-web.yaml"
    write_starter(path)
    text = path.read_text(encoding="utf-8").replace("target_path: .", f"target_path: {tmp_path.as_posix()}")
    path.write_text(text, encoding="utf-8")
    config = build_config(path)
    assert config.project_name == "my-app"


def test_write_starter_refuses_to_overwrite(tmp_path):
    path = _write(tmp_path, "project_name: keep-me\n")
    with pytest.raises(FileExistsError, match="forge-web.yaml"):
        write_starter(path)
    assert path.read_text(encoding="utf-8") == "project_name: keep-me\n"
