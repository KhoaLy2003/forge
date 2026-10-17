"""The single type table for entity fields: Java type, SQL type, imports, validation and sample values.

Every spec type (``string``, ``int``, ... ``enum``) is described exactly once in ``TYPE_TABLE``.
Nothing else in Forge (rules, resolver, templates) contains per-type logic; they all ask this module.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:  # entity_spec imports this module for VALID_TYPES, so avoid a runtime cycle
    from core.entity_spec import FieldSpec

DEFAULT_STRING_LENGTH = 255
ENUM_COLUMN_LENGTH = 20
MAX_ENUM_VALUE_LENGTH = ENUM_COLUMN_LENGTH

_VALIDATION_PKG = "jakarta.validation.constraints."


@dataclass(frozen=True)
class TypeInfo:
    """Everything a template needs to know about one field's type.

    ``java``: Java type source (``String``, ``BigDecimal``, or the nested enum class name).
    ``imports``: FQCNs of ``java.*`` types needed to declare/use the field (also cover ``sample_value``).
    ``sql``: SQL column type, e.g. ``VARCHAR(100)``, ``NUMERIC(12,2)``.
    ``validation``: Bean Validation annotation sources in order, e.g. ``("@NotBlank", "@Size(max = 100)")``.
    ``validation_imports``: FQCNs of the annotations used in ``validation``.
    ``length``: column length for string/enum columns, otherwise ``None``.
    ``sample_value`` / ``sample_value_alt``: two different valid Java expressions for generated tests.
    """

    java: str
    imports: tuple[str, ...]
    sql: str
    validation: tuple[str, ...]
    validation_imports: tuple[str, ...] = ()
    length: int | None = None
    sample_value: str = ""
    sample_value_alt: str = ""


@dataclass(frozen=True)
class _TypeRow:
    java: Callable[[str | None], str]
    imports: tuple[str, ...]
    sql: Callable[["FieldSpec"], str]
    sample: Callable[["FieldSpec", str | None], tuple[str, str]]
    length: Callable[["FieldSpec"], int | None] = lambda f: None
    required_annotation: str = "NotNull"
    extra_validation: Callable[["FieldSpec"], list[tuple[str, str]]] = lambda f: []
    check_default: Callable[["FieldSpec", object], str | None] = lambda f, v: None
    default_sql: Callable[["FieldSpec", object], str] = lambda f, v: str(v)


def _quote(value: object) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _string_length(f: "FieldSpec") -> int | None:
    if f.text:
        return None
    return f.length or DEFAULT_STRING_LENGTH


def _string_sql(f: "FieldSpec") -> str:
    return "TEXT" if f.text else f"VARCHAR({_string_length(f)})"


def _string_sample(f: "FieldSpec", _enum: str | None) -> tuple[str, str]:
    limit = _string_length(f)
    if limit is not None and limit < 6:
        return '"a"', '"b"'
    return '"sample"', '"other"'


def _string_validation(f: "FieldSpec") -> list[tuple[str, str]]:
    limit = _string_length(f)
    return [] if limit is None else [(f"@Size(max = {limit})", _VALIDATION_PKG + "Size")]


def _string_default_check(f: "FieldSpec", v: object) -> str | None:
    if not isinstance(v, str):
        return "default must be a string"
    limit = _string_length(f)
    if limit is not None and len(v) > limit:
        return f"default is longer than length {limit}"
    return None


def _is_number(v: object) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _int_check(label: str) -> Callable[["FieldSpec", object], str | None]:
    def check(_f: "FieldSpec", v: object) -> str | None:
        return None if isinstance(v, int) and not isinstance(v, bool) else f"default must be a whole number for {label}"

    return check


def _decimal_sample(f: "FieldSpec", _enum: str | None) -> tuple[str, str]:
    scale = f.scale or 0
    integer_digits = (f.precision or 0) - scale
    if scale == 0:
        a, b = "1", "2"
    elif integer_digits >= 1:
        a, b = "1." + "0" * scale, "2." + "0" * scale
    else:  # precision == scale: only fractional digits fit
        a, b = "0." + "0" * (scale - 1) + "1", "0." + "0" * (scale - 1) + "2"
    return f'new BigDecimal("{a}")', f'new BigDecimal("{b}")'


def _decimal_validation(f: "FieldSpec") -> list[tuple[str, str]]:
    return [(f"@Digits(integer = {f.precision - f.scale}, fraction = {f.scale})", _VALIDATION_PKG + "Digits")]


def _date_check(f: "FieldSpec", v: object) -> str | None:
    try:
        date.fromisoformat(str(v))
    except ValueError:
        return "default must be an ISO date such as 2026-01-31"
    return None


def _instant_check(f: "FieldSpec", v: object) -> str | None:
    try:
        datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except ValueError:
        return "default must be an ISO instant such as 2026-01-31T00:00:00Z"
    return None


def _uuid_check(f: "FieldSpec", v: object) -> str | None:
    try:
        uuid.UUID(str(v))
    except ValueError:
        return "default must be a UUID"
    return None


def _enum_check(f: "FieldSpec", v: object) -> str | None:
    if v not in (f.values or []):
        return f"default must be one of {list(f.values or [])}"
    return None


def _enum_sample(f: "FieldSpec", enum_class: str | None) -> tuple[str, str]:
    values = f.values or []
    first = values[0]
    second = values[1] if len(values) > 1 else values[0]
    return f"{enum_class}.{first}", f"{enum_class}.{second}"


TYPE_TABLE: dict[str, _TypeRow] = {
    "string": _TypeRow(
        java=lambda e: "String", imports=(), sql=_string_sql, sample=_string_sample,
        length=_string_length, required_annotation="NotBlank", extra_validation=_string_validation,
        check_default=_string_default_check, default_sql=lambda f, v: _quote(v),
    ),
    "int": _TypeRow(
        java=lambda e: "Integer", imports=(), sql=lambda f: "INTEGER",
        sample=lambda f, e: ("1", "2"), check_default=_int_check("int"),
    ),
    "long": _TypeRow(
        java=lambda e: "Long", imports=(), sql=lambda f: "BIGINT",
        sample=lambda f, e: ("1L", "2L"), check_default=_int_check("long"),
    ),
    "decimal": _TypeRow(
        java=lambda e: "BigDecimal", imports=("java.math.BigDecimal",),
        sql=lambda f: f"NUMERIC({f.precision},{f.scale})", sample=_decimal_sample,
        extra_validation=_decimal_validation,
        check_default=lambda f, v: None if _is_number(v) else "default must be a number",
    ),
    "boolean": _TypeRow(
        java=lambda e: "Boolean", imports=(), sql=lambda f: "BOOLEAN",
        sample=lambda f, e: ("true", "false"),
        check_default=lambda f, v: None if isinstance(v, bool) else "default must be true or false",
        default_sql=lambda f, v: "TRUE" if v else "FALSE",
    ),
    "date": _TypeRow(
        java=lambda e: "LocalDate", imports=("java.time.LocalDate",), sql=lambda f: "DATE",
        sample=lambda f, e: ("LocalDate.of(2026, 1, 1)", "LocalDate.of(2026, 6, 15)"),
        check_default=_date_check, default_sql=lambda f, v: _quote(v),
    ),
    "instant": _TypeRow(
        java=lambda e: "Instant", imports=("java.time.Instant",), sql=lambda f: "TIMESTAMP WITH TIME ZONE",
        sample=lambda f, e: ('Instant.parse("2026-01-01T00:00:00Z")', 'Instant.parse("2026-06-15T00:00:00Z")'),
        check_default=_instant_check, default_sql=lambda f, v: _quote(v),
    ),
    "uuid": _TypeRow(
        java=lambda e: "UUID", imports=("java.util.UUID",), sql=lambda f: "UUID",
        sample=lambda f, e: ("UUID.randomUUID()", "UUID.randomUUID()"),
        check_default=_uuid_check, default_sql=lambda f, v: _quote(v),
    ),
    "enum": _TypeRow(
        java=lambda e: e or "String", imports=(), sql=lambda f: f"VARCHAR({ENUM_COLUMN_LENGTH})",
        sample=_enum_sample, length=lambda f: ENUM_COLUMN_LENGTH, check_default=_enum_check,
        default_sql=lambda f, v: _quote(v),
    ),
}

VALID_TYPES: tuple[str, ...] = tuple(TYPE_TABLE)


def enum_class_name(entity: str, field: str) -> str:
    """Name of the nested enum class generated for an enum field, e.g. ``("Order", "status")`` -> ``OrderStatus``."""
    return entity + field[:1].upper() + field[1:]


def check_default(field: "FieldSpec") -> str | None:
    """Return an error message if ``field.default`` does not fit the field's type, else ``None``."""
    if field.default is None:
        return None
    return TYPE_TABLE[field.type].check_default(field, field.default)


def default_sql(field: "FieldSpec") -> str | None:
    """SQL literal for the field's ``default`` (``'x'``, ``42``, ``TRUE``), or ``None`` when no default is set."""
    if field.default is None:
        return None
    return TYPE_TABLE[field.type].default_sql(field, field.default)


def resolve_type(field: "FieldSpec", enum_class: str | None = None) -> TypeInfo:
    """Resolve a validated ``FieldSpec`` to its ``TypeInfo``.

    ``enum_class`` (from ``enum_class_name``) is required for ``enum`` fields because the Java type is that class.
    """
    row = TYPE_TABLE[field.type]
    if field.type == "enum" and not enum_class:
        raise ValueError("enum_class is required to resolve an enum field")
    extra = row.extra_validation(field)
    validation: list[tuple[str, str]] = []
    if field.required:
        validation.append((f"@{row.required_annotation}", _VALIDATION_PKG + row.required_annotation))
    validation.extend(extra)
    sample, sample_alt = row.sample(field, enum_class)
    return TypeInfo(
        java=row.java(enum_class),
        imports=row.imports,
        sql=row.sql(field),
        validation=tuple(src for src, _ in validation),
        validation_imports=tuple(sorted({imp for _, imp in validation})),
        length=row.length(field),
        sample_value=sample,
        sample_value_alt=sample_alt,
    )
