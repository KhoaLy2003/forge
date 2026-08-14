# Code Generator / Project Scaffolding Tool — Plan

## Goal

Speed up the "init source code" phase for new services by generating a
ready-to-build Java + Spring Boot + PostgreSQL project from a pre-built
template, instead of creating it by hand. The tool should be faster than
manual setup *and* trustworthy enough that people actually use it instead of
copy-pasting an old project.

## Tech Stack (generated projects)

- Java 21x
- Spring Boot 4x
- PostgreSQL

## Tooling (the generator itself)

- Python (script/CLI) — chosen for templating maturity (Jinja2), cross-platform
  support, and easy CLI frameworks (Click / Typer)

---

## Original Idea (starting point)

- Script initializes a project from a pre-built template
- User provides required parameters to run the script, including:
  - project name
  - path location
  - ... (to be expanded — see Parameters below)
- **Preview generation**: print the project tree structure (folders, files,
  etc.) for user preview, and ask user to continue or not
- **Progress tracking**: print current status while the script runs
- **Validate run after generation**: use a build command to verify the
  generated project actually builds

### Original proposed source structure

```
generator
- README.md
- CHANGELOG.md          # version change log
- QUICK_REFERENCE.md    # quick guide about commands to run script
- <script file(s)>
- templates/
...
```

---

## Review & Improvements

### 1. Templates need a real strategy, not a single fixed folder

A single hardcoded template will go stale and won't scale to different
project shapes. Better approach: treat templates as a **versioned,
parameterized directory tree** (Jinja2 for both file/folder names and file
contents), with support for **feature modules** layered on top of a base
(e.g. with/without Kafka, with/without Redis cache, monolith vs modular
layout). This avoids duplicating whole template trees for every combination.

### 2. Parameters need a schema, not just a list

Beyond project name + path, likely needed:
- Java version pin
- Spring Boot version
- Build tool: Maven or Gradle
- Group / artifact coordinates (Maven) or module path (Gradle)
- Package structure style: layered vs hexagonal/DDD
- DB migration tool: Flyway vs Liquibase
- Optional modules: security, actuator, testcontainers, docker-compose for
  local PostgreSQL

Define all of this in a single `config.yaml` / `schema.json` so the CLI, the
preview step, and the validation step all read from **one source of truth**
instead of drifting apart over time.

### 3. Validation should be layered, not just "does it build"

- **Structural check** — did all expected files actually get created
- **Compile check** — `mvn compile` / `./gradlew compileJava`
- **Boot smoke test** — does the app context actually start (e.g. run with a
  timeout, or a generated slice test that loads the context). A project can
  compile fine and still fail to boot (bad `application.yml`, missing DB
  connection handling, etc.)
- **DB connectivity check** — optional/soft warning rather than a hard
  failure, since PostgreSQL may not be running yet at generation time

### 4. Idempotency / re-run safety

Decide up front what happens if the target folder already exists or the user
re-runs with the same project name: abort, merge, or force-overwrite flag.
This is a common source of frustration in scaffolding tools if left
undefined.

### 5. Post-generation "next steps" output

After a successful run, print exactly what to do next — `cd` command,
`docker compose up -d`, `mvn spring-boot:run` / `./gradlew bootRun`, and any
generated DB URL/credentials. The manual pain isn't just file creation, it's
remembering the setup steps afterward — closing that gap is a big part of
what makes this "faster than manual."

---

## Refined Source Structure

```
generator/
  README.md
  CHANGELOG.md
  QUICK_REFERENCE.md
  cli.py                    # entry point
  core/
    config_schema.py        # parameter validation (single source of truth)
    tree_preview.py         # renders tree, prompts y/n
    progress.py             # step tracker / logger
    renderer.py             # Jinja2 rendering engine
    validator.py            # structural + compile + boot checks
  templates/
    base-layered/
    base-hexagonal/
    modules/                # optional add-ons (flyway, testcontainers, docker-pg)
  tests/
    test_generation.py      # generate into tmpdir, assert it actually builds
```

Note: `tests/` is a deliberate addition — since the tool's entire job is
"produce working code," it needs its own CI that generates a real project and
builds it, or regressions in the templates will slip through silently.

---

## Naming Suggestions

| Name | Why it fits |
|---|---|
| **Blueprint** | Matches the "preview the plan, then build it" flow directly |
| **Forge** / **SpringForge** | Implies shaping something real, fast |
| **Scaffy** | Playful, scaffold-y, memorable |
| **Baseline** | Evokes a known-good starting point |
| **Genesis-JVM** / **javagen** | Plain, descriptive, searchable |

Leaning toward **Blueprint** or **Forge** — both map directly to the tool's
two standout features (preview before generating, then validate after)
rather than being generic scaffolding-tool names.

---

## Open Questions for Review

- [ ] Maven or Gradle as the default (or support both from day one)?
- [ ] Which package structure is the default: layered or hexagonal/DDD?
- [ ] Should optional modules (Kafka, Redis, security) be in scope for v1, or
      added later?
- [ ] Preferred behavior when target folder already exists?
- [ ] Final name pick?
