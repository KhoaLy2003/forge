"""Interactive wizard that fills in missing ForgeConfig parameters, reprompting on invalid input."""

from pathlib import Path

import yaml
from pydantic import ValidationError

from core.config_schema import (
    ForgeConfig,
    validate_artifact_id,
    validate_group_id,
    validate_project_name,
)
from core.entity_rules import topological_order, validate_names, validate_relations
from core.entity_spec import RELATION_TYPES, EntitySpec, FieldSpec, RelationSpec
from core.type_map import VALID_TYPES

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


def needs_prompt(overrides: dict) -> bool:
    """Whether ``collect_params`` would have to prompt for at least one of the four project parameters.

    ``template`` is deliberately not part of this: it is never wizard-prompted (see cli.py's --template default).
    """
    return any(overrides.get(field) in (None, "") for field, _label, _validator in FIELD_PROMPTS)


def collect_params(overrides: dict, prompt_fn=input) -> ForgeConfig:
    """Fill in any missing parameters via prompts and return a validated ForgeConfig."""
    values = dict(overrides)
    for field, label, validator in FIELD_PROMPTS:
        if values.get(field) in (None, ""):
            values[field] = _prompt_field(label, validator, prompt_fn)
    values["target_path"] = Path(values["target_path"]).expanduser().resolve()
    return ForgeConfig(**values)


# ----------------------------------------------------------------------------- entity step


def _ask_yes(prompt_fn, question: str) -> bool:
    return prompt_fn(f"{question} [y/N]: ").strip().lower() in ("y", "yes")


def _model_errors(entities: dict[str, EntitySpec]) -> list[str]:
    """Every rule violation for the entity set built so far (the same rules ForgeConfig applies)."""
    errors = validate_names(entities) + validate_relations(entities)
    if not errors:
        try:
            topological_order(entities)
        except ValueError as exc:
            errors += str(exc).splitlines()
    return errors


def _show(print_fn, errors: list[str]) -> None:
    for error in errors:
        print_fn(f"Invalid value: {error}")


def _ask_int(label: str, prompt_fn, print_fn, optional: bool = False) -> int | None:
    while True:
        raw = prompt_fn(f"{label}: ").strip()
        if raw == "" and optional:
            return None
        try:
            return int(raw)
        except ValueError:
            print_fn(f"Invalid value: '{raw}' is not a whole number")


def _ask_choice(label: str, choices, prompt_fn, print_fn) -> str:
    while True:
        raw = prompt_fn(f"{label} ({', '.join(choices)}): ").strip()
        if raw in choices:
            return raw
        print_fn(f"Invalid value: '{raw}' is not one of: {', '.join(choices)}")


def _ask_entity_name(entities, prompt_fn, print_fn) -> tuple[str, str | None]:
    """Prompt for a valid, unused entity name; asks for a ``table`` override when the derived one is rejected."""
    while True:
        name = prompt_fn("Entity name (PascalCase, singular, e.g. Customer): ").strip()
        if name in entities:
            print_fn(f"Invalid value: entity '{name}' is already declared")
            continue
        errors = _model_errors({**entities, name: EntitySpec(name=name)})
        if not errors:
            return name, None
        _show(print_fn, errors)
        if not any("table" in e.lower() for e in errors):
            continue
        table = prompt_fn("Table name to use instead (blank to choose another entity name): ").strip()
        if not table:
            continue
        table_errors = _model_errors({**entities, name: EntitySpec(name=name, table=table)})
        if not table_errors:
            return name, table
        _show(print_fn, table_errors)


def _ask_field_name(entity: EntitySpec, entities, prompt_fn, print_fn) -> str:
    while True:
        name = prompt_fn("  Field name (camelCase): ").strip()
        if name in entity.fields:
            print_fn(f"Invalid value: field '{name}' is already declared")
            continue
        candidate = entity.model_copy(update={"fields": {**entity.fields, name: FieldSpec(type="int")}})
        errors = _model_errors({**entities, entity.name: candidate})
        if not errors:
            return name
        _show(print_fn, errors)


def _ask_field(prompt_fn, print_fn) -> FieldSpec:
    """Prompt for a field's type, the attributes that type needs, and ``required``; reprompt until it validates."""
    while True:
        ftype = _ask_choice("  Type", VALID_TYPES, prompt_fn, print_fn)
        extra: dict = {}
        if ftype == "string":
            length = _ask_int("  Length (blank for the default, 255)", prompt_fn, print_fn, optional=True)
            if length is not None:
                extra["length"] = length
        elif ftype == "decimal":
            extra["precision"] = _ask_int("  Precision (total digits)", prompt_fn, print_fn)
            extra["scale"] = _ask_int("  Scale (digits after the point)", prompt_fn, print_fn)
        elif ftype == "enum":
            raw = prompt_fn("  Values (comma separated, UPPER_SNAKE_CASE): ")
            extra["values"] = [v.strip() for v in raw.split(",") if v.strip()]
        extra["required"] = _ask_yes(prompt_fn, "  Required?")
        try:
            return FieldSpec(type=ftype, **extra)
        except ValidationError as exc:
            _show(print_fn, [e["msg"].removeprefix("Value error, ") for e in exc.errors()])


def _ask_relation(entity: EntitySpec, entities, prompt_fn, print_fn) -> tuple[str, RelationSpec]:
    """Prompt for one relation; the target is chosen from the entities declared before this one."""
    targets = list(entities)
    while True:
        name = prompt_fn("  Relation name (camelCase): ").strip()
        kind = _ask_choice("  Kind", RELATION_TYPES, prompt_fn, print_fn)
        target = _ask_choice("  Target", targets, prompt_fn, print_fn)
        required = False if kind == "many-to-many" else _ask_yes(prompt_fn, "  Required?")
        if name in entity.relations:
            print_fn(f"Invalid value: relation '{name}' is already declared")
            continue
        try:
            relation = RelationSpec(type=kind, target=target, required=required)
        except ValidationError as exc:
            _show(print_fn, [e["msg"].removeprefix("Value error, ") for e in exc.errors()])
            continue
        candidate = entity.model_copy(update={"relations": {**entity.relations, name: relation}})
        errors = _model_errors({**entities, entity.name: candidate})
        if not errors:
            return name, relation
        _show(print_fn, errors)


def collect_entities(prompt_fn=input, print_fn=print) -> dict[str, EntitySpec]:
    """Interactively declare entities, their fields and their relations; returns them in declaration order.

    Every answer is checked with the same rules ``ForgeConfig`` applies (``core/entity_rules.py``) and
    reprompted with the message on failure. Relation targets are limited to entities declared earlier.
    """
    entities: dict[str, EntitySpec] = {}
    question = "Add an entity?"
    while _ask_yes(prompt_fn, question):
        question = "Add another entity?"
        name, table = _ask_entity_name(entities, prompt_fn, print_fn)
        entity = EntitySpec(name=name, table=table)
        while _ask_yes(prompt_fn, "  Add a field?"):
            fname = _ask_field_name(entity, entities, prompt_fn, print_fn)
            entity = entity.model_copy(
                update={"fields": {**entity.fields, fname: _ask_field(prompt_fn, print_fn)}}
            )
        if entities:
            while _ask_yes(prompt_fn, "  Add a relation?"):
                rname, relation = _ask_relation(entity, entities, prompt_fn, print_fn)
                entity = entity.model_copy(update={"relations": {**entity.relations, rname: relation}})
        entities[name] = entity
    return entities


def save_forge_yaml(config: ForgeConfig, path: Path) -> None:
    """Write the project parameters and entities in the format ``load_forge_yaml`` reads (no ``entities`` if empty)."""
    data: dict = {
        "project_name": config.project_name,
        "target_path": str(config.target_path),
        "group_id": config.group_id,
        "artifact_id": config.artifact_id,
        "template": config.template,
    }
    if config.entities:
        data["entities"] = {
            key: entity.model_dump(mode="json", by_alias=True, exclude_defaults=True, exclude={"name"})
            for key, entity in config.entities.items()
        }
    Path(path).write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
