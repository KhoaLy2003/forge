# Forge Enhancements — Design

Four independent, small enhancements to the already-implemented Forge v1
scaffolding tool (see `2026-08-13-forge-scaffolding-tool-design.md` and its
implementation plan for v1 context).

## 1. Tree-structured preview

**Current behavior:** `core/tree_preview.format_tree(paths: list[Path]) -> str`
prints a flat, alphabetically sorted list of forward-slash-normalized
relative paths, one per line.

**New behavior:** same signature, same inputs (a flat list of file `Path`
objects — `resolve_tree` never returns directories, since directories are
always implied by their files' paths). Internally, build a nested dict from
each path's parts (a node with children is a directory; a leaf node — no
children — is a file), then render recursively with `tree`-command-style
box-drawing connectors: `├── ` for a non-last sibling, `└── ` for the last
sibling at a level, `│   ` / `    ` as the continuation prefix for deeper
levels depending on whether the ancestor was last. Sort alphabetically at
each level (directories and files intermixed, matching the standard `tree`
command's default — not a directories-first sort).

Example, for a generated project:
```
docker-compose.yml
pom.xml
src
└── main
    ├── java
    │   └── com
    │       └── example
    │           └── demoservice
    │               └── DemoServiceApplication.java
    └── resources
        └── application.yml
```

`confirm()` is unchanged — it still just prints whatever text it receives
and prompts. `cli.py`'s call site (`confirm(format_tree(tree))`) is
unaffected.

Existing tests for `format_tree` (`tests/test_tree_preview.py`) get
rewritten to assert against the new nested-tree output instead of the old
flat-list output.

## 2. Docstrings

Add a module-level docstring (one short paragraph: what this file is
responsible for) to the top of `cli.py` and every file under `core/`:
`config_schema.py`, `progress.py`, `renderer.py`, `tree_preview.py`,
`validator.py`, `wizard.py`. Add a one-line PEP 257-style docstring to every
public function and class in those files, stating what it does, not how
(e.g. `"""Render a Jinja2 template tree to a directory."""`, not a
step-by-step description of the loop inside it).

**Scope:** `cli.py` + `core/*.py` only. `tests/*.py` is explicitly excluded
— test function names already document behavior, and this keeps the change
focused on the library code that ships in the installable package.

## 3. SQL-format Liquibase migrations

Switches the generated project's migrations from the current YAML-based
setup to the `java-spring-boot` skill's standard: Liquibase Formatted SQL
with an XML master changelog.

**File changes in `templates/base-layered/src/main/resources/db/changelog/`:**
- `db.changelog-master.yaml` → `db.changelog-master.xml`: standard Liquibase
  XML root (`<databaseChangeLog>` with the liquibase.org XML namespace),
  `<include file="db/changelog/001-create-example-table.sql" relativeToChangelogFile="false"/>`
- `001-create-example-table.yaml` → `001-create-example-table.sql`:
  - starts with `-- liquibase formatted sql`
  - `-- changeset forge:<epoch-millis-id>` header (a fixed literal epoch-ms
    value baked into the template — this is a static template with exactly
    one migration ever, so a hardcoded unique id is sufficient; no need to
    generate one dynamically at template-render time)
  - a `-- comment:` line describing the change
  - `CREATE TABLE example (id BIGSERIAL PRIMARY KEY, name VARCHAR(255));` —
    `BIGSERIAL` is PostgreSQL-native auto-increment, compatible with the
    `Example` entity's existing `@GeneratedValue(strategy = GenerationType.IDENTITY)`
  - a mandatory `-- rollback DROP TABLE example;` line

**Other changes:**
- `templates/base-layered/src/main/resources/application.yml`'s
  `spring.liquibase.change-log` value updated from
  `classpath:db/changelog/db.changelog-master.yaml` to `...master.xml`
- `tests/test_template_content.py`'s `EXPECTED_TEMPLATE_FILES` list updated
  to the two new filenames in place of the two old ones

No change to `Example.java`, `ExampleRepository.java`, `ExampleService.java`,
or `ExampleController.java` — only the migration files and the one config
path reference change. The generated table shape (columns `id`, `name`) is
identical to today's; only the migration file format changes.

## 4. Numbered progress steps

**Current behavior:** `core/progress.step(message: str) -> None` prints
`f"-> {message}"`.

**New behavior:** `core/progress.step(message: str, index: int, total: int) -> None`
prints `f"[{index}/{total}] {message}"`.

`cli.py`'s three existing `step()` call sites become:
- `step("Writing project files...", 1, 3)`
- `step("Running structural check...", 2, 3)`
- `step("Running compile check...", 3, 3)`

The final `"Project generated successfully!"` line stays a separate,
unnumbered completion message — it is not one of the three numbered
progress stages, since it only prints after all three have already
succeeded.

`tests/test_progress.py`'s existing test is updated for the new signature
and output format.

## Testing

Each of the 4 changes updates its existing test file in place (no new test
files needed): `test_tree_preview.py`, `test_template_content.py`,
`test_progress.py`. Docstrings (item 2) have no dedicated test — they're
verified by code review / self-review, not automated assertion. After all
four changes, the full suite (`test_generation.py` in particular) must
still pass, including the real `mvn compile` against the regenerated
migration files, proving the SQL-format migration is valid and Liquibase
can actually apply it at schema level (compile alone doesn't execute
migrations, but a broken changelog reference or malformed SQL syntax would
still be worth having *some* signal for — see Open Question below).

## Open Question

`mvn compile` does not execute Liquibase migrations (that happens at
application boot via `spring.liquibase.change-log`), so item 3's SQL syntax
correctness is not exercised by the existing structural + compile
validation pipeline. This is an accepted v1 gap carried over from the
original design (boot smoke test was explicitly deferred) — not a new gap
introduced by this enhancement, so no new validation step is added here.
