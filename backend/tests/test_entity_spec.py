from pathlib import Path

import pytest

from core.entity_spec import EntitySpec, FieldSpec, ProjectFile, RelationSpec, load_forge_yaml

SAMPLE = """
entities:
  Customer:
    fields:
      name:   { type: string, length: 100, required: true }
      email:  { type: string, unique: true, required: true }
      status: { type: enum, values: [ACTIVE, SUSPENDED] }
  Order:
    table: customer_orders
    fields:
      total:    { type: decimal, precision: 12, scale: 2, required: true }
      placedAt: { type: instant }
    relations:
      customer: { type: many-to-one, target: Customer, required: true, inverse: orders }
      items:    { type: one-to-many, target: OrderItem, mappedBy: order }
  Product:
    relations:
      categories: { type: many-to-many, target: Category }
"""


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "forge.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_spec_sample_parses(tmp_path):
    project = load_forge_yaml(write(tmp_path, SAMPLE))
    assert isinstance(project, ProjectFile)
    assert list(project.entities) == ["Customer", "Order", "Product"]
    order = project.entities["Order"]
    assert order.name == "Order"
    assert order.table == "customer_orders"
    assert order.fields["total"].precision == 12
    assert order.relations["items"].mapped_by == "order"
    assert order.relations["customer"].inverse == "orders"
    assert project.entities["Product"].fields == {}


def test_project_parameters_are_loaded(tmp_path):
    project = load_forge_yaml(
        write(tmp_path, "project_name: demo\ngroup_id: com.example\nartifact_id: demo\ntemplate: base-layered\n")
    )
    assert project.project_name == "demo"
    assert project.group_id == "com.example"
    assert project.template == "base-layered"
    assert project.entities == {}


def test_unknown_field_type_names_entity_field_and_valid_types(tmp_path):
    text = "entities:\n  Customer:\n    fields:\n      name: { type: strng }\n"
    with pytest.raises(ValueError) as exc:
        load_forge_yaml(write(tmp_path, text))
    message = str(exc.value)
    assert "Customer" in message and "name" in message
    assert "strng" in message
    for valid in ("string", "int", "long", "decimal", "boolean", "date", "instant", "uuid", "enum"):
        assert valid in message
    assert "forge.yaml" in message


def test_unknown_key_rejected(tmp_path):
    text = "entities:\n  Customer:\n    fields:\n      name: { type: string, lenght: 10 }\n"
    with pytest.raises(ValueError, match="lenght"):
        load_forge_yaml(write(tmp_path, text))


def test_unknown_top_level_key_rejected(tmp_path):
    with pytest.raises(ValueError, match="bogus"):
        load_forge_yaml(write(tmp_path, "bogus: 1\n"))


def test_decimal_without_precision_rejected(tmp_path):
    text = "entities:\n  A:\n    fields:\n      price: { type: decimal }\n"
    with pytest.raises(ValueError, match="precision"):
        load_forge_yaml(write(tmp_path, text))


def test_enum_without_values_rejected(tmp_path):
    text = "entities:\n  A:\n    fields:\n      status: { type: enum }\n"
    with pytest.raises(ValueError, match="values"):
        load_forge_yaml(write(tmp_path, text))


def test_empty_file_gives_no_entities(tmp_path):
    assert load_forge_yaml(write(tmp_path, "")).entities == {}


def test_invalid_yaml_mentions_path(tmp_path):
    path = write(tmp_path, "entities: [unclosed\n")
    with pytest.raises(ValueError) as exc:
        load_forge_yaml(path)
    assert str(path) in str(exc.value)


def test_missing_file_mentions_path(tmp_path):
    with pytest.raises(ValueError, match="missing.yaml"):
        load_forge_yaml(tmp_path / "missing.yaml")


def test_entity_with_empty_body_is_allowed(tmp_path):
    project = load_forge_yaml(write(tmp_path, "entities:\n  Tag:\n"))
    assert project.entities["Tag"].fields == {}


def test_unquoted_yaml_date_default_becomes_iso_string(tmp_path):
    text = "entities:\n  A:\n    fields:\n      since: { type: date, default: 2026-01-31 }\n"
    assert load_forge_yaml(write(tmp_path, text)).entities["A"].fields["since"].default == "2026-01-31"


@pytest.mark.parametrize(
    "kwargs, fragment",
    [
        ({"type": "int", "length": 5}, "length"),
        ({"type": "string", "length": 5, "text": True}, "text"),
        ({"type": "int", "precision": 3}, "precision"),
        ({"type": "decimal", "precision": 2, "scale": 3}, "scale"),
        ({"type": "string", "values": ["A"]}, "values"),
        ({"type": "enum", "values": ["active"]}, "UPPER_SNAKE"),
        ({"type": "enum", "values": ["A", "A"]}, "unique"),
        ({"type": "enum", "values": ["A"], "default": "B"}, "default"),
        ({"type": "int", "default": "x"}, "default"),
        ({"type": "boolean", "default": 1}, "default"),
        ({"type": "uuid", "default": "nope"}, "UUID"),
    ],
)
def test_field_modifier_errors(kwargs, fragment):
    with pytest.raises(ValueError, match=fragment):
        FieldSpec(**kwargs)


def test_valid_defaults_accepted():
    assert FieldSpec(type="boolean", default=True).default is True
    assert FieldSpec(type="enum", values=["A", "B"], default="B").default == "B"
    assert FieldSpec(type="decimal", precision=5, scale=2, default=1.5).default == 1.5


@pytest.mark.parametrize(
    "kwargs, fragment",
    [
        ({"type": "one-to-one", "target": "A", "inverse": "x"}, "inverse"),
        ({"type": "many-to-one", "target": "A", "mappedBy": "x"}, "mappedBy"),
        ({"type": "many-to-one", "target": "A", "cascade": "all"}, "cascade"),
        ({"type": "one-to-many", "target": "A", "cascade": "all"}, "mappedBy"),
        ({"type": "many-to-many", "target": "A", "required": True}, "required"),
        ({"type": "sideways", "target": "A"}, "valid types"),
    ],
)
def test_relation_modifier_errors(kwargs, fragment):
    with pytest.raises(ValueError, match=fragment):
        RelationSpec(**kwargs)


def test_relation_aliases_and_field_names_both_work():
    by_alias = RelationSpec(type="one-to-many", target="A", mappedBy="b", orphanRemoval=True, cascade="all")
    by_name = RelationSpec(type="one-to-many", target="A", mapped_by="b", orphan_removal=True, cascade="all")
    assert by_alias == by_name


def test_entity_spec_extra_key_forbidden():
    with pytest.raises(ValueError):
        EntitySpec(name="A", colour="red")
