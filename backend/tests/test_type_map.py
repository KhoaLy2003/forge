import pytest

from core.entity_spec import FieldSpec
from core.type_map import TYPE_TABLE, VALID_TYPES, default_sql, enum_class_name, resolve_type


def field(**kwargs) -> FieldSpec:
    return FieldSpec(**kwargs)


def test_valid_types_are_exactly_the_spec_types():
    assert set(VALID_TYPES) == {"string", "int", "long", "decimal", "boolean", "date", "instant", "uuid", "enum"}
    assert set(TYPE_TABLE) == set(VALID_TYPES)


@pytest.mark.parametrize(
    "kwargs, java, sql, imports",
    [
        ({"type": "string"}, "String", "VARCHAR(255)", ()),
        ({"type": "string", "length": 100}, "String", "VARCHAR(100)", ()),
        ({"type": "string", "text": True}, "String", "TEXT", ()),
        ({"type": "int"}, "Integer", "INTEGER", ()),
        ({"type": "long"}, "Long", "BIGINT", ()),
        ({"type": "decimal", "precision": 12, "scale": 2}, "BigDecimal", "NUMERIC(12,2)", ("java.math.BigDecimal",)),
        ({"type": "boolean"}, "Boolean", "BOOLEAN", ()),
        ({"type": "date"}, "LocalDate", "DATE", ("java.time.LocalDate",)),
        ({"type": "instant"}, "Instant", "TIMESTAMP WITH TIME ZONE", ("java.time.Instant",)),
        ({"type": "uuid"}, "UUID", "UUID", ("java.util.UUID",)),
        ({"type": "enum", "values": ["A", "B"]}, "OrderStatus", "VARCHAR(20)", ()),
    ],
)
def test_java_sql_and_imports(kwargs, java, sql, imports):
    info = resolve_type(field(**kwargs), enum_class="OrderStatus")
    assert (info.java, info.sql, info.imports) == (java, sql, imports)


@pytest.mark.parametrize(
    "kwargs, optional, required",
    [
        ({"type": "string", "length": 100}, ("@Size(max = 100)",), ("@NotBlank", "@Size(max = 100)")),
        ({"type": "string", "text": True}, (), ("@NotBlank",)),
        ({"type": "string"}, ("@Size(max = 255)",), ("@NotBlank", "@Size(max = 255)")),
        ({"type": "int"}, (), ("@NotNull",)),
        ({"type": "long"}, (), ("@NotNull",)),
        ({"type": "decimal", "precision": 12, "scale": 2}, ("@Digits(integer = 10, fraction = 2)",),
         ("@NotNull", "@Digits(integer = 10, fraction = 2)")),
        ({"type": "boolean"}, (), ("@NotNull",)),
        ({"type": "date"}, (), ("@NotNull",)),
        ({"type": "instant"}, (), ("@NotNull",)),
        ({"type": "uuid"}, (), ("@NotNull",)),
        ({"type": "enum", "values": ["A"]}, (), ("@NotNull",)),
    ],
)
def test_validation_annotations_by_required(kwargs, optional, required):
    assert resolve_type(field(**kwargs), "E").validation == optional
    assert resolve_type(field(required=True, **kwargs), "E").validation == required


def test_validation_imports_match_annotations():
    info = resolve_type(field(type="decimal", precision=5, scale=2, required=True))
    assert info.validation_imports == (
        "jakarta.validation.constraints.Digits",
        "jakarta.validation.constraints.NotNull",
    )
    info = resolve_type(field(type="string", length=10, required=True))
    assert info.validation_imports == (
        "jakarta.validation.constraints.NotBlank",
        "jakarta.validation.constraints.Size",
    )


@pytest.mark.parametrize(
    "kwargs, sample, alt",
    [
        ({"type": "string"}, '"sample"', '"other"'),
        ({"type": "string", "length": 3}, '"a"', '"b"'),
        ({"type": "int"}, "1", "2"),
        ({"type": "long"}, "1L", "2L"),
        ({"type": "decimal", "precision": 12, "scale": 2}, 'new BigDecimal("1.00")', 'new BigDecimal("2.00")'),
        ({"type": "decimal", "precision": 3, "scale": 3}, 'new BigDecimal("0.001")', 'new BigDecimal("0.002")'),
        ({"type": "decimal", "precision": 5, "scale": 0}, 'new BigDecimal("1")', 'new BigDecimal("2")'),
        ({"type": "boolean"}, "true", "false"),
        ({"type": "date"}, "LocalDate.of(2026, 1, 1)", "LocalDate.of(2026, 6, 15)"),
        ({"type": "instant"}, 'Instant.parse("2026-01-01T00:00:00Z")', 'Instant.parse("2026-06-15T00:00:00Z")'),
        ({"type": "uuid"}, "UUID.randomUUID()", "UUID.randomUUID()"),
        ({"type": "enum", "values": ["ACTIVE", "SUSPENDED"]}, "OrderStatus.ACTIVE", "OrderStatus.SUSPENDED"),
    ],
)
def test_sample_values(kwargs, sample, alt):
    info = resolve_type(field(**kwargs), enum_class="OrderStatus")
    assert (info.sample_value, info.sample_value_alt) == (sample, alt)


def test_non_uuid_samples_differ():
    for kwargs in ({"type": "string"}, {"type": "int"}, {"type": "boolean"}, {"type": "date"}):
        info = resolve_type(field(**kwargs))
        assert info.sample_value != info.sample_value_alt


def test_length_is_reported_for_string_and_enum_only():
    assert resolve_type(field(type="string")).length == 255
    assert resolve_type(field(type="string", length=40)).length == 40
    assert resolve_type(field(type="string", text=True)).length is None
    assert resolve_type(field(type="enum", values=["A"]), "E").length == 20
    assert resolve_type(field(type="int")).length is None


def test_enum_requires_class_name():
    with pytest.raises(ValueError):
        resolve_type(field(type="enum", values=["A"]))


def test_enum_class_name():
    assert enum_class_name("Order", "status") == "OrderStatus"
    assert enum_class_name("OrderItem", "kind") == "OrderItemKind"


@pytest.mark.parametrize(
    "kwargs, expected",
    [
        ({"type": "string", "default": "it's"}, "'it''s'"),
        ({"type": "int", "default": 5}, "5"),
        ({"type": "boolean", "default": True}, "TRUE"),
        ({"type": "boolean", "default": False}, "FALSE"),
        ({"type": "decimal", "precision": 5, "scale": 2, "default": 1.5}, "1.5"),
        ({"type": "enum", "values": ["A", "B"], "default": "B"}, "'B'"),
        ({"type": "date", "default": "2026-01-01"}, "'2026-01-01'"),
        ({"type": "int"}, None),
    ],
)
def test_default_sql(kwargs, expected):
    assert default_sql(field(**kwargs)) == expected
