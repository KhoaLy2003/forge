"""Interactive wizard that fills in missing ForgeWebConfig parameters, reprompting on invalid input."""

from pathlib import Path

from forge_web.core.config_schema import ForgeWebConfig, validate_project_name

FIELD_PROMPTS = [
    ("project_name", "Project name", validate_project_name),
    ("target_path", "Target path (parent directory)", None),
    ("api_base_url", "API base URL (e.g. http://localhost:8080/api)", None),
]


def _prompt_field(label, validator, prompt_fn):
    """Prompt for one field, reprompting until the validator accepts the input."""
    while True:
        raw = prompt_fn(f"{label}: ").strip()
        if validator is None:
            if raw == "":
                continue
            return raw
        try:
            return validator(raw)
        except ValueError as exc:
            print(f"Invalid value: {exc}")


def collect_params(overrides: dict, prompt_fn=input) -> ForgeWebConfig:
    """Fill in any missing parameters via prompts and return a validated ForgeWebConfig."""
    values = dict(overrides)
    for field, label, validator in FIELD_PROMPTS:
        if values.get(field) in (None, ""):
            values[field] = _prompt_field(label, validator, prompt_fn)
    values["target_path"] = Path(values["target_path"]).expanduser().resolve()
    return ForgeWebConfig(**values)
