import pytest

from core.entity_rules import resolve_model, topological_order, validate_relations
from core.entity_spec import EntitySpec, FieldSpec, RelationSpec


def ent(name, fields=None, relations=None, table=None) -> EntitySpec:
    return EntitySpec(
        name=name,
        table=table,
        fields={k: FieldSpec(**v) for k, v in (fields or {}).items()},
        relations={k: RelationSpec(**v) for k, v in (relations or {}).items()},
    )


def model_of(*entities):
    return {e.name: e for e in entities}


def m2o(target, **kw):
    return {"type": "many-to-one", "target": target, **kw}


# ---------------------------------------------------------------- the spec's Customer/Order example


def customer_order():
    return model_of(
        ent("Customer", fields={"name": {"type": "string", "length": 100, "required": True}}),
        ent(
            "Order",
            table="customer_orders",
            fields={"total": {"type": "decimal", "precision": 12, "scale": 2, "required": True}},
            relations={
                "customer": m2o("Customer", required=True, inverse="orders"),
                "items": {"type": "one-to-many", "target": "OrderItem", "mappedBy": "order",
                          "cascade": "all", "orphanRemoval": True},
            },
        ),
        ent("OrderItem", relations={"order": m2o("Order", required=True)}),
    )


def test_customer_order_example_validates():
    assert validate_relations(customer_order()) == []


def test_customer_order_topological_order():
    assert topological_order(customer_order()) == ["Customer", "Order", "OrderItem"]


def test_customer_order_resolved_entities():
    model = resolve_model(customer_order())
    assert [e.name for e in model.entities] == ["Customer", "Order", "OrderItem"]
    customer, order, item = model.entities
    assert (customer.var_name, customer.package, customer.table, customer.plural_path) == (
        "customer", "customer", "customers", "customers")
    assert (order.var_name, order.table, order.plural_path, order.package) == (
        "order", "customer_orders", "orders", "order")
    assert (item.table, item.plural_path, item.package, item.var_name) == (
        "order_items", "order-items", "orderitem", "orderItem")
    assert [e.changelog_file for e in model.entities] == [
        "003-create-customers-table.sql",
        "004-create-customer_orders-table.sql",
        "005-create-order_items-table.sql",
    ]
    assert model.changelog_start == 3


def test_customer_order_owning_relation_details():
    model = resolve_model(customer_order())
    order = model.entities[1]
    rel = order.owning_relations[0]
    assert (rel.name, rel.kind, rel.target, rel.target_package, rel.target_var) == (
        "customer", "many-to-one", "Customer", "customer", "customer")
    assert (rel.column, rel.required, rel.unique, rel.id_field) == ("customer_id", True, False, "customerId")
    assert (rel.is_collection, rel.on_delete, rel.inverse_name, rel.synthetic) == (False, "RESTRICT", "orders", False)
    assert rel.fk_name == "fk_customer_orders_customer_id"
    assert rel.index_name == "idx_customer_orders_customer_id"
    assert rel.java_type == "Customer" and rel.id_java_type == "UUID"
    assert rel.deferred is False  # required -> inline


def test_inverse_shortcut_creates_collection_on_parent():
    customer = resolve_model(customer_order()).entities[0]
    assert customer.owning_relations == []
    inv = customer.inverse_relations[0]
    assert (inv.name, inv.target, inv.target_package, inv.mapped_by) == ("orders", "Order", "order", "customer")
    assert (inv.cascade, inv.orphan_removal, inv.generated) == (None, False, True)
    assert (inv.singular, inv.add_helper, inv.remove_helper) == ("order", "addOrder", "removeOrder")


def test_explicit_mapped_by_inverse_with_cascade_and_back_reference():
    model = resolve_model(customer_order())
    order, item = model.entities[1], model.entities[2]
    inv = order.inverse_relations[0]
    assert (inv.name, inv.mapped_by, inv.cascade, inv.orphan_removal, inv.generated) == (
        "items", "order", "all", True, False)
    assert (inv.singular, inv.add_helper) == ("item", "addItem")
    assert item.owning_relations[0].inverse_name == "items"


def test_foreign_keys_and_constraints_pass():
    model = resolve_model(customer_order())
    assert model.fk_constraints == []  # all relations required -> inline
    fk = model.entities[1].foreign_keys[0]
    assert (fk.table, fk.column, fk.ref_table, fk.on_delete) == ("customer_orders", "customer_id", "customers", "RESTRICT")
    assert (fk.required, fk.unique, fk.deferred, fk.entity) == (True, False, False, "Order")
    assert fk.constraint_name == "fk_customer_orders_customer_id"
    assert model.changelog_files == [
        "002-create-notifications.sql",
        "003-create-customers-table.sql",
        "004-create-customer_orders-table.sql",
        "005-create-order_items-table.sql",
    ]


def test_fields_are_resolved_with_types():
    customer = resolve_model(customer_order()).entities[0]
    f = customer.fields[0]
    assert (f.name, f.getter, f.setter, f.column) == ("name", "getName", "setName", "name")
    assert (f.java_type, f.sql_type, f.required, f.length) == ("String", "VARCHAR(100)", True, 100)
    assert f.validation == ("@NotBlank", "@Size(max = 100)")
    assert f.sample_value == '"sample"' and f.sample_value_alt == '"other"'
    assert f.is_enum is False and f.enum_values == ()
    total = resolve_model(customer_order()).entities[1].fields[0]
    assert total.imports == ("java.math.BigDecimal",)
    assert customer.imports == ("java.util.ArrayList", "java.util.List")
    assert resolve_model(customer_order()).entities[1].imports == ("java.math.BigDecimal", "java.util.ArrayList", "java.util.List")


# ---------------------------------------------------------------- four relation kinds, all types, enum


def four_kinds():
    all_types = {
        "label": {"type": "string", "length": 50, "required": True, "unique": True},
        "notes": {"type": "string", "text": True},
        "count": {"type": "int", "default": 0},
        "big": {"type": "long"},
        "price": {"type": "decimal", "precision": 10, "scale": 2},
        "active": {"type": "boolean", "default": True},
        "born": {"type": "date"},
        "seenAt": {"type": "instant"},
        "ref": {"type": "uuid"},
        "kind": {"type": "enum", "values": ["BASIC", "PREMIUM"], "default": "BASIC"},
    }
    return model_of(
        ent("Product", fields=all_types, relations={"categories": {"type": "many-to-many", "target": "Category"}}),
        ent("Category"),
        ent("Invoice", relations={
            "product": m2o("Product", required=True),
            "approver": m2o("Employee"),
        }),
        ent("Employee", relations={"badge": {"type": "one-to-one", "target": "Badge", "required": True}}),
        ent("Badge"),
    )


def test_four_kinds_topological_order_is_deterministic_and_alphabetical_ties():
    # Badge/Category/Product have no required deps; Employee needs Badge; Invoice needs Product (approver optional)
    assert topological_order(four_kinds()) == ["Badge", "Category", "Employee", "Product", "Invoice"]


def test_one_to_one_is_unique_fk():
    model = resolve_model(four_kinds())
    employee = next(e for e in model.entities if e.name == "Employee")
    rel = employee.owning_relations[0]
    assert (rel.kind, rel.unique, rel.required, rel.column, rel.id_field) == ("one-to-one", True, True, "badge_id", "badgeId")
    assert rel.unique_name == "uq_employees_badge_id"
    assert rel.index_name is None
    assert employee.foreign_keys[0].unique is True and employee.foreign_keys[0].index_name is None


def test_optional_relation_fk_is_deferred_to_constraints_pass():
    model = resolve_model(four_kinds())
    assert [(f.table, f.column, f.deferred) for f in model.fk_constraints] == [("invoices", "approver_id", True)]
    assert model.changelog_files[-1].endswith("-add-constraints.sql")


def test_many_to_many_join_table():
    model = resolve_model(four_kinds())
    assert len(model.join_tables) == 1
    jt = model.join_tables[0]
    assert (jt.name, jt.left_entity, jt.right_entity) == ("categories_products", "Product", "Category")
    assert (jt.left_column, jt.right_column) == ("product_id", "category_id")
    assert (jt.left_table, jt.right_table) == ("products", "categories")
    assert jt.changelog_file == "008-create-categories_products-table.sql"
    assert [(f.column, f.ref_table, f.deferred) for f in jt.foreign_keys] == [
        ("product_id", "products", False), ("category_id", "categories", False)]
    assert jt.foreign_keys[0].index_name is None and jt.foreign_keys[1].index_name is not None
    product = next(e for e in model.entities if e.name == "Product")
    rel = product.owning_relations[0]
    assert (rel.kind, rel.is_collection, rel.column, rel.id_field, rel.id_java_type) == (
        "many-to-many", True, None, "categoryIds", "Set<UUID>")
    assert (rel.join_table, rel.join_column, rel.inverse_join_column) == ("categories_products", "product_id", "category_id")
    assert (rel.java_type, rel.collection_type, rel.collection_impl) == ("Set<Category>", "Set", "HashSet")
    assert "java.util.Set" in product.imports and "java.util.HashSet" in product.imports


def test_changelog_files_order():
    model = resolve_model(four_kinds())
    assert model.changelog_files == [
        "002-create-notifications.sql",
        "003-create-badges-table.sql",
        "004-create-categories-table.sql",
        "005-create-employees-table.sql",
        "006-create-products-table.sql",
        "007-create-invoices-table.sql",
        "008-create-categories_products-table.sql",
        "009-add-constraints.sql",
    ]


def test_all_types_resolved_on_product():
    product = next(e for e in resolve_model(four_kinds()).entities if e.name == "Product")
    by_name = {f.name: f for f in product.fields}
    assert by_name["label"].unique and by_name["label"].unique_name == "uq_products_label"
    assert by_name["notes"].sql_type == "TEXT" and by_name["notes"].is_text
    assert by_name["count"].default_sql == "0" and by_name["active"].default_sql == "TRUE"
    assert by_name["price"].sql_type == "NUMERIC(10,2)" and by_name["price"].column == "price"
    assert by_name["seenAt"].column == "seen_at" and by_name["seenAt"].getter == "getSeenAt"
    kind = by_name["kind"]
    assert (kind.is_enum, kind.enum_class, kind.java_type, kind.enum_values) == (
        True, "ProductKind", "ProductKind", ("BASIC", "PREMIUM"))
    assert kind.sample_value == "ProductKind.BASIC" and kind.sample_value_alt == "ProductKind.PREMIUM"
    assert kind.enum_import_suffix == "product.entity.Product.ProductKind"
    assert kind.default_sql == "'BASIC'"
    assert [(e.class_name, e.values, e.field_name) for e in product.enums] == [("ProductKind", ("BASIC", "PREMIUM"), "kind")]
    assert product.imports == (
        "java.math.BigDecimal", "java.time.Instant", "java.time.LocalDate", "java.util.HashSet",
        "java.util.Set", "java.util.UUID",
    )


# ---------------------------------------------------------------- cycles


def test_required_cycle_is_error_naming_members():
    entities = model_of(
        ent("Customer", relations={"lastOrder": m2o("Order", required=True)}),
        ent("Order", table="customer_orders", relations={"customer": m2o("Customer", required=True)}),
        ent("Product"),
    )
    with pytest.raises(ValueError) as exc:
        topological_order(entities)
    message = str(exc.value)
    assert "Customer" in message and "Order" in message and "Product" not in message
    assert "cycle" in message and "required" in message


def test_required_self_reference_is_a_cycle():
    with pytest.raises(ValueError, match="Category"):
        topological_order(model_of(ent("Category", relations={"parent": m2o("Category", required=True)})))


def test_optional_cycle_accepted_with_stable_order():
    entities = model_of(
        ent("Customer", relations={"lastOrder": m2o("Order")}),
        ent("Order", table="customer_orders", relations={"customer": m2o("Customer", required=True)}),
    )
    assert topological_order(entities) == ["Customer", "Order"]
    model = resolve_model(entities)
    assert [(f.table, f.column) for f in model.fk_constraints] == [("customers", "last_order_id")]
    assert model.changelog_files[-1] == "005-add-constraints.sql"


def test_optional_self_reference_accepted():
    model = resolve_model(model_of(ent("Category", relations={"parent": m2o("Category")})))
    assert [(f.table, f.column, f.ref_table) for f in model.fk_constraints] == [("categories", "parent_id", "categories")]


def test_topological_order_independent_of_declaration_order():
    a = model_of(ent("Zeta"), ent("Alpha", relations={"zeta": m2o("Zeta", required=True)}), ent("Beta"))
    b = model_of(ent("Beta"), ent("Alpha", relations={"zeta": m2o("Zeta", required=True)}), ent("Zeta"))
    assert topological_order(a) == topological_order(b) == ["Beta", "Zeta", "Alpha"]


# ---------------------------------------------------------------- relation validation errors


def test_unknown_target():
    errors = validate_relations(model_of(ent("Order", table="t", relations={"customer": m2o("Custmer")})))
    assert len(errors) == 1
    assert "Order" in errors[0] and "customer" in errors[0] and "Custmer" in errors[0]


def test_mapped_by_missing_relation():
    entities = model_of(
        ent("Order", table="t", relations={"items": {"type": "one-to-many", "target": "OrderItem", "mappedBy": "ordr"}}),
        ent("OrderItem", relations={"order": m2o("Order")}),
    )
    errors = validate_relations(entities)
    assert len(errors) == 1 and "mappedBy 'ordr'" in errors[0] and "order" in errors[0]


def test_mapped_by_pointing_at_non_owning_relation():
    entities = model_of(
        ent("Order", table="t", relations={"items": {"type": "one-to-many", "target": "OrderItem", "mappedBy": "more"}}),
        ent("OrderItem", relations={"more": {"type": "one-to-many", "target": "Order", "mappedBy": "items"}}),
    )
    errors = validate_relations(entities)
    assert any("owning" in e and "more" in e for e in errors)


def test_mapped_by_pointing_at_relation_to_another_entity():
    entities = model_of(
        ent("Order", table="t", relations={"items": {"type": "one-to-many", "target": "OrderItem", "mappedBy": "product"}}),
        ent("OrderItem", relations={"product": m2o("Product")}),
        ent("Product"),
    )
    errors = validate_relations(entities)
    assert any("product" in e and "Product" in e and "Order" in e for e in errors)


def test_many_to_many_declared_on_both_sides_is_error():
    entities = model_of(
        ent("Product", relations={"categories": {"type": "many-to-many", "target": "Category"}}),
        ent("Category", relations={"products": {"type": "many-to-many", "target": "Product"}}),
    )
    errors = validate_relations(entities)
    assert len(errors) == 1
    assert "Product.categories" in errors[0] and "Category.products" in errors[0] and "exactly one" in errors[0]


def test_inverse_and_mapped_by_cannot_both_describe_the_same_pair():
    entities = model_of(
        ent("Order", table="t", relations={"items": {"type": "one-to-many", "target": "OrderItem", "mappedBy": "order"}}),
        ent("OrderItem", relations={"order": m2o("Order", inverse="itemList")}),
    )
    assert any("inverse" in e and "mappedBy" in e for e in validate_relations(entities))


def test_inverse_name_colliding_with_target_member():
    entities = model_of(
        ent("Customer", fields={"orders": {"type": "string"}}),
        ent("Order", table="t", relations={"customer": m2o("Customer", inverse="orders")}),
    )
    assert any("orders" in e and "Customer" in e for e in validate_relations(entities))


def test_relation_errors_are_aggregated():
    entities = model_of(
        ent("A", relations={"x": m2o("Nope"), "y": m2o("Nada")}),
        ent("B", relations={"z": m2o("Nil")}),
    )
    assert len(validate_relations(entities)) == 3


def test_dto_name_collision_between_field_and_relation_id():
    entities = model_of(
        ent("Customer"),
        ent("Order", table="t", fields={"customerId": {"type": "string"}}, relations={"customer": m2o("Customer")}),
    )
    errors = validate_relations(entities)
    assert any("customerId" in e or "customer_id" in e for e in errors)


def test_resolve_model_raises_with_all_errors():
    entities = model_of(ent("A", relations={"x": m2o("Nope")}), ent("Order"))
    with pytest.raises(ValueError) as exc:
        resolve_model(entities)
    assert "Nope" in str(exc.value) and "reserved SQL word" in str(exc.value)


# ---------------------------------------------------------------- unidirectional one-to-many


def unidirectional():
    return model_of(
        ent("Order", table="customer_orders",
            relations={"items": {"type": "one-to-many", "target": "OrderItem", "required": True}}),
        ent("OrderItem"),
    )


def test_unidirectional_one_to_many_is_modelled_as_owning_many_to_one_on_child():
    assert validate_relations(unidirectional()) == []
    model = resolve_model(unidirectional())
    assert [e.name for e in model.entities] == ["Order", "OrderItem"]  # required edge OrderItem -> Order
    order, item = model.entities
    assert order.inverse_relations == []
    assert order.owning_relations == []
    rel = item.owning_relations[0]
    assert (rel.name, rel.kind, rel.target, rel.column, rel.required) == ("order", "many-to-one", "Order", "order_id", True)
    assert (rel.synthetic, rel.declared_as, rel.inverse_name) == (True, "items", None)
    assert item.foreign_keys[0].ref_table == "customer_orders"


def test_two_unidirectional_one_to_many_to_same_child_get_distinct_names():
    entities = model_of(
        ent("Order", table="customer_orders", relations={
            "items": {"type": "one-to-many", "target": "OrderItem"},
            "returns": {"type": "one-to-many", "target": "OrderItem"},
        }),
        ent("OrderItem"),
    )
    names = [r.name for r in resolve_model(entities).entities[1].owning_relations]
    assert names == ["order", "orderReturns"]


def test_cycle_through_unidirectional_required_one_to_many():
    entities = model_of(
        ent("A", relations={"bs": {"type": "one-to-many", "target": "B", "required": True}, "b": m2o("B", required=True)}),
        ent("B"),
    )
    # B depends on A (FK on b table, from A.bs) and A depends on B (A.b)
    with pytest.raises(ValueError, match="cycle"):
        topological_order(entities)
