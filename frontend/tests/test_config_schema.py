from pathlib import Path

import pytest
from pydantic import ValidationError

from forge_web.core.config_schema import ForgeWebConfig, validate_project_name


def make_config(**overrides):
    values = dict(
        project_name="my-dashboard",
        target_path=Path("/tmp/out"),
        api_base_url="http://localhost:8080/api",
        template="base",
    )
    values.update(overrides)
    return ForgeWebConfig(**values)


def test_validate_project_name_accepts_valid_name():
    assert validate_project_name("my-dashboard") == "my-dashboard"


def test_validate_project_name_rejects_uppercase():
    with pytest.raises(ValueError):
        validate_project_name("MyDashboard")


def test_validate_project_name_rejects_leading_digit():
    with pytest.raises(ValueError):
        validate_project_name("1bad")


def test_validate_project_name_rejects_underscore():
    with pytest.raises(ValueError):
        validate_project_name("my_dashboard")


def test_validate_project_name_rejects_trailing_hyphen():
    with pytest.raises(ValueError):
        validate_project_name("my-")


def test_validate_project_name_rejects_consecutive_hyphens():
    with pytest.raises(ValueError):
        validate_project_name("a--b")


def test_valid_config_accepted():
    config = make_config()
    assert config.project_name == "my-dashboard"


def test_target_dir_is_target_path_joined_with_project_name():
    config = make_config()
    assert config.target_dir == Path("/tmp/out/my-dashboard")


def test_app_display_name_is_title_cased_with_spaces():
    config = make_config(project_name="my-dashboard")
    assert config.app_display_name == "My Dashboard"


def test_template_context_has_expected_keys_and_values():
    config = make_config()
    context = config.template_context()
    assert context == {
        "project_name": "my-dashboard",
        "app_display_name": "My Dashboard",
        "api_base_url": "http://localhost:8080/api",
        "template": "base",
        "include_data_fetching": True,
    }


def test_invalid_project_name_rejected():
    with pytest.raises(ValidationError):
        make_config(project_name="1bad")


def test_template_context_includes_include_data_fetching_flag_true_for_base():
    config = make_config(template="base")
    assert config.template_context()["include_data_fetching"] is True


def test_template_context_includes_include_data_fetching_flag_false_for_minimal():
    config = make_config(template="minimal")
    assert config.template_context()["include_data_fetching"] is False


def test_unknown_template_raises_validation_error():
    with pytest.raises(ValidationError):
        make_config(template="nonexistent")
