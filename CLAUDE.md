# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Forge is a Python CLI (Typer-based) that scaffolds a ready-to-build Java + Spring Boot 4 + PostgreSQL project from a single Jinja2 template. Running `forge new` generates a complete, compiling Maven project — not a bare skeleton.

## Commands

```bash
# Setup
py -m venv .venv
.venv\Scripts\pip install -e ".[dev]"

# Run the CLI
.venv\Scripts\forge new
.venv\Scripts\forge new --name my-service --path C:\projects --group-id com.example --artifact-id my-service

# Tests
.venv\Scripts\pytest -v
.venv\Scripts\pytest tests/test_renderer.py -v      # single file
.venv\Scripts\pytest tests/test_renderer.py::test_name -v   # single test
```

`mvn` must be on PATH for `test_generation.py` and the validator's compile check to pass — both actually shell out to Maven against a generated project.

## Architecture

The pipeline in `cli.py`'s `new` command is the whole system: **wizard → preview → render → validate**, each stage a separate module in `core/`.

1. **`core/wizard.py`** (`collect_params`) — fills in whatever CLI flags were omitted by prompting interactively, reprompting on validation failure. Returns a `ForgeConfig`.
2. **`core/config_schema.py`** (`ForgeConfig`) — the single source of truth for parameter validation (project name, group id, artifact id regexes) and for every derived value used in templates (`base_package`, `package_path`, `app_class_name`). `template_context()` is what the renderer receives — if a template needs a new variable, add it here.
3. **`core/renderer.py`** (`resolve_tree` / `render_tree`) — a custom Jinja2 tree renderer. Both file/directory **names** and file **contents** are templated (e.g. `templates/base-layered/src/main/java/{{ package_path }}/{{ app_class_name }}Application.java`). `resolve_tree` computes the output path list without writing (used for the preview); `render_tree` does the actual write and raises `TargetExistsError` if the target directory exists.
4. **`core/tree_preview.py`** — renders the resolved path list as a box-drawing tree and asks `[y/N]` before anything is written.
5. **`core/validator.py`** — post-generation checks: `check_structure` (expected files present) then `run_compile` (real `mvn compile` subprocess, 300s timeout). Both return a `ValidationResult`.
6. **`core/progress.py`** — trivial `[n/total]` step printer used between stages.

`cli.py` wires these together and owns `EXPECTED_STRUCTURAL_PATHS` (what the structural check verifies) and `TEMPLATE_DIR` (currently the single `templates/base-layered` template — no template-selection concept yet). On any write or validation failure, it offers to delete the partially-generated folder; it never merges or overwrites an existing target directory.

### The template itself

`templates/base-layered/` is a full Spring Boot project, not fragments — Java 21, Spring Boot 4, Liquibase migrations, docker-compose for local Postgres, and one example entity (`Example`) wired end-to-end through `controller/service/repository/entity` as a reference for full CRUD. Jinja2 placeholders appear in both paths (`{{ package_path }}`, `{{ app_class_name }}`) and file contents. Because `jinja2.StrictUndefined` is used, every variable referenced in the template must exist in `ForgeConfig.template_context()`.

### Testing approach

`tests/test_generation.py` is an end-to-end test: it builds a real `ForgeConfig`, renders the actual template into a tmp dir, and runs both validator checks including a real `mvn compile`. Other test files unit-test each `core/` module in isolation. When changing `config_schema.py`'s derived properties or the template's variable usage, both layers need to stay in sync — the strict Jinja2 undefined check will fail fast if they don't.

## Design docs

The original design spec and implementation plan live under `docs/superpowers/specs/` and `docs/superpowers/plans/`.
