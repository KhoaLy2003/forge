"""Entity rules: naming and SQL-reserved-word validation, relation resolution and dependency ordering.

Public API (all take ``dict[str, EntitySpec]`` keyed by entity name, in declaration order):

- ``validate_names(entities) -> list[str]``       naming rules (entity/field/relation/table names)
- ``validate_relations(entities) -> list[str]``   relation targets, ``mappedBy``/``inverse``, many-to-many, collisions
- ``topological_order(entities) -> list[str]``    dependency order over *required* to-one edges; raises on a cycle
- ``resolve_model(entities) -> Model``            validates everything, then builds the template-ready ``Model``

Validators return *all* error messages (never stop at the first). The resolved dataclasses live in
``core/entity_model.py`` and are re-exported here.

Relation semantics (see the design spec):

- many-to-one / one-to-one own an FK column (one-to-one adds a unique constraint).
- one-to-many with ``mappedBy`` is the inverse collection of a many-to-one; ``inverse: name`` on a many-to-one
  generates the same collection without declaring it.
- one-to-many without ``mappedBy`` is unidirectional: it is modelled as a *synthetic* owning many-to-one on the
  child (FK column on the child's table); the parent gets no collection.
- many-to-many is declared on exactly one entity, which owns the join table.
- A required FK is created inline in its table's CREATE TABLE (so the target must be created first -> topological
  order over required edges); an optional FK is added by ALTER TABLE in the final constraints changelog.
"""

from __future__ import annotations

import hashlib
import heapq
import re
from dataclasses import dataclass, field

from core.config_schema import JAVA_RESERVED_WORDS
from core.entity_model import (
    EnumDescriptor,
    ForeignKey,
    JoinTable,
    Model,
    ResolvedEntity,
    ResolvedField,
    ResolvedInverse,
    ResolvedRelation,
)
from core.entity_spec import EntitySpec
from core.type_map import default_sql, enum_class_name, resolve_type

__all__ = [
    "SQL_RESERVED_WORDS", "snake_case", "kebab_case", "pluralize", "singularize", "derive_table_name",
    "validate_names", "validate_relations", "topological_order", "resolve_model",
    "Model", "ResolvedEntity", "ResolvedField", "ResolvedRelation", "ResolvedInverse", "JoinTable",
    "ForeignKey", "EnumDescriptor",
]

CHANGELOG_START = 3
MAX_IDENTIFIER = 63
BASE_ENTITY_MEMBERS = frozenset({"id", "version", "createdAt", "updatedAt", "deletedAt"})
RESERVED_PACKAGES = frozenset({"common", "notification", "example"})
RESERVED_TABLES = frozenset({
    "notification_templates", "notifications", "deliveries", "notification_preferences",
    "databasechangelog", "databasechangeloglock",
})
RESERVED_CLASS_NAMES = frozenset({
    "BaseEntity", "Object", "String", "Integer", "Long", "Boolean", "Number", "Class", "Enum", "Record",
    "Void", "Math", "System", "Thread", "Exception", "Error", "Override", "List", "Set", "Map", "Optional",
    "UUID", "BigDecimal", "Instant", "LocalDate", "Date", "Page", "Pageable", "Application",
})

# Reserved in PostgreSQL ("reserved" and "reserved (can be function or type)"): unusable as a column name.
PG_RESERVED_WORDS = frozenset(
    """all analyse analyze and any array as asc asymmetric authorization binary both case cast check collate
    collation column concurrently constraint create cross current_catalog current_date current_role
    current_schema current_time current_timestamp current_user default deferrable desc distinct do else end
    except false fetch for foreign freeze from full grant group having ilike in initially inner intersect into
    is isnull join lateral leading left like limit localtime localtimestamp natural not notnull null offset on
    only or order outer overlaps placing primary references returning right select session_user similar some
    symmetric system_user table tablesample then to trailing true union unique user using variadic verbose when
    where window with""".split()
)
# Not reserved by PostgreSQL but troublesome as table names (JPQL/SQL keywords, common clashes); the design spec
# rejects these as table names. They are *not* rejected as column names.
_SOFT_RESERVED_WORDS = frozenset(
    {"index", "key", "role", "session", "schema", "update", "delete", "insert", "values", "set", "begin",
     "commit", "rollback", "transaction"}
)
SQL_RESERVED_WORDS = PG_RESERVED_WORDS | _SOFT_RESERVED_WORDS

_TABLE_SUGGESTIONS = {
    "order": "customer_orders", "user": "app_users", "group": "user_groups", "role": "user_roles",
    "session": "user_sessions", "key": "api_keys", "index": "search_indexes",
}

ENTITY_NAME_RE = re.compile(r"^[A-Z][A-Za-z0-9]*$")
MEMBER_NAME_RE = re.compile(r"^[a-z][A-Za-z0-9]*$")
TABLE_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_NOT_PLURAL_SUFFIXES = ("ss", "us", "is", "as", "ics")

_IRREGULAR_PLURALS = {
    "person": "people", "child": "children", "man": "men", "woman": "women", "mouse": "mice",
    "foot": "feet", "tooth": "teeth", "goose": "geese",
}
_IRREGULAR_SINGULARS = {v: k for k, v in _IRREGULAR_PLURALS.items()}


# ----------------------------------------------------------------------------- string helpers


def upper_first(value: str) -> str:
    """Upper-case the first character: ``status`` -> ``Status``."""
    return value[:1].upper() + value[1:]


def lower_first(value: str) -> str:
    """Lower-case the first character: ``OrderItem`` -> ``orderItem``."""
    return value[:1].lower() + value[1:]


def snake_case(name: str) -> str:
    """``OrderItem`` -> ``order_item``, ``placedAt`` -> ``placed_at``, ``HTTPLog`` -> ``http_log``."""
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "_", name).lower()


def kebab_case(name: str) -> str:
    """``order_items`` -> ``order-items``."""
    return name.replace("_", "-")


def pluralize(word: str) -> str:
    """Pluralize the last ``_``-separated word: ``category`` -> ``categories``, ``address`` -> ``addresses``."""
    head, sep, last = word.rpartition("_")
    if last in _IRREGULAR_PLURALS:
        plural = _IRREGULAR_PLURALS[last]
    elif re.search(r"[^aeiou]y$", last):
        plural = last[:-1] + "ies"
    elif re.search(r"(s|x|z|ch|sh)$", last):
        plural = last + "es"
    else:
        plural = last + "s"
    return head + sep + plural


def singularize(word: str) -> str:
    """Best-effort inverse of ``pluralize`` (``categories`` -> ``category``); unchanged if not recognisably plural."""
    head, sep, last = word.rpartition("_")
    if last in _IRREGULAR_SINGULARS:
        singular = _IRREGULAR_SINGULARS[last]
    elif last.endswith("ies") and len(last) > 3:
        singular = last[:-3] + "y"
    elif re.search(r"(sses|xes|zes|ches|shes)$", last):
        singular = last[:-2]
    elif last.endswith("s") and not last.endswith(_NOT_PLURAL_SUFFIXES):
        singular = last[:-1]
    else:
        singular = last
    return head + sep + singular


def _ident(*parts: str) -> str:
    """Join SQL identifier parts with ``_``, shortening with a stable hash if over PostgreSQL's 63-char limit."""
    name = "_".join(parts)
    if len(name) <= MAX_IDENTIFIER:
        return name
    digest = hashlib.sha1(name.encode()).hexdigest()[:8]
    return name[: MAX_IDENTIFIER - 9] + "_" + digest


def derive_table_name(entity: EntitySpec) -> str:
    """The entity's table: its explicit ``table:`` or else the snake_case plural of its name."""
    return entity.table or pluralize(snake_case(entity.name))


def _looks_plural(name: str) -> bool:
    return len(name) > 3 and name.endswith("s") and not name.endswith(_NOT_PLURAL_SUFFIXES)


def _join(errors: list[str]) -> str:
    return "Invalid entity model:\n" + "\n".join(f"  - {e}" for e in errors)


# ----------------------------------------------------------------------------- naming rules


def _entity_name_errors(key: str, e: EntitySpec, entities: dict[str, EntitySpec]) -> list[str]:
    errors: list[str] = []
    name = e.name
    where = f"Entity '{name}'"
    if key != name:
        errors.append(f"Entity key '{key}' does not match its name '{name}'")
    if not ENTITY_NAME_RE.match(name):
        errors.append(f"{where}: name must be PascalCase letters/digits starting with a capital, e.g. 'OrderItem'")
    elif name.lower() in JAVA_RESERVED_WORDS:
        errors.append(f"{where}: '{name}' is a reserved Java word and cannot be an entity name")
    elif name in RESERVED_CLASS_NAMES:
        errors.append(f"{where}: '{name}' clashes with a class used by the generated code; choose another name")
    elif _looks_plural(name):
        errors.append(f"{where}: entity names must be singular (e.g. 'Customer', not 'Customers')")
    if name.lower() in RESERVED_PACKAGES:
        errors.append(
            f"{where}: its package '{name.lower()}' is used by a generated module; choose another name"
        )
    return errors


def _table_errors(e: EntitySpec) -> list[str]:
    errors: list[str] = []
    where = f"Entity '{e.name}'"
    table = derive_table_name(e)
    if e.table is not None:
        if not TABLE_NAME_RE.match(e.table) or len(e.table) > MAX_IDENTIFIER:
            errors.append(f"{where}: table '{e.table}' must be lowercase snake_case (max {MAX_IDENTIFIER} characters)")
        elif e.table in SQL_RESERVED_WORDS:
            errors.append(f"{where}: table '{e.table}' is a reserved SQL word; choose another `table:` name")
    else:
        singular = snake_case(e.name)
        suggestion = _TABLE_SUGGESTIONS.get(singular, f"app_{pluralize(singular)}")
        if singular in SQL_RESERVED_WORDS:
            errors.append(
                f"{where}: '{singular}' is a reserved SQL word (it also breaks JPQL queries on the entity); "
                f"set `table: {suggestion}` (or another non-reserved name) on the entity"
            )
        elif table in SQL_RESERVED_WORDS:
            errors.append(f"{where}: derived table '{table}' is a reserved SQL word; set `table: {suggestion}`")
    if table in RESERVED_TABLES:
        errors.append(f"{where}: table '{table}' is used by a generated module; set a different `table:`")
    return errors


def _member_errors(e: EntitySpec, entities: dict[str, EntitySpec]) -> list[str]:
    errors: list[str] = []
    where = f"Entity '{e.name}'"
    both = [n for n in e.fields if n in e.relations]
    for n in both:
        errors.append(f"{where}: '{n}' is declared as both a field and a relation")
    for kind, names in (("field", e.fields), ("relation", e.relations)):
        for n in names:
            if not MEMBER_NAME_RE.match(n):
                errors.append(f"{where}: {kind} '{n}' must be camelCase, e.g. 'firstName'")
            elif n in JAVA_RESERVED_WORDS:
                errors.append(f"{where}: {kind} '{n}' is a reserved Java word")
            elif n in BASE_ENTITY_MEMBERS:
                errors.append(f"{where}: {kind} '{n}' collides with the inherited BaseEntity member '{n}'")
            elif kind == "field" and snake_case(n) in PG_RESERVED_WORDS:
                errors.append(f"{where}: field '{n}' maps to column '{snake_case(n)}', a reserved SQL word; rename the field")
    for fname, f in e.fields.items():
        if f.type == "enum":
            cls = enum_class_name(e.name, fname)
            if cls in entities:
                errors.append(
                    f"{where}: the generated enum '{cls}' for field '{fname}' clashes with entity '{cls}'; rename one"
                )
    return errors


def validate_names(entities: dict[str, EntitySpec]) -> list[str]:
    """Check entity, table, field and relation names. Returns every violation found (empty list = valid)."""
    errors: list[str] = []
    tables: dict[str, str] = {}
    packages: dict[str, str] = {}
    for key, e in entities.items():
        errors += _entity_name_errors(key, e, entities)
        errors += _table_errors(e)
        errors += _member_errors(e, entities)
        table = derive_table_name(e)
        if table in tables:
            errors.append(f"Entities '{tables[table]}' and '{e.name}' both use table '{table}'; set a distinct `table:`")
        else:
            tables[table] = e.name
        package = e.name.lower()
        if package in packages:
            errors.append(f"Entities '{packages[package]}' and '{e.name}' map to the same package '{package}'")
        else:
            packages[package] = e.name
    return errors


# ----------------------------------------------------------------------------- relation analysis


@dataclass
class _Owning:
    owner: str
    name: str
    kind: str
    target: str
    required: bool
    unique: bool
    synthetic: bool = False
    declared_as: str | None = None
    inverse_name: str | None = None


@dataclass
class _Inverse:
    owner: str
    name: str
    target: str
    mapped_by: str
    cascade: str | None
    orphan_removal: bool
    generated: bool


@dataclass
class _ManyToMany:
    owner: str
    name: str
    target: str


@dataclass
class _Analysis:
    errors: list[str] = field(default_factory=list)
    owning: list[_Owning] = field(default_factory=list)
    inverses: list[_Inverse] = field(default_factory=list)
    m2m: list[_ManyToMany] = field(default_factory=list)


def _collection_id_field(name: str) -> str:
    return f"{singularize(name)}Ids"


def _check_mapped_by(ename: str, rname: str, r, entities, mapped) -> str | None:
    where = f"Entity '{ename}' relation '{rname}'"
    target = entities[r.target]
    owner_rel = target.relations.get(r.mapped_by)
    if owner_rel is None:
        back = [n for n, x in target.relations.items() if x.type == "many-to-one" and x.target == ename]
        hint = f"many-to-one relations of '{target.name}' pointing back: {', '.join(back)}" if back else (
            f"'{target.name}' needs a many-to-one relation to '{ename}'")
        return f"{where}: mappedBy '{r.mapped_by}' is not a relation of '{target.name}'; {hint}"
    if owner_rel.type != "many-to-one":
        return (
            f"{where}: mappedBy '{r.mapped_by}' must name the owning many-to-one relation of '{target.name}', "
            f"but '{target.name}.{r.mapped_by}' is {owner_rel.type} (not an owning many-to-one)"
        )
    if owner_rel.target != ename:
        return (
            f"{where}: mappedBy '{r.mapped_by}' points to '{owner_rel.target}', "
            f"but '{target.name}.{r.mapped_by}' must point back to '{ename}'"
        )
    if owner_rel.inverse is not None:
        return (
            f"{where}: '{target.name}.{r.mapped_by}' already declares `inverse: {owner_rel.inverse}`; "
            f"use either `inverse` on the many-to-one or `mappedBy` on the one-to-many, not both"
        )
    if (target.name, r.mapped_by) in mapped:
        return (
            f"{where}: '{target.name}.{r.mapped_by}' is already the mappedBy target of "
            f"'{mapped[(target.name, r.mapped_by)]}'"
        )
    return None


def _analyze(entities: dict[str, EntitySpec]) -> _Analysis:
    a = _Analysis()
    used = {k: set(e.fields) | set(e.relations) | BASE_ENTITY_MEMBERS for k, e in entities.items()}
    mapped: dict[tuple[str, str], str] = {}
    pending: list[tuple[str, str, object]] = []

    for ename, e in entities.items():
        for rname, r in e.relations.items():
            where = f"Entity '{ename}' relation '{rname}'"
            if r.target not in entities:
                a.errors.append(
                    f"{where}: target '{r.target}' does not exist (declared entities: {', '.join(sorted(entities))})"
                )
            elif r.type in ("many-to-one", "one-to-one"):
                a.owning.append(_Owning(ename, rname, r.type, r.target, r.required, r.type == "one-to-one"))
            elif r.type == "many-to-many":
                a.m2m.append(_ManyToMany(ename, rname, r.target))
            elif r.mapped_by is None:
                pending.append((ename, rname, r))
            else:
                error = _check_mapped_by(ename, rname, r, entities, mapped)
                if error:
                    a.errors.append(error)
                else:
                    mapped[(r.target, r.mapped_by)] = f"{ename}.{rname}"
                    a.inverses.append(_Inverse(ename, rname, r.target, r.mapped_by, r.cascade, r.orphan_removal, False))

    # `inverse:` shortcut on many-to-one
    for o in [o for o in a.owning if o.kind == "many-to-one"]:
        inverse = entities[o.owner].relations[o.name].inverse
        if inverse is None:
            continue
        where = f"Entity '{o.owner}' relation '{o.name}'"
        if not MEMBER_NAME_RE.match(inverse) or inverse in JAVA_RESERVED_WORDS:
            a.errors.append(f"{where}: inverse name '{inverse}' must be a camelCase, non-reserved identifier")
        elif inverse in used[o.target]:
            a.errors.append(
                f"{where}: inverse name '{inverse}' collides with an existing field/relation of '{o.target}'"
            )
        else:
            used[o.target].add(inverse)
            a.inverses.append(_Inverse(o.target, inverse, o.owner, o.name, None, False, True))

    owning_by_key = {(o.owner, o.name): o for o in a.owning}
    for inv in a.inverses:
        owner_rel = owning_by_key.get((inv.target, inv.mapped_by))
        if owner_rel is not None:
            owner_rel.inverse_name = inv.name

    # many-to-many declared on both sides
    for m in a.m2m:
        for other in a.m2m:
            if other.owner == m.target and other.target == m.owner and (m.owner, m.name) < (other.owner, other.name):
                a.errors.append(
                    f"Many-to-many between '{m.owner}' and '{m.target}' is declared on both sides "
                    f"({m.owner}.{m.name} and {other.owner}.{other.name}); declare it on exactly one side"
                )

    # unidirectional one-to-many -> synthetic owning many-to-one on the child
    for ename, rname, r in pending:
        child = r.target
        candidates = [lower_first(ename), lower_first(ename) + upper_first(rname)]
        chosen = next((c for c in candidates if c not in used[child]), None)
        if chosen is None:
            a.errors.append(
                f"Entity '{ename}' relation '{rname}': cannot generate the FK attribute on '{child}' "
                f"(names {candidates} are taken); use `mappedBy` with an explicit many-to-one instead"
            )
            continue
        used[child].add(chosen)
        a.owning.append(_Owning(child, chosen, "many-to-one", ename, r.required, False, True, rname))

    _check_columns_and_dto_names(entities, a)
    return a


def _check_columns_and_dto_names(entities: dict[str, EntitySpec], a: _Analysis) -> None:
    for ename, e in entities.items():
        columns: dict[str, str] = {}
        props: dict[str, str] = {}

        def claim(table: dict[str, str], key: str, label: str, what: str) -> None:
            if key in table:
                a.errors.append(f"Entity '{ename}': {what} '{key}' is produced by both {table[key]} and {label}")
            else:
                table[key] = label

        for fname in e.fields:
            claim(columns, snake_case(fname), f"field '{fname}'", "column")
            claim(props, fname, f"field '{fname}'", "DTO property")
        for o in (o for o in a.owning if o.owner == ename):
            label = f"relation '{o.name}'"
            claim(columns, snake_case(o.name) + "_id", label, "column")
            claim(props, o.name + "Id", label, "DTO property")
        for m in (m for m in a.m2m if m.owner == ename):
            claim(props, _collection_id_field(m.name), f"relation '{m.name}'", "DTO property")


def validate_relations(entities: dict[str, EntitySpec]) -> list[str]:
    """Check relation targets, ``mappedBy``/``inverse`` pairing, many-to-many sides and generated-name collisions."""
    return _analyze(entities).errors


# ----------------------------------------------------------------------------- ordering


def _required_edges(a: _Analysis) -> list[_Owning]:
    return [o for o in a.owning if o.required]


def _strongly_connected(nodes: set[str], deps: dict[str, set[str]]) -> list[list[str]]:
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    result: list[list[str]] = []
    counter = [0]

    def visit(v: str) -> None:
        index[v] = low[v] = counter[0]
        counter[0] += 1
        stack.append(v)
        on_stack.add(v)
        for w in sorted(deps.get(v, ())):
            if w not in nodes:
                continue
            if w not in index:
                visit(w)
                low[v] = min(low[v], low[w])
            elif w in on_stack:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            component = []
            while True:
                w = stack.pop()
                on_stack.discard(w)
                component.append(w)
                if w == v:
                    break
            result.append(sorted(component))

    for node in sorted(nodes):
        if node not in index:
            visit(node)
    return result


def topological_order(entities: dict[str, EntitySpec]) -> list[str]:
    """Entity names ordered so every REQUIRED to-one target precedes its owner (alphabetical tie-break).

    Only required many-to-one / one-to-one edges (including required unidirectional one-to-many) count.
    Optional edges never affect order. Raises ``ValueError`` naming the members of any required cycle.
    """
    edges = _required_edges(_analyze(entities))
    deps: dict[str, set[str]] = {n: set() for n in entities}
    dependents: dict[str, set[str]] = {n: set() for n in entities}
    for o in edges:
        deps[o.owner].add(o.target)
        dependents[o.target].add(o.owner)
    remaining = {n: len(d) for n, d in deps.items()}
    ready = [n for n, c in remaining.items() if c == 0]
    heapq.heapify(ready)
    order: list[str] = []
    while ready:
        node = heapq.heappop(ready)
        order.append(node)
        for dep in dependents[node]:
            remaining[dep] -= 1
            if remaining[dep] == 0:
                heapq.heappush(ready, dep)
    if len(order) == len(entities):
        return order

    stuck = {n for n in entities if n not in set(order)}
    problems = []
    for component in _strongly_connected(stuck, deps):
        if len(component) == 1 and component[0] not in deps[component[0]]:
            continue
        members = set(component)
        via = sorted(f"{o.owner}.{o.name}" for o in edges if o.owner in members and o.target in members)
        subject = (
            f"Entity '{component[0]}' has a required relation to itself"
            if len(component) == 1
            else f"Required relations form a cycle between {', '.join(component)}"
        )
        problems.append(
            f"{subject} (via {', '.join(via)}); make at least one of these relations optional (`required: false`)"
        )
    raise ValueError("\n".join(problems))


# ----------------------------------------------------------------------------- resolution


def _make_fk(table: str, column: str, ref_table: str, required: bool, unique: bool, deferred: bool,
             entity: str | None, index: bool = True) -> ForeignKey:
    return ForeignKey(
        table=table,
        column=column,
        ref_table=ref_table,
        constraint_name=_ident("fk", table, column),
        index_name=_ident("idx", table, column) if index and not unique else None,
        required=required,
        unique=unique,
        on_delete="RESTRICT",
        deferred=deferred,
        unique_name=_ident("uq", table, column) if unique else None,
        entity=entity,
    )


def _resolve_field(e: EntitySpec, table: str, fname: str, f) -> ResolvedField:
    enum_class = enum_class_name(e.name, fname) if f.type == "enum" else None
    info = resolve_type(f, enum_class)
    column = snake_case(fname)
    return ResolvedField(
        name=fname,
        getter="get" + upper_first(fname),
        setter="set" + upper_first(fname),
        column=column,
        type=f.type,
        java_type=info.java,
        imports=info.imports,
        sql_type=info.sql,
        required=f.required,
        unique=f.unique,
        unique_name=_ident("uq", table, column) if f.unique else None,
        default_sql=default_sql(f),
        validation=info.validation,
        validation_imports=info.validation_imports,
        is_text=bool(f.text),
        length=info.length,
        precision=f.precision,
        scale=f.scale,
        is_enum=f.type == "enum",
        enum_class=enum_class,
        enum_values=tuple(f.values) if f.type == "enum" else (),
        enum_import_suffix=f"{e.name.lower()}.entity.{e.name}.{enum_class}" if enum_class else None,
        sample_value=info.sample_value,
        sample_value_alt=info.sample_value_alt,
    )


def _join_table_name(m: _ManyToMany, tables: dict[str, str], taken: set[str]) -> str:
    if m.owner == m.target:
        name = _ident(tables[m.owner], snake_case(m.name))
    else:
        name = _ident(*sorted([tables[m.owner], tables[m.target]]))
    if name in taken:
        name = _ident(name, snake_case(m.name))
    base, n = name, 2
    while name in taken:
        name = _ident(base, str(n))
        n += 1
    return name


def _join_columns(m: _ManyToMany) -> tuple[str, str]:
    left = snake_case(m.owner) + "_id"
    right = snake_case(m.target) + "_id"
    if left == right:
        right = singularize(snake_case(m.name)) + "_id"
        if right == left:
            right = "related_" + right
    return left, right


def resolve_model(entities: dict[str, EntitySpec]) -> Model:
    """Validate the entity set and resolve it into the template-ready ``Model`` (see ``core/entity_model.py``).

    Raises one ``ValueError`` listing every validation error. With no entities returns an empty model whose
    ``changelog_files`` are just the fixed ``001``/``002`` files.
    """
    errors = validate_names(entities) + validate_relations(entities)
    if errors:
        raise ValueError(_join(errors))
    try:
        order = topological_order(entities)
    except ValueError as exc:
        raise ValueError(_join(str(exc).split("\n"))) from exc

    a = _analyze(entities)
    tables = {k: derive_table_name(e) for k, e in entities.items()}
    index_of = {name: CHANGELOG_START + i for i, name in enumerate(order)}
    owning = {(o.owner, o.name): o for o in a.owning}
    m2m = {(m.owner, m.name): m for m in a.m2m}

    # join tables (named in declaration order for stable collision handling, then sorted by name)
    taken = set(tables.values()) | RESERVED_TABLES
    join_info: list[tuple[str, _ManyToMany]] = []
    for m in a.m2m:
        name = _join_table_name(m, tables, taken)
        taken.add(name)
        join_info.append((name, m))
    join_info.sort(key=lambda item: item[0])
    join_start = CHANGELOG_START + len(order)
    join_tables: list[JoinTable] = []
    join_by_rel: dict[tuple[str, str], JoinTable] = {}
    for j, (name, m) in enumerate(join_info):
        left, right = _join_columns(m)
        jt = JoinTable(
            name=name, left_entity=m.owner, right_entity=m.target, left_column=left, right_column=right,
            left_table=tables[m.owner], right_table=tables[m.target],
            changelog_file=f"{join_start + j:03d}-create-{name}-table.sql", relation=f"{m.owner}.{m.name}",
            foreign_keys=[
                _make_fk(name, left, tables[m.owner], True, False, False, None, index=False),
                _make_fk(name, right, tables[m.target], True, False, False, None),
            ],
        )
        join_tables.append(jt)
        join_by_rel[(m.owner, m.name)] = jt

    resolved: dict[str, ResolvedEntity] = {}
    for ename in order:
        e = entities[ename]
        table = tables[ename]
        fields = [_resolve_field(e, table, fname, f) for fname, f in e.fields.items()]
        relations: list[ResolvedRelation] = []
        fks: list[ForeignKey] = []
        names = [n for n, r in e.relations.items() if r.type != "one-to-many"]
        synthetic = [o.name for o in a.owning if o.owner == ename and o.synthetic]
        for rname in names + synthetic:
            if (ename, rname) in m2m:
                m = m2m[(ename, rname)]
                jt = join_by_rel[(ename, rname)]
                relations.append(_to_relation(ename, rname, "many-to-many", m.target, tables, False, False,
                                              None, jt, None, False, None))
            else:
                o = owning[(ename, rname)]
                fk = _make_fk(table, snake_case(rname) + "_id", tables[o.target], o.required, o.unique,
                              not o.required, ename)
                fks.append(fk)
                relations.append(_to_relation(ename, rname, o.kind, o.target, tables, o.required, o.unique,
                                              fk, None, o.inverse_name, o.synthetic, o.declared_as))
        inverses = [_to_inverse(inv) for inv in a.inverses if inv.owner == ename]
        enums = [EnumDescriptor(f.enum_class, f.enum_values, f.name) for f in fields if f.is_enum]
        imports = {imp for f in fields for imp in f.imports}
        if any(r.is_collection for r in relations):
            imports |= {"java.util.Set", "java.util.HashSet"}
        if inverses:
            imports |= {"java.util.List", "java.util.ArrayList"}
        resolved[ename] = ResolvedEntity(
            name=ename,
            var_name=lower_first(ename),
            package=ename.lower(),
            table=table,
            plural_path=kebab_case(pluralize(snake_case(ename))),
            changelog_index=index_of[ename],
            changelog_file=f"{index_of[ename]:03d}-create-{table}-table.sql",
            fields=fields,
            owning_relations=relations,
            inverse_relations=inverses,
            enums=enums,
            foreign_keys=fks,
            imports=tuple(sorted(imports)),
        )

    ordered = [resolved[n] for n in order]
    deferred = [fk for ent in ordered for fk in ent.foreign_keys if fk.deferred]
    files: list[str] = []
    if not ordered:
        files.append("001-create-example-table.sql")
    files.append("002-create-notifications.sql")
    files += [ent.changelog_file for ent in ordered]
    files += [jt.changelog_file for jt in join_tables]
    if deferred:
        files.append(f"{join_start + len(join_tables):03d}-add-constraints.sql")
    return Model(entities=ordered, join_tables=join_tables, fk_constraints=deferred,
                 changelog_start=CHANGELOG_START, changelog_files=files)


def _to_relation(owner: str, name: str, kind: str, target: str, tables: dict[str, str], required: bool,
                 unique: bool, fk: ForeignKey | None, jt: JoinTable | None, inverse_name: str | None,
                 synthetic: bool, declared_as: str | None) -> ResolvedRelation:
    is_collection = kind == "many-to-many"
    return ResolvedRelation(
        name=name, kind=kind, owner=owner, target=target, target_package=target.lower(),
        target_var=lower_first(target), target_table=tables[target],
        java_type=f"Set<{target}>" if is_collection else target,
        is_collection=is_collection,
        collection_type="Set" if is_collection else None,
        collection_impl="HashSet" if is_collection else None,
        column=fk.column if fk else None,
        required=required, unique=unique,
        fk_name=fk.constraint_name if fk else None,
        index_name=fk.index_name if fk else None,
        unique_name=fk.unique_name if fk else None,
        deferred=fk.deferred if fk else False,
        id_field=_collection_id_field(name) if is_collection else name + "Id",
        id_java_type="Set<UUID>" if is_collection else "UUID",
        join_table=jt.name if jt else None,
        join_column=jt.left_column if jt else None,
        inverse_join_column=jt.right_column if jt else None,
        inverse_name=inverse_name, synthetic=synthetic, declared_as=declared_as,
        on_delete="RESTRICT", getter="get" + upper_first(name), setter="set" + upper_first(name),
    )


def _to_inverse(inv: _Inverse) -> ResolvedInverse:
    singular = singularize(inv.name)
    return ResolvedInverse(
        name=inv.name, getter="get" + upper_first(inv.name), singular=singular,
        add_helper="add" + upper_first(singular), remove_helper="remove" + upper_first(singular),
        target=inv.target, target_package=inv.target.lower(), target_var=lower_first(inv.target),
        mapped_by=inv.mapped_by, mapped_by_setter="set" + upper_first(inv.mapped_by),
        cascade=inv.cascade, orphan_removal=inv.orphan_removal, generated=inv.generated,
        collection_type="List", collection_impl="ArrayList",
    )
