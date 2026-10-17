"""Resolved (template-ready) entity model: plain dataclasses produced by ``entity_rules.resolve_model``.

Templates only read these objects; all naming, typing and relation logic has already been applied.
Naming conventions used throughout: ``name``/``var_name`` are Java identifiers, ``table``/``column`` are SQL
identifiers (snake_case, at most 63 characters), ``*_file`` values are Liquibase changelog file names.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ResolvedField:
    """A scalar field (one column) of an entity.

    name: camelCase Java property.  getter/setter: ``getFoo`` / ``setFoo``.  column: snake_case column.
    java_type: ``String``, ``Integer``, ``BigDecimal``, ... or, for enums, the nested enum class name.
    imports: ``java.*`` FQCNs needed for the type and for ``sample_value``.
    sql_type: e.g. ``VARCHAR(100)``, ``NUMERIC(12,2)``.  required: NOT NULL.  unique: unique constraint.
    unique_name: name for that constraint (``uq_<table>_<column>``).
    default_sql: SQL literal for DEFAULT, or None.
    validation: Bean Validation annotation sources, e.g. ``("@NotBlank", "@Size(max = 100)")``;
        validation_imports: the matching ``jakarta.validation.constraints.*`` FQCNs.
    type: the spec type (``string``, ``int``, ... ``enum``).  is_text: string mapped to TEXT.
    length: column length for string/enum columns, else None.  precision/scale: decimal only.
    is_enum/enum_class/enum_values: enum fields; the enum is a *nested* ``public enum`` inside the entity class.
    enum_import_suffix: for other classes, import ``<base_package>.<enum_import_suffix>``
        (e.g. ``customer.entity.Customer.CustomerStatus``).
    sample_value / sample_value_alt: two valid Java expressions for generated tests (identical only for a
        single-value enum, and ``UUID.randomUUID()`` which differs at run time).
    """

    name: str
    getter: str
    setter: str
    column: str
    type: str
    java_type: str
    imports: tuple[str, ...]
    sql_type: str
    required: bool
    unique: bool
    unique_name: str | None
    default_sql: str | None
    validation: tuple[str, ...]
    validation_imports: tuple[str, ...]
    is_text: bool
    length: int | None
    precision: int | None
    scale: int | None
    is_enum: bool
    enum_class: str | None
    enum_values: tuple[str, ...]
    enum_import_suffix: str | None
    sample_value: str
    sample_value_alt: str


@dataclass
class EnumDescriptor:
    """A nested enum to generate inside the entity class: ``class_name``, ``values``, owning ``field_name``."""

    class_name: str
    values: tuple[str, ...]
    field_name: str


@dataclass
class ForeignKey:
    """One foreign key column.

    table/column -> ref_table(id).  constraint_name: FK constraint name.  index_name: name of the
    supporting index, or None when none is needed (unique FK, or first join-table column covered by the PK).
    required: NOT NULL.  unique: unique FK (one-to-one); unique_name is its constraint name.
    on_delete: always ``RESTRICT``.
    deferred: False -> emit the FK inline in the table's CREATE TABLE (its target table is created earlier);
        True -> emit via ALTER TABLE in the final ``add-constraints`` changelog (optional relations).
    entity: owning entity name, or None for join tables.  ref_column: ``id``.
    """

    table: str
    column: str
    ref_table: str
    constraint_name: str
    index_name: str | None
    required: bool
    unique: bool
    on_delete: str
    deferred: bool
    unique_name: str | None = None
    entity: str | None = None
    ref_column: str = "id"


@dataclass
class ResolvedRelation:
    """An *owning* relation: the entity holds the FK column (to-one) or owns the join table (many-to-many).

    kind: ``many-to-one`` | ``one-to-one`` | ``many-to-many``.  owner: owning entity name.
    target/target_package/target_var/target_table: the other entity.
    java_type: ``Target`` or ``Set<Target>``.  is_collection: many-to-many.
    collection_type/collection_impl: ``Set``/``HashSet`` for many-to-many, else None.
    column: FK column (to-one), None for many-to-many.  required/unique: FK nullability / unique FK.
    fk_name/index_name/unique_name: constraint/index names for the FK column (None for many-to-many, whose FKs
        live on the JoinTable; index_name None when unique).  deferred: see ForeignKey.deferred.
    id_field: DTO property (``customerId`` or ``categoryIds``).  id_java_type: ``UUID`` or ``Set<UUID>``.
    join_table/join_column/inverse_join_column: many-to-many only (join table name, column holding this
        entity's id, column holding the target's id).
    inverse_name: attribute name of the bidirectional counterpart on the target, or None.
    synthetic: True when generated from a unidirectional one-to-many declared on the *target* entity
        (``declared_as`` = that one-to-many's name there); the FK lives on this entity but the target has no
        collection.
    on_delete: ``RESTRICT``.  getter/setter: accessor names.
    """

    name: str
    kind: str
    owner: str
    target: str
    target_package: str
    target_var: str
    target_table: str
    java_type: str
    is_collection: bool
    collection_type: str | None
    collection_impl: str | None
    column: str | None
    required: bool
    unique: bool
    fk_name: str | None
    index_name: str | None
    unique_name: str | None
    deferred: bool
    id_field: str
    id_java_type: str
    join_table: str | None
    join_column: str | None
    inverse_join_column: str | None
    inverse_name: str | None
    synthetic: bool
    declared_as: str | None
    on_delete: str
    getter: str
    setter: str


@dataclass
class ResolvedInverse:
    """A non-owning one-to-many collection on the parent (``@OneToMany(mappedBy = mapped_by)``).

    name: collection property.  singular: singular form for helper names (``item`` for ``items``);
    add_helper/remove_helper: e.g. ``addItem`` / ``removeItem`` (keep both sides in sync).
    target*: the child entity.  mapped_by: owning many-to-one on the child.
    cascade: None or ``"all"``.  orphan_removal: bool.  generated: True when created from the
    many-to-one's ``inverse:`` shortcut rather than an explicit one-to-many.
    collection_type/collection_impl: ``List``/``ArrayList``.
    """

    name: str
    getter: str
    singular: str
    add_helper: str
    remove_helper: str
    target: str
    target_package: str
    target_var: str
    mapped_by: str
    mapped_by_setter: str
    cascade: str | None
    orphan_removal: bool
    generated: bool
    collection_type: str
    collection_impl: str


@dataclass
class JoinTable:
    """Join table of a many-to-many (composite PK of both columns, FKs to both tables, ON DELETE RESTRICT).

    left_*: the owning entity; right_*: the target.  left_column/right_column hold the respective ids.
    changelog_file: the Liquibase file creating it.  relation: ``Entity.relationName`` that owns it.
    foreign_keys: its two ForeignKey objects (inline, never deferred).
    """

    name: str
    left_entity: str
    right_entity: str
    left_column: str
    right_column: str
    left_table: str
    right_table: str
    changelog_file: str
    relation: str
    foreign_keys: list[ForeignKey] = field(default_factory=list)


@dataclass
class ResolvedEntity:
    """One entity ready for templates.

    name: PascalCase.  var_name: camelCase.  package: lowercase single word (package + directory name).
    table: SQL table.  plural_path: kebab-case plural URL segment (``order-items``).
    changelog_index/changelog_file: this table's Liquibase file (``003-create-customers-table.sql``).
    fields: ResolvedField list.  owning_relations: ResolvedRelation list (declared order, then synthetic).
    inverse_relations: ResolvedInverse list.  enums: EnumDescriptor list (nested in the entity class).
    foreign_keys: ForeignKey for each to-one owning relation of this table.
    imports: sorted unique ``java.*`` FQCNs the entity class body needs (field types, collections).
    """

    name: str
    var_name: str
    package: str
    table: str
    plural_path: str
    changelog_index: int
    changelog_file: str
    fields: list[ResolvedField]
    owning_relations: list[ResolvedRelation]
    inverse_relations: list[ResolvedInverse]
    enums: list[EnumDescriptor]
    foreign_keys: list[ForeignKey]
    imports: tuple[str, ...]


@dataclass
class Model:
    """The fully resolved entity model.

    entities: topologically ordered (dependencies first).  join_tables: sorted by name.
    fk_constraints: only the *deferred* ForeignKeys (optional relations) for the final constraints changelog.
    changelog_start: first entity changelog number (3).
    changelog_files: ordered Liquibase file names for the master changelog (no 001 file when entities exist).
    """

    entities: list[ResolvedEntity]
    join_tables: list[JoinTable]
    fk_constraints: list[ForeignKey]
    changelog_start: int
    changelog_files: list[str]
