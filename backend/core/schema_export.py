"""JSON Schema for ``forge.yaml``, derived from the pydantic input models and patched for the file format."""

from core.entity_spec import RELATION_TYPES, ProjectFile
from core.type_map import VALID_TYPES


def _set_enum(prop: dict, values: list[str]) -> None:
    """Put ``enum`` on the property root, or on its string branch when pydantic emitted an ``anyOf``."""
    if "anyOf" in prop:
        for branch in prop["anyOf"]:
            if branch.get("type") == "string":
                branch["enum"] = values
                return
    prop["enum"] = values


def forge_yaml_schema() -> dict:
    """Return the JSON Schema (draft-07) describing a ``forge.yaml`` file."""
    schema = ProjectFile.model_json_schema(by_alias=True)
    defs = schema["$defs"]

    entity = defs["EntitySpec"]
    entity["properties"].pop("name", None)  # injected from the mapping key
    if "name" in entity.get("required", []):
        entity["required"].remove("name")
        if not entity["required"]:
            del entity["required"]

    _set_enum(defs["FieldSpec"]["properties"]["type"], list(VALID_TYPES))
    _set_enum(defs["RelationSpec"]["properties"]["type"], list(RELATION_TYPES))

    # The loader accepts an empty entity body (``Tag:``), which YAML parses as null.
    schema["properties"]["entities"]["additionalProperties"] = {
        "anyOf": [{"$ref": "#/$defs/EntitySpec"}, {"type": "null"}]
    }
    schema["$schema"] = "http://json-schema.org/draft-07/schema#"
    schema["title"] = "forge.yaml"
    return schema
