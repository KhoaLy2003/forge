from pathlib import Path

from forge_web.core.wizard import collect_params


def test_collect_params_uses_overrides_without_prompting():
    def fail_if_called(_label):
        raise AssertionError("prompt_fn should not be called")

    config = collect_params(
        {
            "project_name": "my-dashboard",
            "target_path": "/tmp/out",
            "api_base_url": "http://localhost:8080/api",
            "template": "base",
        },
        prompt_fn=fail_if_called,
    )
    assert config.project_name == "my-dashboard"
    assert config.target_path == Path("/tmp/out").resolve()


def test_collect_params_prompts_for_missing_fields():
    responses = iter(["my-dashboard", "/tmp/out", "http://localhost:8080/api"])
    config = collect_params({}, prompt_fn=lambda _label: next(responses))
    assert config.project_name == "my-dashboard"
    assert config.api_base_url == "http://localhost:8080/api"


def test_collect_params_reprompts_on_invalid_project_name():
    responses = iter(
        ["BAD_NAME", "my-dashboard", "/tmp/out", "http://localhost:8080/api"]
    )
    config = collect_params({}, prompt_fn=lambda _label: next(responses))
    assert config.project_name == "my-dashboard"


def test_collect_params_mixes_overrides_and_prompts():
    responses = iter(["/tmp/out", "http://localhost:8080/api"])
    config = collect_params(
        {"project_name": "my-dashboard"},
        prompt_fn=lambda _label: next(responses),
    )
    assert config.target_path == Path("/tmp/out").resolve()
    assert config.api_base_url == "http://localhost:8080/api"


def test_collect_params_resolves_relative_target_path():
    config = collect_params(
        {
            "project_name": "my-dashboard",
            "target_path": "some/relative/dir",
            "api_base_url": "http://localhost:8080/api",
            "template": "base",
        },
        prompt_fn=lambda _label: (_ for _ in ()).throw(
            AssertionError("prompt_fn should not be called")
        ),
    )
    assert config.target_path.is_absolute()
    assert config.target_path == Path("some/relative/dir").resolve()


def test_collect_params_defaults_template_when_omitted():
    """`template` is deliberately NOT wizard-prompted (see cli.py's --template default) —
    omitting it from overrides falls through to ForgeWebConfig's own default so existing
    flag-complete, non-interactive invocations aren't newly blocked on a prompt."""
    config = collect_params(
        {
            "project_name": "my-dashboard",
            "target_path": "/tmp/out",
            "api_base_url": "http://localhost:8080/api",
        },
        prompt_fn=lambda _label: (_ for _ in ()).throw(
            AssertionError("prompt_fn should not be called")
        ),
    )
    assert config.template == "base"


def test_collect_params_reprompts_on_empty_answer_for_validatorless_field():
    api_base_url_calls = []

    def prompt_fn(label):
        if label.startswith("API base URL"):
            api_base_url_calls.append(label)
            if len(api_base_url_calls) == 1:
                return ""
            return "http://localhost:8080/api"
        if label.startswith("Project name"):
            return "my-dashboard"
        if label.startswith("Target path"):
            return "/tmp/out"
        raise AssertionError(f"unexpected label: {label}")

    config = collect_params({}, prompt_fn=prompt_fn)
    assert len(api_base_url_calls) == 2
    assert config.api_base_url == "http://localhost:8080/api"


def test_collect_params_expands_home_in_target_path():
    config = collect_params(
        {
            "project_name": "my-dashboard",
            "target_path": "~/somedir",
            "api_base_url": "http://localhost:8080/api",
            "template": "base",
        },
        prompt_fn=lambda _label: (_ for _ in ()).throw(
            AssertionError("prompt_fn should not be called")
        ),
    )
    assert "~" not in str(config.target_path)
    assert config.target_path == Path("~/somedir").expanduser().resolve()
