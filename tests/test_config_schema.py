from pathlib import Path

import pytest
from pydantic import ValidationError

from core.config_schema import (
    ForgeConfig,
    validate_artifact_id,
    validate_group_id,
    validate_project_name,
)


def make_config(**overrides):
    values = dict(
        project_name="demo-service",
        target_path=Path("/tmp/out"),
        group_id="com.example",
        artifact_id="demo-service",
    )
    values.update(overrides)
    return ForgeConfig(**values)


def test_valid_config_accepted():
    config = make_config()
    assert config.project_name == "demo-service"


def test_target_dir_is_target_path_joined_with_project_name():
    config = make_config()
    assert config.target_dir == Path("/tmp/out/demo-service")


def test_base_package_strips_hyphens_from_artifact_id():
    config = make_config(group_id="com.example", artifact_id="demo-service")
    assert config.base_package == "com.example.demoservice"


def test_package_path_replaces_dots_with_slashes():
    config = make_config(group_id="com.example", artifact_id="demo-service")
    assert config.package_path == "com/example/demoservice"


def test_app_class_name_is_pascal_case_without_application_suffix():
    config = make_config(artifact_id="demo-service")
    assert config.app_class_name == "DemoService"


def test_template_context_has_expected_keys():
    config = make_config()
    context = config.template_context()
    assert set(context) == {
        "project_name",
        "group_id",
        "artifact_id",
        "base_package",
        "package_path",
        "app_class_name",
    }


def test_invalid_project_name_rejected():
    with pytest.raises(ValidationError):
        make_config(project_name="Not_Valid!")


def test_invalid_group_id_rejected():
    with pytest.raises(ValidationError):
        make_config(group_id="Com.Example")


def test_invalid_artifact_id_rejected():
    with pytest.raises(ValidationError):
        make_config(artifact_id="Not Valid")


def test_validate_project_name_raises_value_error_with_message():
    with pytest.raises(ValueError, match="lowercase"):
        validate_project_name("Bad Name")


def test_validate_group_id_raises_value_error_with_message():
    with pytest.raises(ValueError, match="dot-separated"):
        validate_group_id("BAD")


def test_validate_artifact_id_raises_value_error_with_message():
    with pytest.raises(ValueError, match="lowercase"):
        validate_artifact_id("Bad Name")


def test_validate_group_id_rejects_reserved_java_keyword():
    with pytest.raises(ValueError, match="reserved"):
        validate_group_id("com.new")


def test_validate_group_id_accepts_non_reserved_segments():
    assert validate_group_id("com.example") == "com.example"


def test_validate_artifact_id_rejects_reserved_java_keyword():
    with pytest.raises(ValueError, match="reserved"):
        validate_artifact_id("class")


def test_validate_artifact_id_accepts_non_reserved_id():
    assert validate_artifact_id("my-service") == "my-service"


def test_validate_artifact_id_accepts_id_that_is_only_reserved_before_hyphen_strip():
    # "my-class" strips to "myclass", which is not a reserved word.
    assert validate_artifact_id("my-class") == "my-class"
