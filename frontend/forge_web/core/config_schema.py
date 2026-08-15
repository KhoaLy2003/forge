"""Parameter schema for a Forge Web run: validation rules and the single source of truth for template context."""

import re
from pathlib import Path

from pydantic import BaseModel, field_validator

PROJECT_NAME_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")


def validate_project_name(value: str) -> str:
    """Validate a project name is lowercase letters/digits, hyphen-separated, starting with a letter, with no leading/trailing/consecutive hyphens."""
    if not PROJECT_NAME_RE.match(value):
        raise ValueError(
            "must be lowercase letters, digits, or single hyphens between segments, "
            "starting with a letter, with no leading/trailing/consecutive hyphens"
        )
    return value


class ForgeWebConfig(BaseModel):
    """Validated parameters for one Forge Web generation run, plus derived template values."""

    project_name: str
    target_path: Path
    api_base_url: str

    @field_validator("project_name")
    @classmethod
    def _check_project_name(cls, v: str) -> str:
        return validate_project_name(v)

    @property
    def target_dir(self) -> Path:
        """The full directory the project will be generated into."""
        return self.target_path / self.project_name

    @property
    def app_display_name(self) -> str:
        """The human-readable app name derived from the project name."""
        return " ".join(part.capitalize() for part in self.project_name.split("-"))

    def template_context(self) -> dict:
        """Build the Jinja2 rendering context used by the template renderer."""
        return {
            "project_name": self.project_name,
            "app_display_name": self.app_display_name,
            "api_base_url": self.api_base_url,
        }
