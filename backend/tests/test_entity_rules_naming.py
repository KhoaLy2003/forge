import pytest

from core.entity_rules import (
    SQL_RESERVED_WORDS,
    derive_table_name,
    kebab_case,
    pluralize,
    singularize,
    snake_case,
    validate_names,
)
from core.entity_spec import EntitySpec, FieldSpec


def entity(name="Customer", table=None, fields=None, relations=None) -> EntitySpec:
    return EntitySpec(
        name=name,
        table=table,
        fields={k: FieldSpec(**v) for k, v in (fields or {}).items()},
        relations=relations or {},
    )


def names_errors(*entities: EntitySpec) -> list[str]:
    return validate_names({e.name: e for e in entities})


def test_reserved_set_contains_required_words():
    required = {
        "order", "user", "group", "table", "select", "index", "key", "column", "check", "default",
        "desc", "asc", "grant", "limit", "offset", "primary", "references", "role", "session", "schema",
    }
    assert required <= SQL_RESERVED_WORDS


@pytest.mark.parametrize(
    "word, plural",
    [
        ("category", "categories"),
        ("address", "addresses"),
        ("box", "boxes"),
        ("church", "churches"),
        ("dish", "dishes"),
        ("day", "days"),
        ("customer", "customers"),
        ("person", "people"),
        ("order_item", "order_items"),
    ],
)
def test_pluralize(word, plural):
    assert pluralize(word) == plural
    assert singularize(plural) == word


@pytest.mark.parametrize(
    "name, snake",
    [("Customer", "customer"), ("OrderItem", "order_item"), ("placedAt", "placed_at"), ("HTTPLog", "http_log")],
)
def test_snake_case(name, snake):
    assert snake_case(name) == snake


def test_kebab_case():
    assert kebab_case("order_items") == "order-items"


def test_derive_table_name_default_and_override():
    assert derive_table_name(entity("Category")) == "categories"
    assert derive_table_name(entity("Address")) == "addresses"
    assert derive_table_name(entity("OrderItem")) == "order_items"
    assert derive_table_name(entity("Order", table="customer_orders")) == "customer_orders"


def test_order_entity_rejected_with_table_suggestion():
    errors = names_errors(entity("Order"))
    assert len(errors) == 1
    assert "Order" in errors[0] and "reserved SQL word" in errors[0]
    assert "table: customer_orders" in errors[0]


def test_user_entity_rejected_with_suggestion():
    errors = names_errors(entity("User"))
    assert "reserved SQL word" in errors[0] and "table:" in errors[0]


def test_order_with_explicit_table_is_ok():
    assert names_errors(entity("Order", table="customer_orders")) == []


def test_explicit_reserved_table_rejected():
    errors = names_errors(entity("Order", table="order"))
    assert any("reserved SQL word" in e and "'order'" in e for e in errors)


def test_explicit_table_must_be_snake_case():
    assert any("table" in e for e in names_errors(entity("Order", table="My Orders")))


def test_lowercase_entity_name_rejected():
    errors = names_errors(entity("customer"))
    assert any("PascalCase" in e for e in errors)


def test_plural_entity_name_rejected():
    errors = names_errors(entity("Customers"))
    assert any("singular" in e for e in errors)


def test_singular_looking_s_endings_allowed():
    assert names_errors(entity("Address"), entity("Status"), entity("Analysis")) == []


def test_java_reserved_entity_and_field_rejected():
    errors = names_errors(entity("Record"))
    assert any("Java" in e for e in errors)
    errors = names_errors(entity("Customer", fields={"class": {"type": "string"}}))
    assert any("class" in e and "reserved" in e for e in errors)


def test_clashing_generated_class_names_rejected():
    assert any("Page" in e for e in names_errors(entity("Page")))
    assert any("BaseEntity" in e for e in names_errors(entity("BaseEntity")))


def test_package_clash_with_generated_modules_rejected():
    assert any("package" in e for e in names_errors(entity("Notification", table="alerts")))
    assert any("package" in e for e in names_errors(entity("Common")))


@pytest.mark.parametrize("name", ["id", "version", "createdAt", "updatedAt", "deletedAt"])
def test_base_entity_member_collision(name):
    errors = names_errors(entity("Customer", fields={name: {"type": "string"}}))
    assert any(name in e and "BaseEntity" in e for e in errors)


def test_field_name_must_be_camel_case():
    errors = names_errors(entity("Customer", fields={"First_Name": {"type": "string"}}))
    assert any("camelCase" in e and "First_Name" in e for e in errors)


def test_duplicate_name_across_fields_and_relations():
    from core.entity_spec import RelationSpec

    e = entity(
        "Customer",
        fields={"owner": {"type": "string"}},
        relations={"owner": RelationSpec(type="many-to-one", target="Customer")},
    )
    assert any("owner" in x and "both a field and a relation" in x for x in names_errors(e))


def test_duplicate_entity_tables_rejected():
    errors = names_errors(entity("Customer", table="things"), entity("Product", table="things"))
    assert any("things" in e and "Customer" in e and "Product" in e for e in errors)


def test_table_collision_with_generated_notification_tables():
    errors = names_errors(entity("Delivery"))
    assert any("deliveries" in e for e in errors)


def test_reserved_column_name_rejected_but_soft_words_allowed():
    errors = names_errors(entity("Customer", fields={"desc": {"type": "string"}}))
    assert any("column" in e and "desc" in e for e in errors)
    assert names_errors(entity("Customer", fields={"role": {"type": "string"}, "key": {"type": "string"}})) == []


def test_enum_class_clashing_with_entity_name_rejected():
    errors = names_errors(
        entity("Order", table="orders_t", fields={"status": {"type": "enum", "values": ["A"]}}),
        entity("OrderStatus"),
    )
    assert any("OrderStatus" in e and "enum" in e for e in errors)


def test_errors_are_aggregated():
    errors = names_errors(
        entity("Order"),
        entity("customer"),
        entity("Product", fields={"id": {"type": "string"}, "class": {"type": "string"}}),
    )
    assert len(errors) >= 4


def test_dict_key_must_match_name():
    errors = validate_names({"Customer": entity("Client")})
    assert any("Customer" in e and "Client" in e for e in errors)


def test_valid_set_has_no_errors():
    assert names_errors(
        entity("Customer", fields={"name": {"type": "string"}}),
        entity("OrderItem"),
        entity("Order", table="customer_orders"),
    ) == []
