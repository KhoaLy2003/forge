"""Parameter schema for a Forge run: validation rules and the single source of truth for template context."""

import re
from pathlib import Path

from pydantic import BaseModel, PrivateAttr, field_validator, model_validator

from core.entity_spec import EntitySpec
from core.templates import discover_templates

PROJECT_NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")
GROUP_ID_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$")
ARTIFACT_ID_RE = re.compile(r"^[a-z][a-z0-9-]*$")

VALID_TEMPLATES = frozenset(discover_templates())

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


def validate_template(value: str) -> str:
    """Validate a template name is one of the registered templates."""
    if value not in VALID_TEMPLATES:
        raise ValueError(f"must be one of: {', '.join(sorted(VALID_TEMPLATES))}")
    return value


class ForgeConfig(BaseModel):
    """Validated parameters for one Forge generation run, plus derived template values."""

    project_name: str
    target_path: Path
    group_id: str
    artifact_id: str
    template: str = "base-layered"
    entities: dict[str, EntitySpec] = {}

    _model: object = PrivateAttr(default=None)

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

    @field_validator("template")
    @classmethod
    def _check_template(cls, v: str) -> str:
        return validate_template(v)

    @model_validator(mode="after")
    def _check_entities(self) -> "ForgeConfig":
        # entity_rules imports JAVA_RESERVED_WORDS from this module, so import it lazily here
        from core.entity_rules import resolve_model, topological_order, validate_names, validate_relations

        if not self.entities:
            self._model = resolve_model({})
            return self
        errors: list[str] = []
        if self.template == "minimal":
            errors.append(
                "entities require the 'base-layered' template (the 'minimal' template has no Liquibase); "
                "use --template base-layered or remove the entities"
            )
        errors += validate_names(self.entities) + validate_relations(self.entities)
        if not errors:
            try:
                topological_order(self.entities)
            except ValueError as exc:
                errors += str(exc).splitlines()
        if errors:
            lines = [f"  - {e}" for e in errors]
            raise ValueError("\n".join(["Invalid entity model:", *lines]))
        self._model = resolve_model(self.entities)
        return self

    @property
    def has_entities(self) -> bool:
        """Whether any entities were declared (they replace the Example slice)."""
        return bool(self.entities)

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

    @property
    def use_liquibase(self) -> bool:
        """Whether the selected template retains Liquibase migrations and Testcontainers."""
        return self.template != "minimal"

    @property
    def include_monitoring(self) -> bool:
        """Whether the selected template ships the metrics endpoint and monitoring stack files."""
        return self.template != "minimal"

    def template_context(self) -> dict:
        """Build the Jinja2 rendering context used by the template renderer.

        Entity keys (see ``core/entity_model.py``): ``has_entities``; ``entities`` (ResolvedEntity list in
        dependency order); ``join_tables``; ``fk_constraints`` (deferred FKs for the final constraints
        changelog); ``changelog_start`` (3); ``changelog_files`` (ordered Liquibase includes for the master); ``constraints_changelog_file`` (name of the
        final ``NNN-add-constraints.sql`` when deferred FKs exist, else None).
        """
        model = self._model
        return {
            "project_name": self.project_name,
            "group_id": self.group_id,
            "artifact_id": self.artifact_id,
            "base_package": self.base_package,
            "package_path": self.package_path,
            "app_class_name": self.app_class_name,
            "template": self.template,
            "use_liquibase": self.use_liquibase,
            "include_monitoring": self.include_monitoring,
            "has_entities": self.has_entities,
            "entities": model.entities,
            "join_tables": model.join_tables,
            "fk_constraints": model.fk_constraints,
            "changelog_start": model.changelog_start,
            "changelog_files": model.changelog_files,
            "constraints_changelog_file": (
                model.changelog_files[-1] if model.fk_constraints else None
            ),
        }
