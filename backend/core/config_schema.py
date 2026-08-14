"""Parameter schema for a Forge run: validation rules and the single source of truth for template context."""

import re
from pathlib import Path

from pydantic import BaseModel, field_validator

PROJECT_NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")
GROUP_ID_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$")
ARTIFACT_ID_RE = re.compile(r"^[a-z][a-z0-9-]*$")

JAVA_RESERVED_WORDS = frozenset(
    {
        "abstract", "assert", "boolean", "break", "byte", "case", "catch",
        "char", "class", "const", "continue", "default", "do", "double",
        "else", "enum", "extends", "final", "finally", "float", "for",
        "goto", "if", "implements", "import", "instanceof", "int",
        "interface", "long", "native", "new", "package", "private",
        "protected", "public", "return", "short", "static", "strictfp",
        "super", "switch", "synchronized", "this", "throw", "throws",
        "transient", "try", "void", "volatile", "while", "true", "false",
        "null", "var", "record", "yield", "sealed", "permits",
    }
)


def validate_project_name(value: str) -> str:
    """Validate a project name is lowercase letters/digits/hyphens starting with a letter."""
    if not PROJECT_NAME_RE.match(value):
        raise ValueError(
            "must be lowercase letters, digits, or hyphens, starting with a letter"
        )
    return value


def validate_group_id(value: str) -> str:
    """Validate a Maven group id is dot-separated lowercase segments."""
    if not GROUP_ID_RE.match(value):
        raise ValueError(
            "must be dot-separated lowercase segments, e.g. com.example"
        )
    for segment in value.split("."):
        if segment in JAVA_RESERVED_WORDS:
            raise ValueError(
                f"'{segment}' is a reserved Java keyword and cannot be used in a group id"
            )
    return value


def validate_artifact_id(value: str) -> str:
    """Validate a Maven artifact id is lowercase letters/digits/hyphens starting with a letter."""
    if not ARTIFACT_ID_RE.match(value):
        raise ValueError(
            "must be lowercase letters, digits, or hyphens, starting with a letter"
        )
    stripped = value.replace("-", "")
    if stripped in JAVA_RESERVED_WORDS:
        raise ValueError(
            f"'{stripped}' is a reserved Java keyword and cannot be used in an artifact id"
        )
    return value


class ForgeConfig(BaseModel):
    """Validated parameters for one Forge generation run, plus derived template values."""

    project_name: str
    target_path: Path
    group_id: str
    artifact_id: str

    @field_validator("project_name")
    @classmethod
    def _check_project_name(cls, v: str) -> str:
        return validate_project_name(v)

    @field_validator("group_id")
    @classmethod
    def _check_group_id(cls, v: str) -> str:
        return validate_group_id(v)

    @field_validator("artifact_id")
    @classmethod
    def _check_artifact_id(cls, v: str) -> str:
        return validate_artifact_id(v)

    @property
    def target_dir(self) -> Path:
        """The full directory the project will be generated into."""
        return self.target_path / self.project_name

    @property
    def base_package(self) -> str:
        """The Java package name derived from the group id and artifact id."""
        return f"{self.group_id}.{self.artifact_id.replace('-', '')}"

    @property
    def package_path(self) -> str:
        """The base package as a filesystem path (dots replaced with slashes)."""
        return self.base_package.replace(".", "/")

    @property
    def app_class_name(self) -> str:
        """The PascalCase application class name prefix derived from the artifact id."""
        return "".join(part.capitalize() for part in self.artifact_id.split("-"))

    def template_context(self) -> dict:
        """Build the Jinja2 rendering context used by the template renderer."""
        return {
            "project_name": self.project_name,
            "group_id": self.group_id,
            "artifact_id": self.artifact_id,
            "base_package": self.base_package,
            "package_path": self.package_path,
            "app_class_name": self.app_class_name,
        }
