# Multi-Template Support (Forge + Forge Web) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `--template` flag to both `forge` and `forge-web`, backed by a shared-base-plus-exclude-glob template mechanism, plus one new `minimal` template per package.

**Architecture:** Each package's single template directory is split into `templates/_shared/` (the full current file tree, unchanged) and per-template `templates/<name>/manifest.py` files exporting an `EXCLUDES` glob tuple. A new `core/templates.py` module discovers the registry and filters expected-path lists; `core/renderer.py` gains an `excluded` parameter. `cli.py` replaces the hardcoded `TEMPLATE_DIR` with the registry and a `--template` flag/wizard prompt. A handful of shared files (`pom.xml`, `application.yml`, `package.json`, `App.tsx`) get Jinja2 conditionals keyed off new `template_context()` booleans (`use_liquibase`, `include_data_fetching`) for content that must differ by template even though the file itself is shared.

**Tech Stack:** Python (Typer, Pydantic, Jinja2, pytest) for the generators; the generated backend template is Java/Spring Boot/Maven, the generated frontend template is Vite/React/TypeScript.

**Spec:** `docs/superpowers/specs/2026-08-16-multi-template-support-design.md`

## Global Constraints

- Exclude patterns are matched with `fnmatch` semantics against the POSIX-style, **unrendered** template-source relative path (renderer) or the **rendered** expected-path (structural-path filtering, pattern itself rendered through the same context first). `fnmatch`'s `*` already matches across `/` since it has no path awareness — write patterns with a single `*`, not `**`.
- `--template` defaults to `None` on both CLIs; the wizard prompts for it (like every other currently-prompted field) when omitted, validating against the discovered registry. This is additive — no existing flag's behavior changes.
- Backend default/legacy template is named `base-layered`; frontend's is named `base`. Both keep their exact current file set and content (empty `EXCLUDES`).
- `minimal` (both packages) only *excludes* files/content — it never adds or overrides anything the other template doesn't already have. Additive overlays are explicitly out of scope for this plan.
- Keep backend and frontend changes in separate commits (this repo's existing convention — see `CONTRIBUTING.md`).
- Every new/changed Jinja2-templated file must only reference context keys that exist in the corresponding `template_context()` (`jinja2.StrictUndefined` is in effect — an unregistered variable fails the render immediately).

---

## Backend (`forge`)

### Task 1: Renderer supports an `excluded` glob parameter

**Files:**
- Modify: `backend/core/renderer.py`
- Test: `backend/tests/test_renderer.py`

**Interfaces:**
- Produces: `resolve_tree(template_dir: Path, context: dict, excluded: tuple[str, ...] = ()) -> list[Path]`, `render_tree(template_dir: Path, target_dir: Path, context: dict, excluded: tuple[str, ...] = ()) -> None` — both backward-compatible (existing 2-positional-arg call sites keep working since `excluded` defaults to `()`).

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_renderer.py`:
- `test_resolve_tree_drops_paths_matching_excluded_pattern`: build a template dir with `keep.txt` and `drop/nested.txt`; call `resolve_tree(template_dir, {}, excluded=("drop/*",))`; assert result is `[Path("keep.txt")]`.
- `test_render_tree_does_not_write_excluded_files`: same fixture; call `render_tree(template_dir, target_dir, {}, excluded=("drop/*",))`; assert `(target_dir / "keep.txt").exists()` and not `(target_dir / "drop").exists()`.
- `test_excluded_pattern_matches_against_unrendered_path`: template dir has `{{ package_path }}/example/Foo.java`; call with `excluded=("{{ package_path }}/example/*",)` and a context providing `package_path`; assert the file is dropped (proves matching happens on the raw, pre-render path, not the rendered one).

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\pytest backend/tests/test_renderer.py -v`
Expected: the three new tests FAIL with `TypeError: resolve_tree() got an unexpected keyword argument 'excluded'`.

- [ ] **Step 3: Implement**

In `backend/core/renderer.py`, add `import fnmatch` and a private helper:

```python
def _is_excluded(rel_path: Path, excluded: tuple[str, ...]) -> bool:
    rel_posix = rel_path.as_posix()
    return any(fnmatch.fnmatch(rel_posix, pattern) for pattern in excluded)
```

Thread `excluded: tuple[str, ...] = ()` through `_iter_rendered_files`, `resolve_tree`, and `render_tree`'s signatures. In `_iter_rendered_files`, immediately after computing `path.relative_to(template_dir)` (before the `rel_parts` rendering loop), skip the file (`continue`) if `_is_excluded(path.relative_to(template_dir), excluded)`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv\Scripts\pytest backend/tests/test_renderer.py -v`
Expected: PASS (all tests, old and new).

- [ ] **Step 5: Commit**

```bash
git add backend/core/renderer.py backend/tests/test_renderer.py
git commit -m "feat(backend): support excluded glob patterns in the tree renderer"
```

---

### Task 2: Restructure backend templates into `_shared` + per-template manifests

**Files:**
- Move: `backend/templates/base-layered/**` → `backend/templates/_shared/**` (git mv, content unchanged)
- Create: `backend/templates/base-layered/manifest.py`
- Create: `backend/templates/minimal/manifest.py`
- Test: `backend/tests/test_template_manifests.py`

**Interfaces:**
- Produces: each `templates/<name>/manifest.py` exports `EXCLUDES: tuple[str, ...]`, loaded by Task 3's `core/templates.py`.

- [ ] **Step 1: Move the existing template**

```bash
git mv backend/templates/base-layered backend/templates/_shared
```

- [ ] **Step 2: Create `backend/templates/base-layered/manifest.py`**

```python
"""Exclude-glob manifest for the base-layered template — the full reference project."""

EXCLUDES: tuple[str, ...] = ()
```

- [ ] **Step 3: Create `backend/templates/minimal/manifest.py`**

```python
"""Exclude-glob manifest for the minimal template — drops Liquibase migrations and the
Testcontainers-backed repository test; keeps the example CRUD slice and MapStruct."""

EXCLUDES: tuple[str, ...] = (
    "src/main/resources/db/changelog/*",
    "src/test/java/{{ package_path }}/example/repository/ExampleRepositoryTest.java",
)
```

- [ ] **Step 4: Write the failing manifest-sanity test**

Add `backend/tests/test_template_manifests.py`:

```python
from pathlib import Path

import pytest

from core.templates import discover_templates

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def test_every_template_directory_has_a_manifest():
    template_dirs = {p.name for p in TEMPLATES_DIR.iterdir() if p.is_dir() and p.name != "_shared"}
    assert set(discover_templates()) == template_dirs


@pytest.mark.parametrize("name", ["base-layered", "minimal"])
def test_each_exclude_pattern_matches_at_least_one_shared_file(name):
    excludes = discover_templates()[name]
    shared_files = [str(p.relative_to(TEMPLATES_DIR / "_shared").as_posix()) for p in (TEMPLATES_DIR / "_shared").rglob("*") if p.is_file()]
    import fnmatch
    for pattern in excludes:
        assert any(fnmatch.fnmatch(f, pattern) for f in shared_files), f"pattern {pattern!r} matched nothing"
```

- [ ] **Step 5: Run test to verify it fails**

Run: `.venv\Scripts\pytest backend/tests/test_template_manifests.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.templates'` (Task 3 creates it — this is expected red; proceed to Task 3 before this can go green).

- [ ] **Step 6: Commit the move and manifests (test stays red until Task 3)**

```bash
git add backend/templates backend/tests/test_template_manifests.py
git commit -m "feat(backend): split templates into _shared plus base-layered/minimal manifests"
```

---

### Task 3: `core/templates.py` registry discovery + expected-path filtering

**Files:**
- Create: `backend/core/templates.py`
- Test: `backend/tests/test_template_manifests.py` (extend from Task 2)

**Interfaces:**
- Consumes: `backend/templates/<name>/manifest.py` files (Task 2), each with `EXCLUDES: tuple[str, ...]`.
- Produces: `TEMPLATES_DIR: Path`, `SHARED_DIR: Path`, `discover_templates() -> dict[str, tuple[str, ...]]`, `filter_excluded_paths(paths: list[Path], excluded: tuple[str, ...], context: dict) -> list[Path]` — used by `cli.py` (Task 4) to filter `EXPECTED_STRUCTURAL_PATHS`.

- [ ] **Step 1: Implement `core/templates.py`**

```python
"""Template registry: discovers templates/<name>/manifest.py files and filters expected-path lists."""

import fnmatch
import importlib.util
from pathlib import Path

import jinja2

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
SHARED_DIR = TEMPLATES_DIR / "_shared"

_ENV = jinja2.Environment(undefined=jinja2.StrictUndefined)


def _load_excludes(manifest_path: Path) -> tuple[str, ...]:
    spec = importlib.util.spec_from_file_location(f"manifest_{manifest_path.parent.name}", manifest_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return tuple(module.EXCLUDES)


def discover_templates() -> dict[str, tuple[str, ...]]:
    """Return {template_name: excludes} for every templates/<name>/manifest.py (excluding _shared)."""
    return {
        manifest_path.parent.name: _load_excludes(manifest_path)
        for manifest_path in sorted(TEMPLATES_DIR.glob("*/manifest.py"))
    }


def filter_excluded_paths(paths: list[Path], excluded: tuple[str, ...], context: dict) -> list[Path]:
    """Drop any path matching a rendered exclude pattern; for filtering expected-structural-path lists."""
    rendered_patterns = [
        _ENV.from_string(pattern).render(**context) if ("{{" in pattern or "{%" in pattern) else pattern
        for pattern in excluded
    ]
    return [
        path for path in paths
        if not any(fnmatch.fnmatch(path.as_posix(), pat) for pat in rendered_patterns)
    ]
```

- [ ] **Step 2: Run the Task 2 manifest-sanity tests**

Run: `.venv\Scripts\pytest backend/tests/test_template_manifests.py -v`
Expected: PASS.

- [ ] **Step 3: Write and run a failing/passing test for `filter_excluded_paths`**

Add to `backend/tests/test_template_manifests.py`:

```python
def test_filter_excluded_paths_renders_pattern_placeholders_before_matching():
    from core.templates import filter_excluded_paths
    paths = [Path("src/test/java/com/example/demo/example/repository/ExampleRepositoryTest.java"), Path("keep.txt")]
    excluded = ("src/test/java/{{ package_path }}/example/repository/ExampleRepositoryTest.java",)
    result = filter_excluded_paths(paths, excluded, {"package_path": "com/example/demo"})
    assert result == [Path("keep.txt")]
```

Run: `.venv\Scripts\pytest backend/tests/test_template_manifests.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/core/templates.py backend/tests/test_template_manifests.py
git commit -m "feat(backend): add template registry discovery and expected-path filtering"
```

---

### Task 4: `use_liquibase` conditional content in `pom.xml` and `application.yml`

**Files:**
- Modify: `backend/core/config_schema.py`
- Modify: `backend/templates/_shared/pom.xml`
- Modify: `backend/templates/_shared/src/main/resources/application.yml`
- Test: `backend/tests/test_config_schema.py`

**Interfaces:**
- Consumes: `core.templates.discover_templates()` (Task 3) for `template` field validation.
- Produces: `ForgeConfig.template: str` field; `template_context()` gains `"template"` and `"use_liquibase"` keys.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_config_schema.py`:

```python
def test_template_context_includes_use_liquibase_flag_true_for_base_layered():
    config = ForgeConfig(project_name="demo", target_path=Path("."), group_id="com.example", artifact_id="demo", template="base-layered")
    assert config.template_context()["use_liquibase"] is True


def test_template_context_includes_use_liquibase_flag_false_for_minimal():
    config = ForgeConfig(project_name="demo", target_path=Path("."), group_id="com.example", artifact_id="demo", template="minimal")
    assert config.template_context()["use_liquibase"] is False


def test_unknown_template_raises_validation_error():
    with pytest.raises(ValidationError):
        ForgeConfig(project_name="demo", target_path=Path("."), group_id="com.example", artifact_id="demo", template="nonexistent")
```

(Add `from pydantic import ValidationError` to the test file's imports if not already present.)

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest backend/tests/test_config_schema.py -v`
Expected: FAIL — `ForgeConfig` has no `template` field yet.

- [ ] **Step 3: Implement in `backend/core/config_schema.py`**

Add near the top: `from core.templates import discover_templates` and `VALID_TEMPLATES = frozenset(discover_templates())`.

Add a `template: str` field to `ForgeConfig`, plus:

```python
@field_validator("template")
@classmethod
def _check_template(cls, v: str) -> str:
    if v not in VALID_TEMPLATES:
        raise ValueError(f"must be one of: {', '.join(sorted(VALID_TEMPLATES))}")
    return v
```

Add a `use_liquibase` property: `return self.template != "minimal"`. Add both `"template": self.template` and `"use_liquibase": self.use_liquibase` to the dict returned by `template_context()`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest backend/tests/test_config_schema.py -v`
Expected: PASS.

- [ ] **Step 5: Make `pom.xml` and `application.yml` content-conditional**

In `backend/templates/_shared/pom.xml`:
- Wrap the `<dependencyManagement>` block (the `testcontainers-bom` import) in `{% if use_liquibase %}` / `{% endif %}`.
- Wrap the `liquibase-core` and `spring-boot-liquibase` `<dependency>` entries in the same conditional.
- Wrap the two `org.testcontainers` test-scoped `<dependency>` entries (`junit-jupiter`, `postgresql`) in the same conditional.

In `backend/templates/_shared/src/main/resources/application.yml`:
- Wrap the `liquibase:` block (2 lines) in `{% if use_liquibase %}` / `{% endif %}`.
- Change `ddl-auto: none` to `ddl-auto: {% if use_liquibase %}none{% else %}update{% endif %}`.

- [ ] **Step 6: Commit**

```bash
git add backend/core/config_schema.py backend/tests/test_config_schema.py backend/templates/_shared/pom.xml backend/templates/_shared/src/main/resources/application.yml
git commit -m "feat(backend): make Liquibase/Testcontainers content conditional on use_liquibase"
```

---

### Task 5: `cli.py` wires the registry, `--template` flag, and wizard prompt

**Files:**
- Modify: `backend/cli.py`
- Modify: `backend/core/wizard.py`
- Test: `backend/tests/test_cli.py`, `backend/tests/test_wizard.py`

**Interfaces:**
- Consumes: `core.templates.{discover_templates, filter_excluded_paths, SHARED_DIR}` (Task 3), `ForgeConfig.template`/`use_liquibase` (Task 4).
- Produces: `forge new --template <name>`; `collect_params` prompts for `template` when omitted.

- [ ] **Step 1: Write the failing wizard test**

Add to `backend/tests/test_wizard.py` (mirroring the existing prompt tests' style — read the file first to match its fixture pattern): a test that calls `collect_params` with `template` omitted from overrides and a fake `prompt_fn` sequence supplying `"minimal"` for the template prompt; assert `config.template == "minimal"`. Add a second test where the fake prompt returns an invalid template name once, then `"base-layered"`; assert it reprompts (mirrors the existing reprompt-on-invalid-input tests for `group_id`/`artifact_id`).

- [ ] **Step 2: Run to verify it fails**

Run: `.venv\Scripts\pytest backend/tests/test_wizard.py -v`
Expected: FAIL (no template prompt exists yet).

- [ ] **Step 3: Implement the wizard prompt**

In `backend/core/wizard.py`, add `from core.templates import discover_templates` and `from core.config_schema import validate_template` (new function, see Step 4). Add a `("template", "Template (base-layered/minimal)", validate_template)` entry to `FIELD_PROMPTS`.

In `backend/core/config_schema.py`, extract the field-validator body from Task 4 into a standalone module-level function `validate_template(value: str) -> str` (same logic), and have the `ForgeConfig` field validator call it — this mirrors the existing `validate_project_name`/`validate_group_id`/`validate_artifact_id` pattern the wizard already imports from.

- [ ] **Step 4: Run wizard test to verify it passes**

Run: `.venv\Scripts\pytest backend/tests/test_wizard.py -v`
Expected: PASS.

- [ ] **Step 5: Write the failing CLI test**

Add to `backend/tests/test_cli.py` (match its existing invocation style via Typer's `CliRunner`): a test asserting `forge new --template minimal ...` (with all other required flags) renders successfully and the target project does NOT contain `src/main/resources/db/changelog`. A second test asserting `--template does-not-exist` exits non-zero with an "unknown template" message.

- [ ] **Step 6: Run to verify it fails**

Run: `.venv\Scripts\pytest backend/tests/test_cli.py -v`
Expected: FAIL — `cli.py` doesn't accept `--template` yet.

- [ ] **Step 7: Implement in `backend/cli.py`**

Replace the `TEMPLATE_DIR = Path(...) / "templates" / "base-layered"` constant with:

```python
from core.templates import SHARED_DIR, discover_templates, filter_excluded_paths

TEMPLATES = discover_templates()
```

Add `template: str = typer.Option(None, "--template")` to `new()`'s signature; add `"template": template` to the `overrides` dict passed to `collect_params`.

After `config = collect_params(overrides)`, add:

```python
if config.template not in TEMPLATES:
    typer.echo(f"Error: unknown template '{config.template}'. Available: {', '.join(sorted(TEMPLATES))}")
    raise typer.Exit(code=1)
excluded = TEMPLATES[config.template]
```

Replace the `if not TEMPLATE_DIR.is_dir()` check and every subsequent `TEMPLATE_DIR` reference with `SHARED_DIR`, and pass `excluded=excluded` to both `resolve_tree(...)` and `render_tree(...)`.

Replace the structural-check call:

```python
static_paths = filter_excluded_paths(EXPECTED_STRUCTURAL_PATHS, excluded, context)
dynamic_paths = filter_excluded_paths(expected_structural_paths(context), excluded, context)
structural = check_structure(config.target_dir, static_paths + dynamic_paths)
```

- [ ] **Step 8: Run CLI tests to verify they pass**

Run: `.venv\Scripts\pytest backend/tests/test_cli.py -v`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add backend/cli.py backend/core/wizard.py backend/core/config_schema.py backend/tests/test_cli.py backend/tests/test_wizard.py
git commit -m "feat(backend): add --template flag, wizard prompt, and per-template structural filtering"
```

---

### Task 6: Parametrize backend end-to-end generation test over both templates

**Files:**
- Modify: `backend/tests/test_generation.py`

**Interfaces:**
- Consumes: `core.templates.{SHARED_DIR, discover_templates, filter_excluded_paths}`, `cli.EXPECTED_STRUCTURAL_PATHS`/`expected_structural_paths`.

- [ ] **Step 1: Rewrite the test to parametrize over template names**

Replace the single hardcoded-`TEMPLATE_DIR` test with:

```python
import pytest

from cli import EXPECTED_STRUCTURAL_PATHS, expected_structural_paths
from core.config_schema import ForgeConfig
from core.renderer import render_tree
from core.templates import SHARED_DIR, discover_templates, filter_excluded_paths
from core.validator import check_structure, run_compile


@pytest.mark.parametrize("template_name", sorted(discover_templates()))
def test_generated_project_passes_structural_and_compile_checks(tmp_path, template_name):
    config = ForgeConfig(
        project_name="demo-service",
        target_path=tmp_path / template_name,
        group_id="com.example",
        artifact_id="demo-service",
        template=template_name,
    )
    excluded = discover_templates()[template_name]
    context = config.template_context()

    render_tree(SHARED_DIR, config.target_dir, context, excluded=excluded)

    static_paths = filter_excluded_paths(EXPECTED_STRUCTURAL_PATHS, excluded, context)
    dynamic_paths = filter_excluded_paths(expected_structural_paths(context), excluded, context)
    structural = check_structure(config.target_dir, static_paths + dynamic_paths)
    assert structural.passed, structural.details

    compile_result = run_compile(config.target_dir)
    assert compile_result.passed, compile_result.details

    if template_name == "minimal":
        assert not (config.target_dir / "src/main/resources/db/changelog").exists()
```

- [ ] **Step 2: Run tests**

Run: `.venv\Scripts\pytest backend/tests/test_generation.py -v`
Expected: PASS for both `base-layered` and `minimal` (requires `mvn` on PATH; this is the same requirement the existing test already has). This is the first real end-to-end proof that `minimal` actually compiles.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_generation.py
git commit -m "test(backend): parametrize end-to-end generation test over base-layered and minimal"
```

---

## Frontend (`forge-web`)

### Task 7: Renderer supports an `excluded` glob parameter (frontend)

**Files:**
- Modify: `frontend/forge_web/core/renderer.py`
- Test: `frontend/tests/test_renderer.py`

Same change as Task 1, applied to the frontend package's copy of the renderer (the two packages share no code — see `CLAUDE.md`).

- [ ] **Step 1: Write the failing tests**

Read `frontend/tests/test_renderer.py` first to match its existing fixture style, then add the same three tests as Task 1 (`test_resolve_tree_drops_paths_matching_excluded_pattern`, `test_render_tree_does_not_write_excluded_files`, `test_excluded_pattern_matches_against_unrendered_path`) against `frontend/forge_web/core/renderer.py`'s `resolve_tree`/`render_tree`.

- [ ] **Step 2: Run to verify failure**

Run: `.venv\Scripts\pytest frontend/tests/test_renderer.py -v`
Expected: FAIL with `TypeError: unexpected keyword argument 'excluded'`.

- [ ] **Step 3: Implement**

Apply the identical `_is_excluded` helper and `excluded` threading from Task 1, Step 3, to `frontend/forge_web/core/renderer.py`.

- [ ] **Step 4: Run to verify pass**

Run: `.venv\Scripts\pytest frontend/tests/test_renderer.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/forge_web/core/renderer.py frontend/tests/test_renderer.py
git commit -m "feat(frontend): support excluded glob patterns in the tree renderer"
```

---

### Task 8: Restructure frontend templates into `_shared` + per-template manifests

**Files:**
- Move: `frontend/forge_web/templates/base/**` → `frontend/forge_web/templates/_shared/**`
- Create: `frontend/forge_web/templates/base/manifest.py`
- Create: `frontend/forge_web/templates/minimal/manifest.py`
- Test: `frontend/tests/test_template_manifests.py`

- [ ] **Step 1: Move the existing template**

```bash
git mv frontend/forge_web/templates/base frontend/forge_web/templates/_shared
```

- [ ] **Step 2: Create `frontend/forge_web/templates/base/manifest.py`**

```python
"""Exclude-glob manifest for the base template — the full reference project."""

EXCLUDES: tuple[str, ...] = ()
```

- [ ] **Step 3: Create `frontend/forge_web/templates/minimal/manifest.py`**

```python
"""Exclude-glob manifest for the minimal template — drops the CRUD dashboard, its form,
the data hooks, and the API client; keeps the full Shadcn set and the component showcase."""

EXCLUDES: tuple[str, ...] = (
    "src/pages/dashboard/dashboard-page.tsx",
    "src/pages/dashboard/item-form.tsx",
    "src/lib/hooks/use-items.ts",
    "src/lib/api-client/*",
)
```

- [ ] **Step 4: Write the failing manifest-sanity test**

Add `frontend/tests/test_template_manifests.py`, mirroring backend Task 2 Step 4's content exactly but pointed at `frontend/forge_web/templates/` and importing from `forge_web.core.templates` (created in Task 9).

- [ ] **Step 5: Run test to verify it fails**

Run: `.venv\Scripts\pytest frontend/tests/test_template_manifests.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'forge_web.core.templates'` (expected red — Task 9 creates it).

- [ ] **Step 6: Commit**

```bash
git add frontend/forge_web/templates frontend/tests/test_template_manifests.py
git commit -m "feat(frontend): split templates into _shared plus base/minimal manifests"
```

---

### Task 9: `forge_web/core/templates.py` registry discovery + expected-path filtering

**Files:**
- Create: `frontend/forge_web/core/templates.py`
- Test: `frontend/tests/test_template_manifests.py` (extend from Task 8)

Identical structure to backend Task 3, with `TEMPLATES_DIR = Path(__file__).parent.parent / "templates"` resolving to `frontend/forge_web/templates` and imports namespaced under `forge_web.core.templates` (per this package's namespacing rule in `CLAUDE.md`).

- [ ] **Step 1: Implement `frontend/forge_web/core/templates.py`**

Same content as backend Task 3 Step 1's `core/templates.py`, verbatim (no frontend-specific logic needed — copy `discover_templates`/`filter_excluded_paths`/`_load_excludes`/`TEMPLATES_DIR`/`SHARED_DIR`/`_ENV`).

- [ ] **Step 2: Run the Task 8 manifest-sanity tests**

Run: `.venv\Scripts\pytest frontend/tests/test_template_manifests.py -v`
Expected: PASS.

- [ ] **Step 3: Add and run the `filter_excluded_paths` unit test**

Mirror backend Task 3 Step 3's test, adapted to a frontend-shaped path/pattern (e.g. `Path("src/lib/api-client/index.ts")` excluded by `"src/lib/api-client/*"`, with an empty context since no placeholder rendering is needed for this pattern).

Run: `.venv\Scripts\pytest frontend/tests/test_template_manifests.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/forge_web/core/templates.py frontend/tests/test_template_manifests.py
git commit -m "feat(frontend): add template registry discovery and expected-path filtering"
```

---

### Task 10: `include_data_fetching` conditional content in `package.json` and `App.tsx`

**Files:**
- Modify: `frontend/forge_web/core/config_schema.py`
- Modify: `frontend/forge_web/templates/_shared/package.json`
- Modify: `frontend/forge_web/templates/_shared/src/App.tsx`
- Test: `frontend/tests/test_config_schema.py`

**Interfaces:**
- Consumes: `forge_web.core.templates.discover_templates()` (Task 9).
- Produces: `ForgeWebConfig.template: str` field; `template_context()` gains `"template"` and `"include_data_fetching"` keys.

- [ ] **Step 1: Write the failing test**

Mirror backend Task 4 Step 1's three tests, adapted: `include_data_fetching` true for `template="base"`, false for `template="minimal"`, and an unknown-template `ValidationError`.

- [ ] **Step 2: Run to verify failure**

Run: `.venv\Scripts\pytest frontend/tests/test_config_schema.py -v`
Expected: FAIL — no `template` field yet.

- [ ] **Step 3: Implement in `frontend/forge_web/core/config_schema.py`**

Same pattern as backend Task 4 Step 3: `from forge_web.core.templates import discover_templates`, `VALID_TEMPLATES = frozenset(discover_templates())`, a `template: str` field + validator on `ForgeWebConfig`, an `include_data_fetching` property (`self.template != "minimal"`), and both keys added to `template_context()`.

- [ ] **Step 4: Run to verify pass**

Run: `.venv\Scripts\pytest frontend/tests/test_config_schema.py -v`
Expected: PASS.

- [ ] **Step 5: Make `package.json` content-conditional**

In `frontend/forge_web/templates/_shared/package.json`'s `dependencies` object, reorder so the three conditional entries are grouped together, each keeping its own trailing comma, immediately followed by at least one always-present dependency (so the object never ends on an excluded line):

```json
  "dependencies": {
{% if include_data_fetching %}
    "@hookform/resolvers": "^3.9.0",
    "@tanstack/react-query": "^5.59.0",
    "zod": "^3.23.8",
{% endif %}
    "@radix-ui/react-alert-dialog": "^1.1.2",
    "@radix-ui/react-avatar": "^1.1.1",
    "@radix-ui/react-dialog": "^1.1.2",
    "@radix-ui/react-dropdown-menu": "^2.1.2",
    "@radix-ui/react-label": "^2.1.0",
    "@radix-ui/react-select": "^2.1.2",
    "@radix-ui/react-slot": "^1.1.0",
    "@radix-ui/react-tabs": "^1.1.1",
    "@tanstack/react-table": "^8.20.5",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.1.1",
    "lucide-react": "^0.451.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-hook-form": "^7.53.0",
    "react-router-dom": "^6.26.2",
    "sonner": "^1.5.0",
    "tailwind-merge": "^2.5.3"
  },
```

(`react-hook-form` and `@tanstack/react-table` stay unconditional per the spec correction — the retained showcase page uses both.)

- [ ] **Step 6: Make `App.tsx` content-conditional**

In `frontend/forge_web/templates/_shared/src/App.tsx`:
- Wrap the `import { QueryClient, QueryClientProvider } from "@tanstack/react-query";` line and the `import DashboardPage from "@/pages/dashboard/dashboard-page";` line each in `{% if include_data_fetching %}` / `{% endif %}`.
- Wrap `const queryClient = new QueryClient();` in the same conditional.
- Wrap the `/dashboard` route object (lines 26-34 of the current file) in the same conditional.
- Wrap the `<QueryClientProvider client={queryClient}>` opening tag and its matching `</QueryClientProvider>` closing tag in the same conditional (when `include_data_fetching` is false, `<RouterProvider router={router} />` and `<Toaster />` render as direct children of the component's return, not wrapped).

- [ ] **Step 7: Commit**

```bash
git add frontend/forge_web/core/config_schema.py frontend/tests/test_config_schema.py frontend/forge_web/templates/_shared/package.json frontend/forge_web/templates/_shared/src/App.tsx
git commit -m "feat(frontend): make data-fetching dependencies and App.tsx wiring conditional on include_data_fetching"
```

---

### Task 11: `cli.py` wires the registry, `--template` flag, and wizard prompt (frontend)

**Files:**
- Modify: `frontend/forge_web/cli.py`
- Modify: `frontend/forge_web/core/wizard.py`
- Test: `frontend/tests/test_cli.py`, `frontend/tests/test_wizard.py`

Same structure as backend Task 5, adapted to this package's imports and defaults.

- [ ] **Step 1: Write the failing wizard test**

Mirror backend Task 5 Step 1, adapted to `frontend/tests/test_wizard.py`'s existing fixture style and `forge_web.core.wizard.collect_params`.

- [ ] **Step 2: Run to verify failure**

Run: `.venv\Scripts\pytest frontend/tests/test_wizard.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement the wizard prompt**

In `frontend/forge_web/core/wizard.py`: add a `validate_template` import from `forge_web.core.config_schema` (extracted the same way as backend Task 5 Step 3) and a `("template", "Template (base/minimal)", validate_template)` entry to `FIELD_PROMPTS`.

- [ ] **Step 4: Run to verify pass**

Run: `.venv\Scripts\pytest frontend/tests/test_wizard.py -v`
Expected: PASS.

- [ ] **Step 5: Write the failing CLI test**

Mirror backend Task 5 Step 5, adapted to `forge-web new --template minimal` and asserting the target project does NOT contain `src/lib/api-client`.

- [ ] **Step 6: Run to verify failure**

Run: `.venv\Scripts\pytest frontend/tests/test_cli.py -v`
Expected: FAIL.

- [ ] **Step 7: Implement in `frontend/forge_web/cli.py`**

Same transformation as backend Task 5 Step 7: replace `TEMPLATE_DIR` with `SHARED_DIR` + `TEMPLATES = discover_templates()` (imported from `forge_web.core.templates`), add the `--template` option and unknown-template guard, thread `excluded` through `resolve_tree`/`render_tree`, and replace the structural-check call with `filter_excluded_paths(EXPECTED_STRUCTURAL_PATHS, excluded, context)` (this package has no separate `expected_structural_paths()` function — `EXPECTED_STRUCTURAL_PATHS` alone is the full list).

- [ ] **Step 8: Run to verify pass**

Run: `.venv\Scripts\pytest frontend/tests/test_cli.py -v`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add frontend/forge_web/cli.py frontend/forge_web/core/wizard.py frontend/forge_web/core/config_schema.py frontend/tests/test_cli.py frontend/tests/test_wizard.py
git commit -m "feat(frontend): add --template flag, wizard prompt, and per-template structural filtering"
```

---

### Task 12: Parametrize frontend end-to-end generation test over both templates

**Files:**
- Modify: `frontend/tests/test_generation.py`

- [ ] **Step 1: Rewrite the test to parametrize over template names**

Read the existing `frontend/tests/test_generation.py` first to match its exact assertions (`npm install && npm run build`, `npx tsc --noEmit`, design-token check), then apply the same parametrization shape as backend Task 6 Step 1: loop `@pytest.mark.parametrize("template_name", sorted(discover_templates()))`, build a `ForgeWebConfig(..., template=template_name)`, render via `SHARED_DIR` + the template's `excluded`, run `check_structure` with `filter_excluded_paths(EXPECTED_STRUCTURAL_PATHS, excluded, context)`, then the existing `run_build`/`run_typecheck`/`check_no_hardcoded_design_values`/`check_no_spacing_scale_width_collisions` calls unchanged. Add a `minimal`-only assertion that `config.target_dir / "src/lib/api-client"` does not exist.

- [ ] **Step 2: Run tests**

Run: `.venv\Scripts\pytest frontend/tests/test_generation.py -v`
Expected: PASS for both `base` and `minimal` (requires `npm`/`npx` on PATH).

- [ ] **Step 3: Commit**

```bash
git add frontend/tests/test_generation.py
git commit -m "test(frontend): parametrize end-to-end generation test over base and minimal"
```

---

## Documentation

### Task 13: Update docs for both packages

**Files:**
- Modify: `CLAUDE.md` (repo root)
- Modify: `backend/README.md`, `backend/QUICK_REFERENCE.md`
- Modify: `frontend/README.md`, `frontend/QUICK_REFERENCE.md`
- Modify: `CONTRIBUTING.md`
- Modify: `backend/CHANGELOG.md`, `frontend/CHANGELOG.md`

- [ ] **Step 1: Update `CLAUDE.md`**

In both packages' Architecture sections, replace the sentence describing a single hardcoded `TEMPLATE_DIR`/"no template-selection concept yet" with a description of: `templates/_shared/` + per-template `manifest.py` exclude lists, `core/templates.py`'s `discover_templates()`/`filter_excluded_paths()`, and the `--template` flag. Name both registered templates per package (`base-layered`/`minimal`; `base`/`minimal`).

- [ ] **Step 2: Update `backend/README.md` and `backend/QUICK_REFERENCE.md`**

Document `--template {base-layered,minimal}`, and add the include/exclude table from the spec's "Backend: `base-layered` vs `minimal`" section.

- [ ] **Step 3: Update `frontend/README.md` and `frontend/QUICK_REFERENCE.md`**

Document `--template {base,minimal}`, and add the corrected include/exclude table from the spec's "Frontend: `base` vs `minimal`" section (including the `react-hook-form`/`@tanstack/react-table` staying-unconditional note).

- [ ] **Step 4: Update `CONTRIBUTING.md`**

Add a subsection under "Making changes" describing how to add a new template: create `templates/<name>/manifest.py` with an `EXCLUDES: tuple[str, ...]` tuple (glob patterns against the unrendered `_shared`-relative path); if the template needs shared-file *content* (not just presence) to differ, add a corresponding boolean to `template_context()` and wrap the relevant lines in a Jinja2 `{% if %}` block, following the `use_liquibase`/`include_data_fetching` examples.

- [ ] **Step 5: Update both `CHANGELOG.md` files' `[Unreleased]` sections**

Backend bullet: "Added `--template` flag (`base-layered`/`minimal`) and a `minimal` template that drops Liquibase migrations and Testcontainers-backed repository tests." Frontend bullet: "Added `--template` flag (`base`/`minimal`) and a `minimal` template that drops the sample CRUD dashboard, API client, and TanStack Query hooks while keeping the full Shadcn component set and showcase page."

- [ ] **Step 6: Commit**

```bash
git add CLAUDE.md CONTRIBUTING.md backend/README.md backend/QUICK_REFERENCE.md backend/CHANGELOG.md frontend/README.md frontend/QUICK_REFERENCE.md frontend/CHANGELOG.md
git commit -m "docs: document --template flag, minimal templates, and how to add a new template"
```
