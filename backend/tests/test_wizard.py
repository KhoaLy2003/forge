from pathlib import Path

from core.wizard import collect_params


def test_collect_params_uses_overrides_without_prompting():
    def fail_if_called(_label):
        raise AssertionError("prompt_fn should not be called")

    config = collect_params(
        {
            "project_name": "demo-service",
            "target_path": "/tmp/out",
            "group_id": "com.example",
            "artifact_id": "demo-service",
        },
        prompt_fn=fail_if_called,
    )
    assert config.project_name == "demo-service"
    assert config.target_path == Path("/tmp/out").resolve()


def test_collect_params_prompts_for_missing_fields():
    responses = iter(["demo-service", "/tmp/out", "com.example", "demo-service"])
    config = collect_params({}, prompt_fn=lambda _label: next(responses))
    assert config.group_id == "com.example"
    assert config.artifact_id == "demo-service"


def test_collect_params_reprompts_on_invalid_group_id():
    responses = iter(
        ["demo-service", "/tmp/out", "BAD_GROUP", "com.example", "demo-service"]
    )
    config = collect_params({}, prompt_fn=lambda _label: next(responses))
    assert config.group_id == "com.example"


def test_collect_params_mixes_overrides_and_prompts():
    responses = iter(["/tmp/out", "com.example"])
    config = collect_params(
        {"project_name": "demo-service", "artifact_id": "demo-service"},
        prompt_fn=lambda _label: next(responses),
    )
    assert config.target_path == Path("/tmp/out").resolve()
    assert config.group_id == "com.example"


def test_collect_params_resolves_relative_target_path():
    config = collect_params(
        {
            "project_name": "demo-service",
            "target_path": "some/relative/dir",
            "group_id": "com.example",
            "artifact_id": "demo-service",
        },
        prompt_fn=lambda _label: (_ for _ in ()).throw(
            AssertionError("prompt_fn should not be called")
        ),
    )
    assert config.target_path.is_absolute()
    assert config.target_path == Path("some/relative/dir").resolve()


def test_collect_params_expands_home_in_target_path():
    config = collect_params(
        {
            "project_name": "demo-service",
            "target_path": "~/somedir",
            "group_id": "com.example",
            "artifact_id": "demo-service",
        },
        prompt_fn=lambda _label: (_ for _ in ()).throw(
            AssertionError("prompt_fn should not be called")
        ),
    )
    assert "~" not in str(config.target_path)
    assert config.target_path == Path("~/somedir").expanduser().resolve()
