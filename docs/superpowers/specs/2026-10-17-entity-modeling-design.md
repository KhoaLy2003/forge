# Backend Entity Modeling — Design

Status: draft for review (2026-10-17). Scope: `backend/` (Forge) only.

## Intent

Forge exists to speed up scaffolding a **new** project (day zero). Today a generated project ships one reference slice (`Example`). The goal is to let the user declare real domain entities, with fields and relational relationships, and have Forge generate their full CRUD slices and Liquibase schema so the project is usable immediately.

Fixed by the user, out of scope here: build tool (Maven), Java 21, Spring Boot 4, PostgreSQL, monorepo layout. No NoSQL. No `forge add` for existing projects (possible later; the model defined here is designed to be reusable by it).

## Roadmap (separate spec → plan → implementation cycles)

1. **Entity modeling (this spec).**
2. Feature modules (`--features`: security/JWT, Redis, messaging, ...) and DevOps files (Dockerfile, extended CI) as features. (Logging and actuator/Prometheus monitoring are delivered by `2026-10-17-observability-design.md`, and a database-outbox notification module by `2026-10-17-notification-module-design.md`; both are part of `base-layered`, not opt-in features.)
3. Presets (`--preset`) and the shared feature registry.
4. Extra architecture templates (hexagonal, modular monolith, ...).
5. Validation changes: local checks stay Docker-free; Testcontainers-backed tests run only in CI/CD.

## Input: the entity spec

One model (`EntitySpec`), two ways to fill it:
- `forge new --from forge.yaml` (non-interactive; works in CI/scripts).
- The wizard asks for entities, fields and relations interactively and can save the result as `forge.yaml`.

Entity declarations are **not** CLI flags (too long to type, hard to express).

```yaml
entities:
  Customer:
    fields:
      name:   { type: string, length: 100, required: true }
      email:  { type: string, unique: true, required: true }
      status: { type: enum, values: [ACTIVE, SUSPENDED] }
  Order:
    table: customer_orders          # optional; default = snake_case plural
    fields:
      total:    { type: decimal, precision: 12, scale: 2, required: true }
      placedAt: { type: instant }
    relations:
      customer: { type: many-to-one, target: Customer, required: true, inverse: orders }
      items:    { type: one-to-many, target: OrderItem, mappedBy: order }
  Product:
    relations:
      categories: { type: many-to-many, target: Category }
```

`forge.yaml` may also carry the project parameters (name, group id, artifact id, template) so a whole run is reproducible from one file. CLI flags override file values.

## Validation (fail early, before anything is written)

All rules live in `core/` alongside the existing config validation and surface through the same error path as `ForgeConfig`.

- Entity names: PascalCase, singular, not a Java reserved word (reuse `JAVA_RESERVED_WORDS`), unique.
- Field/relation names: camelCase, not a Java reserved word, unique within an entity, must not collide with `BaseEntity` members (`id`, `version`, `createdAt`, `updatedAt`, `deletedAt`).
- Table names: derived as snake_case plural; **rejected if a reserved SQL word** (`order`, `user`, `group`, ...). The error suggests an explicit `table:` override. This catches the very common `Order` trap.
- Relation targets must exist; `mappedBy` must reference a real owning relation of the target.
- Dependency graph: required many-to-one/one-to-one edges are topologically sorted for changelog order; a cycle of required relations is an error (optional edges may form cycles and are added with the FK in the same file because both tables are created before constraints are applied — see Liquibase).
- `template: minimal` plus entities is an error (minimal has no Liquibase). Entities require `base-layered`.

## Types

A single mapping table is the source of truth; each type carries its Java type, Liquibase/SQL type, imports and Bean Validation annotations, so templates contain no type logic.

| Spec type | Java | SQL | Notes |
|---|---|---|---|
| `string` | `String` | `VARCHAR(length)` (default 255) | `length` optional; `text: true` -> `TEXT` |
| `int` / `long` | `Integer` / `Long` | `INTEGER` / `BIGINT` | |
| `decimal` | `BigDecimal` | `NUMERIC(p,s)` | use for money; `precision`/`scale` required |
| `boolean` | `Boolean` | `BOOLEAN` | |
| `date` / `instant` | `LocalDate` / `Instant` | `DATE` / `TIMESTAMP WITH TIME ZONE` | |
| `uuid` | `UUID` | `UUID` | |
| `enum` | generated enum | `VARCHAR(20)` | `EnumType.STRING`; `values` required |

Common modifiers: `required` (NOT NULL + `@NotNull`/`@NotBlank` on the create DTO), `unique` (unique constraint + 409 via existing `ConflictException` path), `default`.

IDs are `UUID`, inherited from the existing `BaseEntity` together with audit timestamps, optimistic-locking `version`, and the `deletedAt` soft-delete marker. Generated entities extend `BaseEntity`; they do not redefine these.

## Relationships (relational best practice)

- **many-to-one** is the canonical, *owning* side: FK column + `@ManyToOne(fetch = LAZY)`. Always declared explicitly.
- **one-to-many** is the inverse side and is **opt-in and unidirectional by default**. A bidirectional pair exists only when requested (`inverse:` on the many-to-one, or a one-to-many with `mappedBy`). Bidirectional pairs get add/remove helper methods that keep both sides in sync. Rationale: unidirectional avoids sync bugs, accidental N+1 and serialization loops.
- **many-to-many** declared on one (owning) side; Forge generates the join table with a composite primary key and FKs on both columns. No cascade by default.
- **one-to-one** is a many-to-one with a unique constraint on the FK.
- Cascade/orphan removal are off by default; `cascade: all` and `orphanRemoval` only on one-to-many composition (child lifecycle owned by parent), never on many-to-one or many-to-many.
- All associations are `LAZY`. Foreign keys get an index. DTOs expose related ids (`customerId`, `itemIds` only if requested), never nested entities, so there is no lazy-loading or recursion hazard in responses.
- Delete behaviour is explicit: FK `ON DELETE RESTRICT` by default (the service's existing soft-delete path stays the normal route).

## Generation architecture

### Fan-out renderer (the main structural change)

`core/renderer.py` is a strict file->file mapper today. Entity generation needs one template set rendered once per entity. Design:

- New template directory `templates/_entity/` holding a single entity slice, with paths/contents parameterised on `entity` (e.g. `{{ package_path }}/{{ entity.package }}/entity/{{ entity.name }}.java`), mirroring the current `example/` layout so the `Example` slice becomes the reference for the template.
- `render_tree`/`resolve_tree` gain a "fan-out" pass: for each entity, render `_entity/` with the base context plus `entity`; results are merged into the same output path list used for the preview and the structural check. `_shared` rendering is unchanged.
- When entities are declared, the `Example` slice is excluded via the existing `EXCLUDES` mechanism (the user's entities replace it). With no entities, behaviour is exactly as today.

### Liquibase

- Existing style is kept: `.sql` formatted changelogs, `db.changelog-master.xml` includes them.
- Numbers `001` (the `Example` table, dropped when entities are declared) and `002` (the notification module, `002-create-notifications.sql`) are reserved, so entity files start at `003`. One file per entity table, numbered in topological order (`003-create-customers-table.sql`, ...), then one file per many-to-many join table, then FK/index constraints applied after all tables exist, so optional cycles are safe. The master changelog is generated from the sorted list by a loop (a Jinja2 `for` over the model, not hand-listed includes).
- Each changeset has a `rollback`, matching the current file.

### Per-entity output

Entity, repository, service interface and implementation, controller, create/update/response DTOs, MapStruct mapper, enum classes, one Liquibase file, and unit/slice tests (service, mapper, controller) mirroring the Example tests. Repository (Testcontainers) tests are generated but run only in CI per the roadmap item 5.

### Code placement

New modules under `backend/core/`, one purpose each: `entity_spec.py` (pydantic models + parsing `forge.yaml`), `entity_rules.py` (name/SQL-reserved/graph validation, topological sort), `type_map.py` (type table), and the fan-out logic in `renderer.py`. `ForgeConfig` gains an `entities` field and `template_context()` exposes the resolved model (`entities`, ordered list, join tables). `wizard.py` gains an entity-collection step. `cli.py` gains `--from`. Per project convention, `EXPECTED_STRUCTURAL_PATHS` is extended per entity.

## Testing

- Unit tests per new module (name rules, SQL reserved words, type table, relation validation, topological order, cycle detection, inverse resolution).
- Renderer tests for fan-out path resolution (N entities -> N slices, `Example` excluded).
- Template-content tests asserting generated Liquibase/entity text for each relation kind.
- End-to-end `test_generation.py` gains a fixture project with ~4 entities covering all four relation kinds, each type, and an enum; it must pass the real `mvn compile`. Generated Java tests are compiled (`test-compile`) locally; running Testcontainers tests is CI-only.

## Local experimentation

A `_testing/` directory at the repo root is the scratch area for running scaffold output during development. It is git-ignored (added to `.gitignore`), never committed, and nothing is written outside the repo root.

## Out of scope for the first version

Composite primary keys, inheritance mapping, custom queries, per-relation fetch tuning, auditing beyond `BaseEntity`, non-UUID ids, `forge add` on existing projects, and any non-relational store.

## Risks

- Generated code drifting from the model: mitigated by the compile-checked fixture project and strict Jinja2 undefined.
- The fan-out change touches the renderer shared by every template: mitigated by keeping `_shared` rendering untouched and covering the no-entity path with the existing tests.
