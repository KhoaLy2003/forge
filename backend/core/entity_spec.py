"""Pydantic models for the ``forge.yaml`` entity spec, and the loader that parses the file.

These models only describe the *shape* of the input and local, single-object rules (e.g. decimal needs
precision and scale). Cross-entity rules (names, relations, ordering) live in ``core/entity_rules.py``.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from core.type_map import MAX_ENUM_VALUE_LENGTH, VALID_TYPES, check_default

RELATION_TYPES = ("many-to-one", "one-to-many", "many-to-many", "one-to-one")
ENUM_VALUE_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class FieldSpec(_Strict):
    """One scalar field of an entity (a column)."""

    type: str
    length: int | None = Field(default=None, ge=1)
    text: bool = False
    precision: int | None = Field(default=None, ge=1)
    scale: int | None = Field(default=None, ge=0)
    required: bool = False
    unique: bool = False
    default: str | int | float | bool | None = None
    values: list[str] | None = None

    @field_validator("type")
    @classmethod
    def _check_type(cls, v: str) -> str:
        if v not in VALID_TYPES:
            raise ValueError(f"unknown type '{v}'; valid types: {', '.join(VALID_TYPES)}")
        return v

    @field_validator("default", mode="before")
    @classmethod
    def _stringify_dates(cls, v):
        # PyYAML turns an unquoted 2026-01-31 into a date object; keep it as ISO text.
        if isinstance(v, (date, datetime)):
            return v.isoformat()
        return v

    @model_validator(mode="after")
    def _check_modifiers(self) -> "FieldSpec":
        errors: list[str] = []
        if self.type != "string":
            if self.length is not None:
                errors.append("'length' is only allowed on string fields")
            if self.text:
                errors.append("'text' is only allowed on string fields")
        elif self.text and self.length is not None:
            errors.append("'text: true' and 'length' cannot be combined")
        if self.type == "decimal":
            if self.precision is None or self.scale is None:
                errors.append("decimal fields require both 'precision' and 'scale'")
            elif self.scale > self.precision:
                errors.append(f"'scale' ({self.scale}) must not exceed 'precision' ({self.precision})")
        elif self.precision is not None or self.scale is not None:
            errors.append("'precision' and 'scale' are only allowed on decimal fields")
        if self.type == "enum":
            errors.extend(self._enum_errors())
        elif self.values is not None:
            errors.append("'values' is only allowed on enum fields")
        if not errors:
            default_error = check_default(self)
            if default_error:
                errors.append(default_error)
        if errors:
            raise ValueError("; ".join(errors))
        return self

    def _enum_errors(self) -> list[str]:
        if not self.values:
            return ["enum fields require a non-empty 'values' list"]
        errors = []
        bad = [v for v in self.values if not isinstance(v, str) or not ENUM_VALUE_RE.match(v)]
        if bad:
            errors.append(f"enum values must be UPPER_SNAKE_CASE, got {bad}")
        long_values = [v for v in self.values if len(str(v)) > MAX_ENUM_VALUE_LENGTH]
        if long_values:
            errors.append(f"enum values must be at most {MAX_ENUM_VALUE_LENGTH} characters, got {long_values}")
        if len(set(self.values)) != len(self.values):
            errors.append("enum values must be unique")
        return errors


class RelationSpec(_Strict):
    """One relation from an entity to another entity (see the relation semantics in the design spec)."""

    type: str
    target: str
    required: bool = False
    inverse: str | None = None
    mapped_by: str | None = Field(default=None, alias="mappedBy")
    cascade: Literal["all"] | None = None
    orphan_removal: bool = Field(default=False, alias="orphanRemoval")

    @field_validator("type")
    @classmethod
    def _check_type(cls, v: str) -> str:
        if v not in RELATION_TYPES:
            raise ValueError(f"unknown relation type '{v}'; valid types: {', '.join(RELATION_TYPES)}")
        return v

    @model_validator(mode="after")
    def _check_modifiers(self) -> "RelationSpec":
        errors: list[str] = []
        if self.inverse is not None and self.type != "many-to-one":
            errors.append("'inverse' is only allowed on many-to-one relations")
        if self.mapped_by is not None and self.type != "one-to-many":
            errors.append("'mappedBy' is only allowed on one-to-many relations")
        if (self.cascade is not None or self.orphan_removal) and self.type != "one-to-many":
            errors.append("'cascade' and 'orphanRemoval' are only allowed on one-to-many relations")
        elif (self.cascade is not None or self.orphan_removal) and self.mapped_by is None:
            errors.append("'cascade' and 'orphanRemoval' on a one-to-many require 'mappedBy' (a bidirectional composition)")
        if self.required and self.type == "many-to-many":
            errors.append("'required' is not supported on many-to-many relations")
        if self.required and self.type == "one-to-many" and self.mapped_by is not None:
            errors.append("'required' on a one-to-many with 'mappedBy' belongs on the many-to-one side")
        if errors:
            raise ValueError("; ".join(errors))
        return self


class EntitySpec(_Strict):
    """One entity: a table, its scalar fields and its relations. ``name`` is the PascalCase class name."""

    name: str
    table: str | None = None
    fields: dict[str, FieldSpec] = Field(default_factory=dict)
    relations: dict[str, RelationSpec] = Field(default_factory=dict)


class ProjectFile(_Strict):
    """Contents of a ``forge.yaml``: optional project parameters plus the entities."""

    project_name: str | None = None
    target_path: Path | None = None
    group_id: str | None = None
    artifact_id: str | None = None
    template: str | None = None
    entities: dict[str, EntitySpec] = Field(default_factory=dict)


def _format_errors(source: str | Path, exc: ValidationError) -> str:
    lines = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err["loc"]) or "<root>"
        msg = err["msg"].removeprefix("Value error, ")
        if err["type"] == "extra_forbidden":
            msg = "unknown key (not part of the forge.yaml format)"
        lines.append(f"  - {loc}: {msg}")
    return f"Invalid {source}:\n" + "\n".join(lines)


def load_forge_yaml(path: Path) -> ProjectFile:
    """Parse a ``forge.yaml`` into a ``ProjectFile``.

    Entity ``name`` is injected from the mapping key. Raises ``ValueError`` (mentioning ``path`` and the
    key path, e.g. ``entities.Customer.fields.name.type``) for unreadable files, bad YAML or invalid content.
    """
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"Cannot read {path}: {exc}") from exc
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in {path}: {exc}") from exc
    return parse_project_data(data, path)


def parse_project_data(data, source: str | Path) -> ProjectFile:
    """Validate already-loaded forge.yaml data (injecting entity names from their keys).

    Raises ``ValueError`` naming ``source`` and the key path of every problem.
    """
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError(f"Invalid {source}: top level must be a mapping, got {type(data).__name__}")
    data = dict(data)

    entities = data.get("entities")
    if entities is None:
        data["entities"] = {}
    elif not isinstance(entities, dict):
        raise ValueError(f"Invalid {source}: 'entities' must be a mapping of entity name to definition")
    else:
        normalized = {}
        for key, body in entities.items():
            body = {} if body is None else body
            if not isinstance(body, dict):
                raise ValueError(f"Invalid {source}: entities.{key} must be a mapping")
            if body.get("name", key) != key:
                raise ValueError(f"Invalid {source}: entities.{key}.name must match its key '{key}'")
            body = dict(body)
            body["name"] = key
            for section in ("fields", "relations"):
                if body.get(section) is None:
                    body[section] = {}
            normalized[key] = body
        data["entities"] = normalized
    try:
        return ProjectFile.model_validate(data)
    except ValidationError as exc:
        raise ValueError(_format_errors(source, exc)) from exc
