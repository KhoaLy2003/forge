"""Interactive wizard that fills in missing ForgeConfig parameters, reprompting on invalid input."""

from pathlib import Path

from core.config_schema import (
    ForgeConfig,
    validate_artifact_id,
    validate_group_id,
    validate_project_name,
)

FIELD_PROMPTS = [
    ("project_name", "Project name", validate_project_name),
    ("target_path", "Target path (parent directory)", None),
    ("group_id", "Group id (e.g. com.example)", validate_group_id),
    ("artifact_id", "Artifact id (e.g. my-service)", validate_artifact_id),
]


def _prompt_field(label, validator, prompt_fn):
    """Prompt for one field, reprompting until the validator accepts the input."""
    while True:
        raw = prompt_fn(f"{label}: ").strip()
        if validator is None:
            return raw
        try:
            return validator(raw)
        except ValueError as exc:
            print(f"Invalid value: {exc}")


def collect_params(overrides: dict, prompt_fn=input) -> ForgeConfig:
    """Fill in any missing parameters via prompts and return a validated ForgeConfig."""
    values = dict(overrides)
    for field, label, validator in FIELD_PROMPTS:
        if values.get(field) in (None, ""):
            values[field] = _prompt_field(label, validator, prompt_fn)
    values["target_path"] = Path(values["target_path"]).expanduser().resolve()
    return ForgeConfig(**values)
