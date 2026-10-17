from pathlib import Path

import pytest

from core.project_config import MissingConfigError, build_config, write_starter
from core.entity_spec import load_forge_yaml

VALID = """\
project_name: order-service
target_path: {target}
group_id: com.example
artifact_id: order-service
"""


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "forge.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_complete_file_builds_config(tmp_path):
    path = _write(tmp_path, VALID.format(target=tmp_path.as_posix()))
    config = build_config(path)
    assert config.project_name == "order-service"
    assert config.group_id == "com.example"
    assert config.artifact_id == "order-service"
    assert config.template == "base-layered"


def test_target_path_is_resolved(tmp_path):
    path = _write(tmp_path, VALID.format(target="./sub"))
    config = build_config(path)
    assert config.target_path.is_absolute()


def test_missing_required_key_is_named(tmp_path):
    text = VALID.format(target=tmp_path.as_posix()).replace("group_id: com.example\n", "")
    with pytest.raises(ValueError, match="group_id"):
        build_config(_write(tmp_path, text))


def test_empty_file_lists_all_required_keys(tmp_path):
    path = _write(tmp_path, "")
    with pytest.raises(ValueError) as exc:
        build_config(path)
    for key in ("project_name", "target_path", "group_id", "artifact_id"):
        assert key in str(exc.value)


def test_unknown_key_is_rejected(tmp_path):
    text = VALID.format(target=tmp_path.as_posix()) + "groupId: com.x\n"
    with pytest.raises(ValueError, match="groupId"):
        build_config(_write(tmp_path, text))


def test_invalid_project_name_is_rejected(tmp_path):
    text = VALID.format(target=tmp_path.as_posix()).replace("order-service", "My_Service", 1)
    with pytest.raises(ValueError, match="project_name"):
        build_config(_write(tmp_path, text))


def test_missing_file_raises_missing_config_error(tmp_path):
    with pytest.raises(MissingConfigError):
        build_config(tmp_path / "forge.yaml")


def test_write_starter_creates_loadable_file(tmp_path):
    path = tmp_path / "forge.yaml"
    write_starter(path)
    assert path.exists()
    load_forge_yaml(path)  # must parse with the same loader used by build_config


def test_write_starter_refuses_to_overwrite(tmp_path):
    path = _write(tmp_path, "project_name: keep-me\n")
    with pytest.raises(FileExistsError, match="forge.yaml"):
        write_starter(path)
    assert path.read_text(encoding="utf-8") == "project_name: keep-me\n"


def test_starter_entity_example_is_valid_once_uncommented(tmp_path):
    from core.project_config import STARTER_TEMPLATE

    lines, in_example = [], False
    for line in STARTER_TEMPLATE.splitlines():
        if line.startswith("# entities:"):
            in_example = True
            lines.append("entities:")
        elif in_example and line.startswith("#"):
            lines.append(line[2:] if line.startswith("# ") else "")
        else:
            lines.append(line)
    text = "\n".join(lines).replace("target_path: .", f"target_path: {tmp_path.as_posix()}")
    config = build_config(_write(tmp_path, text))
    assert set(config.entities) == {"Customer", "Invoice"}
