# Forge Web Frontend Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Forge Web, a Python CLI (`frontend/`) that generates a working Vite + React + TypeScript + Shadcn/ui project — pre-themed from `docs/DESIGN.md`, with a sample dashboard, mock/real API client, and static pages — using the same wizard → preview → render → validate pipeline as `backend/` (Forge).

**Architecture:** A Typer CLI (`frontend/cli.py`) wires together small, independently-testable core modules — `config_schema` (Pydantic parameter model), `wizard` (interactive prompts), `renderer` (custom Jinja2 tree renderer applied to file/folder names and contents), `tree_preview` (text tree + y/n confirm), `progress` (status printer), and `validator` (structural + `npm install && npm run build` + `tsc --noEmit` + a hardcoded-design-value grep check) — operating on a single template tree at `frontend/templates/base/`. Each module is a standalone reimplementation matching `backend/core/`'s shape (no shared code, no shared dependency) so the two tools stay independently maintainable.

**Tech Stack:** Python 3.11+, Typer, Jinja2, Pydantic v2, pytest (generator). Generated projects: React 18, TypeScript, Vite, React Router, Tailwind v4, Shadcn/ui, TanStack Query, react-hook-form + zod, npm.

**Spec:** `docs/superpowers/specs/2026-08-14-frontend-generator-design.md`

## Global Constraints

- Framework: Vite SPA + React Router — no Next.js, no SSR (fixed decision, not a wizard parameter).
- Package manager: npm only — no pnpm/yarn support in v1.
- Exactly one template in v1: `base/` — no `--theme`/`--with-*` opt-in module system (noted as future work only).
- Every template file lives under `frontend/templates/base/...` and uses Jinja2 placeholders (`{{ project_name }}`, `{{ app_display_name }}`, `{{ api_base_url }}`) exactly where needed — `jinja2.StrictUndefined` fails the whole render if a variable is referenced that isn't in `ForgeWebConfig.template_context()` (mirrors `backend/core/config_schema.py`'s pattern). This plan's context has exactly three keys: `project_name`, `app_display_name`, `api_base_url`.
- If the target directory already exists, `render_tree` raises `TargetExistsError` before any writes — no merge, no `--force`, no overwrite prompt (identical contract to `backend/core/renderer.py`).
- On validation failure (structural, build, typecheck, or design-token check), prompt the user to keep or delete the generated folder — never decide automatically.
- Design tokens: every color/radius/spacing/typography/shadow value in `templates/base/src/**/*.tsx` and `**/*.css` must come from the CSS custom properties defined in `templates/base/src/styles/theme.css` (seeded from `docs/DESIGN.md`, an Airbnb-style design-token analysis — no YAML front matter; tokens are extracted from the doc's prose/tables) — never a hardcoded hex/rgb/px literal. Enforced by a grep-based check in `validator.py` and exercised by `test_generation.py`.
- Dark mode: **not implemented in v1.** `docs/DESIGN.md` states explicitly "Airbnb does not have a dark mode on the public web" — the generated theme is light-only, `styles/theme.css` has no dark-mode block, and there is no theme-toggle component.
- Elevation: the source design has exactly **one** shadow tier plus flat/scrim — not the 3-level system used in earlier drafts of this plan. `--shadow-1` is the only elevation custom property.
- Environment variables: `VITE_API_MODE` (`mock`|`real`), `VITE_API_BASE_URL`, `VITE_APP_NAME` are read from `import.meta.env` at runtime, never baked into the JS bundle at generation time. `.env.example` documents all three; `.env` is generated from the wizard's answers.
- Component set (v1, curated "broader default," per spec): button, input, label, card, table, dialog, dropdown-menu, sonner (toast), form, sidebar/nav, avatar, data-table, tabs, select, badge, skeleton, alert-dialog.
- Static pages (v1, explicit scope): 404, error boundary, loading skeleton, empty-state pattern.
- Out of scope (do not implement): Next.js/SSR, opt-in component modules (charts, auth pages, i18n), multi-entity/schema-driven page generation, named/multiple theme presets, pnpm/yarn support, unit tests inside the *generated* project (validation is build + typecheck + grep only, no vitest/jest scaffold).

---

## File Structure

```
frontend/
  cli.py                                        [Create — Task 7]
  core/
    __init__.py                                 [Create — Task 0]
    progress.py                                 [Create — Task 1]
    config_schema.py                            [Create — Task 2]
    renderer.py                                 [Create — Task 3]
    tree_preview.py                             [Create — Task 4]
    wizard.py                                   [Create — Task 5]
    validator.py                                [Create — Task 6]
  pyproject.toml                                [Create — Task 0]
  templates/
    base/
      package.json, tsconfig.json,
      tsconfig.node.json, vite.config.ts,
      index.html, .env.example, .gitignore      [Create — Task 8]
      src/
        main.tsx, App.tsx                       [Create — Task 8]
        lib/utils.ts (cn helper)                [Create — Task 8]
        styles/theme.css                        [Create — Task 9]
        components/ui/
          button.tsx, input.tsx, label.tsx,
          card.tsx, badge.tsx, skeleton.tsx      [Create — Task 10]
          table.tsx, data-table.tsx, tabs.tsx,
          select.tsx, dialog.tsx,
          alert-dialog.tsx, dropdown-menu.tsx,
          sonner.tsx, form.tsx, avatar.tsx       [Create — Task 11]
        components/common/
          app-shell.tsx, nav-sidebar.tsx           [Create — Task 12]
        lib/api-client/
          types.ts, api-client.ts,
          mock-client.ts, real-client.ts,
          index.ts                               [Create — Task 13]
        lib/hooks/use-items.ts                    [Create — Task 14]
        lib/utils/format.ts                        [Create — Task 15]
        pages/dashboard/
          dashboard-page.tsx, item-form.tsx        [Create — Task 16]
        pages/showcase/
          component-showcase-page.tsx               [Create — Task 16]
        pages/static/
          not-found-page.tsx, error-page.tsx,
          loading-page.tsx, empty-state.tsx         [Create — Task 17]
  tests/
    __init__.py                                   [Create — Task 0]
    test_sanity.py                                [Create — Task 0]
    test_config_schema.py                          [Create — Task 2]
    test_renderer.py                                [Create — Task 3]
    test_tree_preview.py                             [Create — Task 4]
    test_wizard.py                                    [Create — Task 5]
    test_validator.py                                  [Create — Task 6]
    test_cli.py                                         [Create — Task 7]
    test_generation.py                                   [Create — Task 18]
```

---

### Task 0: Environment & Project Setup

**Files:**
- Create: `frontend/pyproject.toml`
- Create: `frontend/core/__init__.py`
- Create: `frontend/tests/__init__.py`
- Create: `frontend/tests/test_sanity.py`

**Interfaces:**
- Consumes: nothing
- Produces: an installable `forge-web` package (modules `core.*`, `cli`) and a working pytest harness every later task's tests run under.

- [ ] **Step 1: Verify required tools are on PATH**

Run: `py --version`, `node --version`, `npm --version`. Expected: all print version info; Python 3.11+, Node 18+. Stop and report to the user if any is missing — do not proceed.

- [ ] **Step 2: Create `frontend/pyproject.toml`**

Mirror `backend/pyproject.toml`'s shape exactly, adjusted for this package: `name = "forge-web"`, same `dependencies` (`typer>=0.12`, `jinja2>=3.1`, `pydantic>=2.0`), same `[project.optional-dependencies] dev = ["pytest>=8.0"]`, `[project.scripts] forge-web = "cli:main"`, `[tool.setuptools] py-modules = ["cli"]`, `packages = ["core", "templates"]`, `include-package-data = true`, and a `[tool.setuptools.package-data] templates = ["**/*", "**/.*"]` section (needed once `templates/base/` exists, so dotfiles like `.env.example` and `.gitignore` are packaged). Same `[build-system]` block as `backend/pyproject.toml`.

- [ ] **Step 3: Create empty `frontend/core/__init__.py` and `frontend/tests/__init__.py`**

Both empty files (matches `backend/core/__init__.py`).

- [ ] **Step 4: Create `frontend/tests/test_sanity.py`**

Identical to `backend/tests/test_sanity.py`: one test, `test_pytest_runs`, asserting `True`.

- [ ] **Step 5: Install editable and run**

Run: `.venv\Scripts\pip install -e "./frontend[dev]"` then `.venv\Scripts\pytest frontend/tests -v`. Expected: 1 passed.

- [ ] **Step 6: Commit**

```bash
git add frontend/pyproject.toml frontend/core/__init__.py frontend/tests/__init__.py frontend/tests/test_sanity.py
git commit -m "chore: scaffold frontend/ Python package"
```

---

### Task 1: `core/progress.py`

**Files:**
- Create: `frontend/core/progress.py`

**Interfaces:**
- Produces: `step(message: str, index: int, total: int) -> None`

- [ ] **Step 1: Implement `progress.py`**

Identical to `backend/core/progress.py`: a single `step()` function printing `f"[{index}/{total}] {message}"`. No test file needed — this module has no branching logic (matches backend's approach of leaving it untested).

- [ ] **Step 2: Commit**

```bash
git add frontend/core/progress.py
git commit -m "feat: add progress step printer"
```

---

### Task 2: `core/config_schema.py` — `ForgeWebConfig`

**Files:**
- Create: `frontend/core/config_schema.py`
- Test: `frontend/tests/test_config_schema.py`

**Interfaces:**
- Consumes: nothing
- Produces: `ForgeWebConfig` (Pydantic `BaseModel`) with fields `project_name: str`, `target_path: Path`, `api_base_url: str`; property `target_dir -> Path`; property `app_display_name -> str`; method `template_context() -> dict` returning `{"project_name", "app_display_name", "api_base_url"}`. Also module-level `validate_project_name(value: str) -> str` and `PROJECT_NAME_RE`.

- [ ] **Step 1: Write failing tests for `validate_project_name`**

In `test_config_schema.py`, test: a valid name (`"my-dashboard"`) returns unchanged; an uppercase name, a name starting with a digit, and a name containing an underscore each raise `ValueError`. Reuse `backend/core/config_schema.py`'s `PROJECT_NAME_RE` pattern (`^[a-z][a-z0-9-]*$`) — frontend project names double as the npm `package.json` "name" field, which accepts this same lowercase-hyphen shape, so no separate npm-name validator is needed.

- [ ] **Step 2: Run to verify failure**

Run: `pytest frontend/tests/test_config_schema.py -v`. Expected: FAIL — `ModuleNotFoundError` / `ImportError` (module doesn't exist yet).

- [ ] **Step 3: Implement `validate_project_name` and `PROJECT_NAME_RE`**

Copy `backend/core/config_schema.py:8` (`PROJECT_NAME_RE`) and `validate_project_name` (lines 27-33) verbatim into `frontend/core/config_schema.py`.

- [ ] **Step 4: Run to verify pass**

Run: `pytest frontend/tests/test_config_schema.py -v`. Expected: PASS.

- [ ] **Step 5: Write failing tests for `ForgeWebConfig`**

Add tests: constructing `ForgeWebConfig(project_name="my-dashboard", target_path=Path("/tmp"), api_base_url="http://localhost:8080/api")` succeeds; `target_dir` equals `target_path / project_name`; `app_display_name` for `project_name="my-dashboard"` equals `"My Dashboard"` (title-cased, hyphens replaced with spaces); `template_context()` returns exactly `{"project_name": "my-dashboard", "app_display_name": "My Dashboard", "api_base_url": "http://localhost:8080/api"}`; an invalid `project_name` (e.g. `"1bad"`) raises a Pydantic `ValidationError` at construction.

- [ ] **Step 6: Run to verify failure**

Run: `pytest frontend/tests/test_config_schema.py -v`. Expected: FAIL — `ForgeWebConfig` not defined.

- [ ] **Step 7: Implement `ForgeWebConfig`**

```python
class ForgeWebConfig(BaseModel):
    project_name: str
    target_path: Path
    api_base_url: str

    @field_validator("project_name")
    @classmethod
    def _check_project_name(cls, v: str) -> str:
        return validate_project_name(v)

    @property
    def target_dir(self) -> Path:
        return self.target_path / self.project_name

    @property
    def app_display_name(self) -> str:
        return " ".join(part.capitalize() for part in self.project_name.split("-"))

    def template_context(self) -> dict:
        return {
            "project_name": self.project_name,
            "app_display_name": self.app_display_name,
            "api_base_url": self.api_base_url,
        }
```

`api_base_url` has no format validator — any non-empty string is accepted (matches the "no unnecessary validation" principle; a malformed URL only affects the generated `.env`, which the user can edit).

- [ ] **Step 8: Run to verify pass**

Run: `pytest frontend/tests/test_config_schema.py -v`. Expected: all PASS.

- [ ] **Step 9: Commit**

```bash
git add frontend/core/config_schema.py frontend/tests/test_config_schema.py
git commit -m "feat: add ForgeWebConfig parameter schema"
```

---

### Task 3: `core/renderer.py`

**Files:**
- Create: `frontend/core/renderer.py`
- Test: `frontend/tests/test_renderer.py`

**Interfaces:**
- Consumes: nothing
- Produces: `TargetExistsError` (Exception), `resolve_tree(template_dir: Path, context: dict) -> list[Path]`, `render_tree(template_dir: Path, target_dir: Path, context: dict) -> None`.

- [ ] **Step 1: Write failing tests**

Port `backend/tests/test_renderer.py`'s test cases (read that file first for the exact assertions — it covers: rendering file contents with Jinja2 placeholders, rendering `{{ var }}` in path segments for both dirs and files, `resolve_tree` returning paths without writing, `render_tree` raising `TargetExistsError` when `target_dir` already exists, and binary files being copied byte-for-byte on `UnicodeDecodeError`). Use a `tmp_path`-based fixture template tree, not `frontend/templates/base/` (doesn't exist yet).

- [ ] **Step 2: Run to verify failure**

Run: `pytest frontend/tests/test_renderer.py -v`. Expected: FAIL — module not found.

- [ ] **Step 3: Implement `renderer.py`**

Copy `backend/core/renderer.py` verbatim into `frontend/core/renderer.py` — the tree-templating algorithm (`_ENV`, `_iter_rendered_files`, `resolve_tree`, `render_tree`, `TargetExistsError`) is generic Jinja2 file-tree logic with no Java-specific behavior, so it reimplements identically for the frontend generator.

- [ ] **Step 4: Run to verify pass**

Run: `pytest frontend/tests/test_renderer.py -v`. Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/core/renderer.py frontend/tests/test_renderer.py
git commit -m "feat: add Jinja2 tree renderer"
```

---

### Task 4: `core/tree_preview.py`

**Files:**
- Create: `frontend/core/tree_preview.py`
- Test: `frontend/tests/test_tree_preview.py`

**Interfaces:**
- Produces: `format_tree(paths: list[Path]) -> str`, `confirm(tree_text: str, prompt_fn=input) -> bool`.

- [ ] **Step 1: Write failing tests**

Port `backend/tests/test_tree_preview.py`'s cases: `format_tree` renders a nested box-drawing tree from a flat path list (assert exact expected string for a small fixture list); `confirm` prints the tree and returns `True` only when the injected `prompt_fn` returns `"y"` or `"yes"` (case-insensitive), `False` otherwise.

- [ ] **Step 2: Run to verify failure**

Run: `pytest frontend/tests/test_tree_preview.py -v`. Expected: FAIL — module not found.

- [ ] **Step 3: Implement `tree_preview.py`**

Copy `backend/core/tree_preview.py` verbatim — this is pure path/string formatting with no backend-specific behavior.

- [ ] **Step 4: Run to verify pass**

Run: `pytest frontend/tests/test_tree_preview.py -v`. Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/core/tree_preview.py frontend/tests/test_tree_preview.py
git commit -m "feat: add tree preview formatter"
```

---

### Task 5: `core/wizard.py`

**Files:**
- Create: `frontend/core/wizard.py`
- Test: `frontend/tests/test_wizard.py`

**Interfaces:**
- Consumes: `ForgeWebConfig`, `validate_project_name` from `core.config_schema` (Task 2)
- Produces: `collect_params(overrides: dict, prompt_fn=input) -> ForgeWebConfig`

- [ ] **Step 1: Write failing tests**

Port `backend/tests/test_wizard.py`'s pattern: given all fields already in `overrides`, `collect_params` returns a `ForgeWebConfig` without calling `prompt_fn`; given a missing field, it calls an injected `prompt_fn` (a stub returning canned answers in sequence) to fill it; given an invalid answer followed by a valid one, it reprompts (asserts `prompt_fn` called twice for that field, and the invalid-value message path is exercised — capture via `capsys` if the backend test does).

- [ ] **Step 2: Run to verify failure**

Run: `pytest frontend/tests/test_wizard.py -v`. Expected: FAIL — module not found.

- [ ] **Step 3: Implement `wizard.py`**

Same shape as `backend/core/wizard.py`, with `FIELD_PROMPTS` adjusted to this package's three fields:

```python
FIELD_PROMPTS = [
    ("project_name", "Project name", validate_project_name),
    ("target_path", "Target path (parent directory)", None),
    ("api_base_url", "API base URL (e.g. http://localhost:8080/api)", None),
]
```

Keep `_prompt_field` and `collect_params` identical in structure to `backend/core/wizard.py` (reprompt loop on `ValueError`, `target_path` expanded/resolved before constructing the config). `api_base_url` has no validator (per Task 2's decision), so it accepts any non-empty prompt answer as-is — still reprompt on an empty string only.

- [ ] **Step 4: Run to verify pass**

Run: `pytest frontend/tests/test_wizard.py -v`. Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/core/wizard.py frontend/tests/test_wizard.py
git commit -m "feat: add interactive parameter wizard"
```

---

### Task 6: `core/validator.py`

**Files:**
- Create: `frontend/core/validator.py`
- Test: `frontend/tests/test_validator.py`

**Interfaces:**
- Produces: `ValidationResult` (dataclass: `passed: bool`, `message: str`, `details: str = ""`) — identical shape to `backend/core/validator.py`'s; `check_structure(target_dir: Path, expected_paths: list[Path]) -> ValidationResult`; `run_build(target_dir: Path, timeout: int = 300) -> ValidationResult`; `run_typecheck(target_dir: Path, timeout: int = 120) -> ValidationResult`; `check_no_hardcoded_design_values(target_dir: Path) -> ValidationResult`.

- [ ] **Step 1: Write failing test for `check_structure`**

Port `backend/tests/test_validator.py`'s two `check_structure` tests verbatim (pass case, missing-files case) — this function's logic is identical.

- [ ] **Step 2: Run to verify failure, then implement `ValidationResult` + `check_structure`**

Copy `backend/core/validator.py`'s `ValidationResult` dataclass and `check_structure` function verbatim. Run `pytest frontend/tests/test_validator.py -v` — PASS.

- [ ] **Step 3: Write failing tests for `run_build`**

Using `tmp_path`: a minimal valid Vite project (a `package.json` with a `build` script that's a no-op, e.g. `"build": "echo built"`, so the test doesn't depend on a real Vite build) passes; a `package.json` whose `build` script exits non-zero (`"build": "exit 1"`) fails with non-empty `details`; a directory with no `package.json` at all fails.

- [ ] **Step 4: Run to verify failure, then implement `run_build`**

```python
def run_build(target_dir: Path, timeout: int = 300) -> ValidationResult:
    """Run `npm install && npm run build` in target_dir."""
    npm_cmd = shutil.which("npm") or "npm"
    for args, label in ([["install"], "npm install"], [["run", "build"], "npm run build"]):
        try:
            result = subprocess.run(
                [npm_cmd, *args], cwd=target_dir, capture_output=True, text=True,
                timeout=timeout, shell=(os.name == "nt"),
            )
        except FileNotFoundError:
            return ValidationResult(False, "npm executable not found on PATH")
        except subprocess.TimeoutExpired:
            return ValidationResult(False, f"{label} timed out after {timeout}s")
        if result.returncode != 0:
            return ValidationResult(False, f"{label} failed", result.stdout + result.stderr)
    return ValidationResult(True, "Build check passed")
```

`shell=(os.name == "nt")` is needed on Windows because `npm` resolves to `npm.cmd`, which `subprocess.run` can't exec directly without shell interpretation — check whether `backend/core/validator.py`'s `run_compile` needed an equivalent workaround for `mvn`; if it didn't (because `mvn` isn't a `.cmd` shim in this environment), verify empirically here with a quick manual `npm install`/`npm run build` run in a scratch tmp dir before trusting the non-shell path first.

- [ ] **Step 5: Run to verify pass**

Run: `pytest frontend/tests/test_validator.py -v`. Expected: PASS.

- [ ] **Step 6: Write failing tests for `run_typecheck`**

Using `tmp_path`: a minimal `tsconfig.json` + a valid one-line `.ts` file passes; a `.ts` file with a type error (e.g. `const x: number = "not a number";`) fails with non-empty `details`. (This test requires `npx tsc` to be resolvable — install `typescript` as a dev dependency of `frontend/` itself, or skip via `pytest.mark.skipif` if `npx` isn't on PATH, matching how `backend`'s `mvn`-dependent tests assume `mvn` is present per `CLAUDE.md`.)

- [ ] **Step 7: Run to verify failure, then implement `run_typecheck`**

```python
def run_typecheck(target_dir: Path, timeout: int = 120) -> ValidationResult:
    """Run `npx tsc --noEmit` in target_dir."""
    npx_cmd = shutil.which("npx") or "npx"
    try:
        result = subprocess.run(
            [npx_cmd, "tsc", "--noEmit"], cwd=target_dir, capture_output=True, text=True,
            timeout=timeout, shell=(os.name == "nt"),
        )
    except FileNotFoundError:
        return ValidationResult(False, "npx executable not found on PATH")
    except subprocess.TimeoutExpired:
        return ValidationResult(False, f"tsc --noEmit timed out after {timeout}s")
    if result.returncode != 0:
        return ValidationResult(False, "tsc --noEmit failed", result.stdout + result.stderr)
    return ValidationResult(True, "Typecheck passed")
```

- [ ] **Step 8: Run to verify pass**

Run: `pytest frontend/tests/test_validator.py -v`. Expected: PASS (or skipped per Step 6's note).

- [ ] **Step 9: Write failing tests for `check_no_hardcoded_design_values`**

Using `tmp_path`: a `.tsx` file containing only Tailwind utility classes (e.g. `className="bg-primary rounded-full"`) and CSS using `var(--color-primary)` passes; a `.tsx`/`.css` file containing a raw hex literal (e.g. `style={{ color: "#0075de" }}`) outside `styles/theme.css` fails, with the offending file path in `details`; the same hex literal *inside* a file named `theme.css` passes (that file is the token source, exempt from the check).

- [ ] **Step 10: Run to verify failure, then implement `check_no_hardcoded_design_values`**

```python
HEX_COLOR_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")

def check_no_hardcoded_design_values(target_dir: Path) -> ValidationResult:
    """Fail if any hex color literal appears in .tsx/.css files outside theme.css."""
    offenders = []
    for path in target_dir.rglob("*"):
        if path.suffix not in (".tsx", ".ts", ".css") or path.name == "theme.css":
            continue
        text = path.read_text(encoding="utf-8")
        if HEX_COLOR_RE.search(text):
            offenders.append(str(path.relative_to(target_dir)))
    if offenders:
        return ValidationResult(
            False, "Hardcoded design values found outside theme.css", "\n".join(offenders)
        )
    return ValidationResult(True, "Design token check passed")
```

- [ ] **Step 11: Run to verify pass**

Run: `pytest frontend/tests/test_validator.py -v`. Expected: all PASS.

- [ ] **Step 12: Commit**

```bash
git add frontend/core/validator.py frontend/tests/test_validator.py
git commit -m "feat: add build, typecheck, and design-token validators"
```

---

### Task 7: `cli.py`

**Files:**
- Create: `frontend/cli.py`
- Test: `frontend/tests/test_cli.py`

**Interfaces:**
- Consumes: `ForgeWebConfig`, `step`, `render_tree`/`resolve_tree`, `confirm`/`format_tree`, `check_structure`/`run_build`/`run_typecheck`/`check_no_hardcoded_design_values`, `collect_params` from Tasks 1-6.
- Produces: `TEMPLATE_DIR: Path`, `EXPECTED_STRUCTURAL_PATHS: list[Path]`, `app` (Typer instance), `new()` command, `main()` entry point.

- [ ] **Step 1: Write failing tests**

Port `backend/tests/test_cli.py`'s pattern (read that file first): monkeypatch `TEMPLATE_DIR` to point at a small fixture template under `tmp_path` (not the real `frontend/templates/base/`, which doesn't exist until Task 8+); assert `new()` errors cleanly (exit code 1) when `TEMPLATE_DIR` doesn't exist; assert it errors when the resolved `target_dir` already exists; assert the happy path (fixture template + `y` confirmation) writes files and calls through to validation.

- [ ] **Step 2: Run to verify failure**

Run: `pytest frontend/tests/test_cli.py -v`. Expected: FAIL — module not found.

- [ ] **Step 3: Implement `cli.py`**

Same overall shape as `backend/cli.py`: a Typer `app`, a `new()` command with options `--name`, `--path`, `--api-base-url`, `--verbose` (dropping `--group-id`/`--artifact-id`, which don't apply here), wiring `collect_params` → existence checks → `resolve_tree`/`confirm` preview → `render_tree` (with the delete-on-failure prompt around it) → `check_structure` → `run_build` → `run_typecheck` → `check_no_hardcoded_design_values`, each gated on the previous passing, each failure prompting to delete the generated folder. `TEMPLATE_DIR = Path(__file__).parent / "templates" / "base"`. `EXPECTED_STRUCTURAL_PATHS` starts as an empty list here — Task 18 populates it once the template's files exist. On full success, print `cd {target_dir}`, `npm run dev` as next steps (no `docker compose`/`mvn` equivalents).

- [ ] **Step 4: Run to verify pass**

Run: `pytest frontend/tests/test_cli.py -v`. Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/cli.py frontend/tests/test_cli.py
git commit -m "feat: wire Forge Web CLI pipeline"
```

---

### Task 8: Vite/TypeScript/Tailwind project skeleton

**Files:**
- Create: `frontend/templates/base/package.json`
- Create: `frontend/templates/base/tsconfig.json`
- Create: `frontend/templates/base/tsconfig.node.json`
- Create: `frontend/templates/base/vite.config.ts`
- Create: `frontend/templates/base/index.html`
- Create: `frontend/templates/base/.env.example`
- Create: `frontend/templates/base/.gitignore`
- Create: `frontend/templates/base/src/main.tsx`
- Create: `frontend/templates/base/src/App.tsx`
- Create: `frontend/templates/base/src/lib/utils.ts`

**Interfaces:**
- Produces: a project skeleton that later tasks (9-17) add components/pages/lib files into. `App.tsx` exports a default `App` component with a `<BrowserRouter>` and an empty `<Routes>` block (`{/* routes added by later tasks */}`) that later tasks fill in. `lib/utils.ts` exports `cn(...inputs: ClassValue[]): string` (the standard Shadcn `clsx` + `tailwind-merge` helper).

No pytest test cycle — this is generated-project scaffolding with no Python logic; verification happens at Task 18's end-to-end build.

- [ ] **Step 1: `package.json`**

`{{ project_name }}` as the `"name"` field. Dependencies: `react`, `react-dom`, `react-router-dom`, `@tanstack/react-query`, `react-hook-form`, `zod`, `@hookform/resolvers`, `clsx`, `tailwind-merge`, `class-variance-authority`, `lucide-react`, `sonner`, plus the `@radix-ui/react-*` primitives the Task 10-11 components need (`react-dialog`, `react-dropdown-menu`, `react-tabs`, `react-select`, `react-label`, `react-avatar`, `react-alert-dialog`, `react-slot`). Dev dependencies: `@tanstack/react-table` (for `data-table`), `typescript`, `vite`, `@vitejs/plugin-react`, `@types/react`, `@types/react-dom`, `tailwindcss`, `@tailwindcss/vite`. Scripts: `"dev": "vite"`, `"build": "tsc -b && vite build"`, `"preview": "vite preview"`.

- [ ] **Step 2: `tsconfig.json` and `tsconfig.node.json`**

Standard Vite React-TS starter split, with a `@/*` path alias mapped to `./src/*` in `tsconfig.json`'s `compilerOptions.paths` (the Shadcn convention every `components/ui/*` import relies on).

- [ ] **Step 3: `vite.config.ts`**

`@vitejs/plugin-react` and `@tailwindcss/vite` plugins; `resolve.alias` mapping `@` to `path.resolve(__dirname, "./src")`, matching the tsconfig alias.

- [ ] **Step 4: `index.html`**

Standard Vite HTML shell; `<title>{{ app_display_name }}</title>`; `<div id="root">`; `<script type="module" src="/src/main.tsx">`.

- [ ] **Step 5: `.env.example`**

```
VITE_APP_NAME={{ app_display_name }}
VITE_API_MODE=mock
VITE_API_BASE_URL={{ api_base_url }}
```

- [ ] **Step 6: `.gitignore`**

Standard Vite project ignores: `node_modules/`, `dist/`, `.env` (but not `.env.example`), editor/OS junk (`.DS_Store`, `.vscode/` optional).

- [ ] **Step 7: `src/main.tsx`**

Renders `<App />` into `#root` inside `<React.StrictMode>`, imports `./styles/theme.css` (created in Task 9 — this import will 404 until then; acceptable since this whole task isn't build-verified until Task 18).

- [ ] **Step 8: `src/App.tsx`**

`<BrowserRouter>` wrapping a `QueryClientProvider` (Task 14 supplies the `queryClient`; leave a `// TODO: wrap with QueryClientProvider once lib/hooks exists` marker is **not allowed** per the no-placeholders rule for finished code — instead, Task 14 revisits and edits this exact file to add the provider once `lib/hooks/` exists. For now, `App.tsx` renders `<BrowserRouter><Routes>{/* routes added by Task 17 */}</Routes></BrowserRouter>` — routes are template comments describing what a later task adds, not TODOs about this task's own scope).

- [ ] **Step 9: `src/lib/utils.ts`**

```typescript
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

- [ ] **Step 10: Commit**

```bash
git add frontend/templates/base/package.json frontend/templates/base/tsconfig.json frontend/templates/base/tsconfig.node.json frontend/templates/base/vite.config.ts frontend/templates/base/index.html frontend/templates/base/.env.example frontend/templates/base/.gitignore frontend/templates/base/src/main.tsx frontend/templates/base/src/App.tsx frontend/templates/base/src/lib/utils.ts
git commit -m "feat: add Vite/React/TypeScript/Tailwind project skeleton"
```

---

### Task 9: `src/styles/theme.css` — design tokens

**Files:**
- Create: `frontend/templates/base/src/styles/theme.css`

**Interfaces:**
- Produces: the single source of truth for every color/typography/spacing/radius/shadow CSS custom property, consumed by every component file in Tasks 10-17. Exempt from the hardcoded-hex check (Task 6).

- [ ] **Step 1: Author the `@theme` block — colors**

Read `docs/DESIGN.md`'s "Colors" section in full (no YAML front matter in this version — every token is defined inline in prose, e.g. "**Rausch** (`{colors.primary}` — #ff385c)"). Transcribe every token into a Tailwind v4 `@theme { ... }` block using `--color-*` naming, reading the hex value straight out of each bullet:

- Brand & Accent: `--color-primary: #ff385c;`, `--color-primary-active: #e00b41;`, `--color-primary-disabled: #ffd1da;`, `--color-luxe: #460479;`, `--color-plus: #92174d;` (the last two are documented sub-brand tokens, not used by any component this template builds — define them for completeness/future use, but nothing in Tasks 10-17 references them).
- Surface: `--color-canvas: #ffffff;`, `--color-surface-soft: #f7f7f7;`, `--color-surface-strong: #f2f2f2;`.
- Hairlines & Borders: `--color-hairline: #dddddd;`, `--color-hairline-soft: #ebebeb;`, `--color-border-strong: #c1c1c1;`.
- Text: `--color-ink: #222222;`, `--color-body: #3f3f3f;`, `--color-muted: #6a6a6a;`, `--color-muted-soft: #929292;`, `--color-on-primary: #ffffff;`.
- Semantic: `--color-error-text: #c13515;`, `--color-error-text-hover: #b32505;`, `--color-legal-link: #428bff;`.
- Scrim: `--color-scrim: #000000;` (opacity applied at the call site, e.g. `bg-scrim/50`, per the doc's "stored as the base hex; opacity applied at render time" note).

- [ ] **Step 2: Author the `@theme` block — typography, spacing, radius, shadow**

From the "Typography" > Hierarchy table, add one `--text-*` custom property per row using its size (e.g. `--text-body-md: 16px;`, `--text-body-sm: 14px;`, `--text-caption: 14px;`, `--text-button-md: 16px;`) — this template only needs a working subset for its own components, not the full marketing scale: `body-md`, `body-sm`, `caption`, `button-md`, `button-sm`, `link`, `title-sm`, `display-sm` are the ones Tasks 10-17 actually use; skip marketing-only rows (`rating-display`, `display-xl`, `nav-link`, `uppercase-tag`, `badge`, `micro-label`) since no dashboard component in this plan needs them. Font family: `--font-sans: Inter, -apple-system, system-ui, Roboto, "Helvetica Neue", sans-serif;` (per the doc's "Note on Font Substitutes" — Airbnb Cereal VF is proprietary, Inter is the documented open-source substitute).

From "Layout > Spacing System": `--spacing-xxs: 2px; --spacing-xs: 4px; --spacing-sm: 8px; --spacing-md: 12px; --spacing-base: 16px; --spacing-lg: 24px; --spacing-xl: 32px; --spacing-xxl: 48px; --spacing-section: 64px;`.

From the doc's shape references (no dedicated "Shapes" section in this version — radius values are named inline): `--radius-sm: 8px;` (buttons, text-input, per "Buttons" and "Forms"), `--radius-md: 14px;` (property/host/reservation cards, per "Listing Cards"/"Listing Detail" — the doc gives this as "~14px", so use 14px exactly as the template's fixed value), `--radius-xl: 32px;` (per "category strip rounded corners run at 32px" in Key Characteristics — used sparingly), `--radius-full: 9999px;` (pills, circles). There is no `sm`/`lg`/`xs` beyond what's listed — this scale has 4 steps, not 6.

From "## Elevation": `--shadow-1: rgba(0, 0, 0, 0.02) 0 0 0 1px, rgba(0, 0, 0, 0.04) 0 2px 6px 0, rgba(0, 0, 0, 0.1) 0 4px 8px 0;` — the system's one shadow tier, used for hover-floated cards and dropdown/modal surfaces. There is no `--shadow-2` in this design (elevation is capped at one tier plus flat).

- [ ] **Step 3: Import into the app**

Confirm `src/main.tsx` (Task 8, Step 7) imports this file — it already does (`import "./styles/theme.css"`).

- [ ] **Step 4: Manual sanity check**

Visually diff every token against `docs/DESIGN.md`'s prose/tables — every value must match exactly (no rounding, no approximation). Confirm no dark-mode block was added (out of scope per the Global Constraints).

- [ ] **Step 5: Commit**

```bash
git add frontend/templates/base/src/styles/theme.css
git commit -m "feat: add design-token theme (light + auto-derived dark)"
```

---

### Task 10: `components/ui/` — core primitives

**Files:**
- Create: `frontend/templates/base/src/components/ui/button.tsx`
- Create: `frontend/templates/base/src/components/ui/input.tsx`
- Create: `frontend/templates/base/src/components/ui/label.tsx`
- Create: `frontend/templates/base/src/components/ui/card.tsx`
- Create: `frontend/templates/base/src/components/ui/badge.tsx`
- Create: `frontend/templates/base/src/components/ui/skeleton.tsx`

**Interfaces:**
- Consumes: `cn` from `@/lib/utils` (Task 8).
- Produces: React components consumed by Tasks 11-17. `Button` accepts a `variant` prop (`"default" | "secondary" | "outline" | "ghost"`) mapped per `docs/DESIGN.md`'s "Buttons" section: `"default"` → Rausch fill (`bg-primary`), white text, `rounded-sm` (8px), per `button-primary`; `"secondary"` → white fill, ink text, 1px ink outline, `rounded-sm`, per `button-secondary`; `"outline"` → same chrome as `"secondary"` (the doc has no third bordered variant, so `outline` reuses `button-secondary`'s treatment); `"ghost"` → plain ink text, no surface/border, underline on hover, per `button-tertiary-text`. All four variants use the same `rounded-sm` (8px) radius — this design has no default pill-shaped CTA (the one pill button, `button-pill-rausch`, is a marketing-only "featured cell" pattern and is not part of this curated set).

- [ ] **Step 1: Implement each component**

Follow the standard Shadcn/ui `button`/`input`/`label`/`card`/`badge`/`skeleton` component source structure (Radix `Slot` for `Button`'s `asChild`, `class-variance-authority` for variant maps, `cn()` for class merging) — the canonical Shadcn implementations, with every color/radius/spacing/shadow/font class pointed at this template's `theme.css` tokens (`bg-primary`, `text-on-primary`, `rounded-sm`, `shadow-1`, `text-body-sm`, etc.) instead of Shadcn's stock `bg-primary`/zinc defaults. `Input` matches `docs/DESIGN.md`'s `text-input`: white surface, 1px hairline outline, `rounded-sm`, focus flips the border to 2px ink (no glow/ring). `Card` matches the `host-card`/`reservation-card` chrome: white surface, `rounded-md` (14px), `spacing-lg` (24px) padding. No hex literals, no arbitrary Tailwind values (`bg-[#...]`) anywhere.

- [ ] **Step 2: Manual sanity check**

Grep each new file for `#` followed by a hex-like sequence — none should exist (Task 6's `check_no_hardcoded_design_values` will enforce this for real once the template is complete, but catching it now is cheaper than waiting for Task 18).

- [ ] **Step 3: Commit**

```bash
git add frontend/templates/base/src/components/ui/button.tsx frontend/templates/base/src/components/ui/input.tsx frontend/templates/base/src/components/ui/label.tsx frontend/templates/base/src/components/ui/card.tsx frontend/templates/base/src/components/ui/badge.tsx frontend/templates/base/src/components/ui/skeleton.tsx
git commit -m "feat: add core Shadcn UI primitives themed to DESIGN.md tokens"
```

---

### Task 11: `components/ui/` — composite components

**Files:**
- Create: `frontend/templates/base/src/components/ui/table.tsx`
- Create: `frontend/templates/base/src/components/ui/data-table.tsx`
- Create: `frontend/templates/base/src/components/ui/tabs.tsx`
- Create: `frontend/templates/base/src/components/ui/select.tsx`
- Create: `frontend/templates/base/src/components/ui/dialog.tsx`
- Create: `frontend/templates/base/src/components/ui/alert-dialog.tsx`
- Create: `frontend/templates/base/src/components/ui/dropdown-menu.tsx`
- Create: `frontend/templates/base/src/components/ui/sonner.tsx`
- Create: `frontend/templates/base/src/components/ui/form.tsx`
- Create: `frontend/templates/base/src/components/ui/avatar.tsx`

**Interfaces:**
- Consumes: `cn` from `@/lib/utils`, `Button` from `@/components/ui/button` (Task 10, used by `dialog`/`alert-dialog` footers).
- Produces: `data-table.tsx` exports a generic `DataTable<TData, TValue>({ columns, data }: { columns: ColumnDef<TData, TValue>[]; data: TData[] })` component (wraps `@tanstack/react-table`), consumed by Task 16's dashboard page. `form.tsx` exports the Shadcn `Form`/`FormField`/`FormItem`/`FormLabel`/`FormControl`/`FormMessage` set built on `react-hook-form`'s `FormProvider`, consumed by Task 16's item form. `sonner.tsx` exports a `Toaster` component (re-exports the `sonner` package's toaster styled with theme tokens), consumed by `App.tsx` (Task 17 wires it in).

- [ ] **Step 1: Implement each component**

Same approach as Task 10: canonical Shadcn/ui source for `table`, `data-table` (the `@tanstack/react-table` wrapper pattern from Shadcn's docs), `tabs`, `select`, `dialog`, `alert-dialog`, `dropdown-menu` (all Radix-primitive wrappers), `sonner` (theme-aware `Toaster` re-export), `form` (the `react-hook-form` context wiring), `avatar` — every style value from `theme.css` tokens, no hex literals. Dialog/alert-dialog/dropdown-menu surfaces use the one elevation tier this design has (`shadow-1`, per `docs/DESIGN.md`'s "Elevation" section — "used on... the dropdown menus (account menu, language picker, date picker)") and `rounded-md` (14px, matching the `host-card`/`reservation-card` surface chrome, not `rounded-xl` — that token is reserved for the marketing-only category-strip pattern). Dialog's backdrop uses `--color-scrim` at 50% opacity (`bg-scrim/50`), per the doc's "Scrim" token.

- [ ] **Step 2: Manual sanity check**

Same hex-grep spot-check as Task 10, Step 2.

- [ ] **Step 3: Commit**

```bash
git add frontend/templates/base/src/components/ui/table.tsx frontend/templates/base/src/components/ui/data-table.tsx frontend/templates/base/src/components/ui/tabs.tsx frontend/templates/base/src/components/ui/select.tsx frontend/templates/base/src/components/ui/dialog.tsx frontend/templates/base/src/components/ui/alert-dialog.tsx frontend/templates/base/src/components/ui/dropdown-menu.tsx frontend/templates/base/src/components/ui/sonner.tsx frontend/templates/base/src/components/ui/form.tsx frontend/templates/base/src/components/ui/avatar.tsx
git commit -m "feat: add composite Shadcn UI components themed to DESIGN.md tokens"
```

---

### Task 12: `components/common/` — app shell, nav

**Files:**
- Create: `frontend/templates/base/src/components/common/app-shell.tsx`
- Create: `frontend/templates/base/src/components/common/nav-sidebar.tsx`

**Interfaces:**
- Consumes: `Button` (Task 10), `cn` (Task 8).
- Produces: `AppShell({ children }: { children: React.ReactNode })` — page layout wrapping `NavSidebar` + a main content area, consumed by Task 16/17 pages. `NavSidebar` — a vertical sidebar nav (the source design only documents a horizontal `top-nav` with an underline active-indicator; this component adapts that same idea — ink label + `--color-primary` accent marking the active item — to a vertical layout, since the dashboard uses a sidebar).

- [ ] **Step 1: Implement `nav-sidebar.tsx`**

A vertical nav list with exactly two `NavLink`s — "Dashboard" pointing at `/` and "Components" pointing at `/components` — matching the two pages Task 16 builds; no placeholder links for pages that don't exist. Inactive links: `--color-muted` text (per `docs/DESIGN.md`'s "Muted" token, used for inactive product-tab labels in the source design). Active link: `--color-ink` text, `--color-surface-soft` row background, a 2px left border in `--color-primary` as the active indicator (the vertical-nav equivalent of the source design's `product-tab-active` underline rule), `rounded-sm`.

- [ ] **Step 2: Implement `app-shell.tsx`**

A flex layout: `NavSidebar` fixed-width on the left, `children` in a scrollable main area on `bg-canvas` (Airbnb's public pages are pure white, per `docs/DESIGN.md` — no separate "soft" page canvas the way the previous design draft used).

- [ ] **Step 3: Commit**

```bash
git add frontend/templates/base/src/components/common/app-shell.tsx frontend/templates/base/src/components/common/nav-sidebar.tsx
git commit -m "feat: add app shell and nav sidebar"
```

---

### Task 13: `lib/api-client/` — mock/real client

**Files:**
- Create: `frontend/templates/base/src/lib/api-client/types.ts`
- Create: `frontend/templates/base/src/lib/api-client/api-client.ts`
- Create: `frontend/templates/base/src/lib/api-client/mock-client.ts`
- Create: `frontend/templates/base/src/lib/api-client/real-client.ts`
- Create: `frontend/templates/base/src/lib/api-client/index.ts`

**Interfaces:**
- Produces: `types.ts` exports `Item` (`{ id: string; name: string; status: "active" | "archived"; createdAt: string }`) — the one sample domain type, matching Forge backend's single-example-entity philosophy (an `Item`, analogous to `Example`). `api-client.ts` exports the `ApiClient` interface: `{ listItems(): Promise<Item[]>; getItem(id: string): Promise<Item>; createItem(input: { name: string }): Promise<Item>; updateItem(id: string, input: { name: string; status: Item["status"] }): Promise<Item>; deleteItem(id: string): Promise<void> }`. `mock-client.ts` exports `mockClient: ApiClient` (in-memory array seeded with 3-5 fixture items, simulated latency via `setTimeout`-wrapped promises). `real-client.ts` exports `realClient: ApiClient` (each method a `fetch(\`${import.meta.env.VITE_API_BASE_URL}/items...\`)` call, throwing on non-2xx). `index.ts` exports `apiClient: ApiClient = import.meta.env.VITE_API_MODE === "real" ? realClient : mockClient` — the single env-driven switch point every consumer imports.

- [ ] **Step 1: Implement `types.ts` and `api-client.ts`**

As specified above — the interface is the contract Tasks 14/16 code against.

- [ ] **Step 2: Implement `mock-client.ts`**

In-memory `Item[]` array (module-level, mutated by `createItem`/`updateItem`/`deleteItem`), each method wrapped to resolve after a short artificial delay (e.g. 300ms via a `delay()` helper) so the dashboard's loading states are visibly exercised even against mock data.

- [ ] **Step 3: Implement `real-client.ts`**

Straightforward `fetch`-based implementation of the same interface, reading `import.meta.env.VITE_API_BASE_URL` once per call (not cached at module load, so `.env` edits without a rebuild — n/a for Vite which inlines env vars at build time, but read it from the same constant each call for consistency/testability).

- [ ] **Step 4: Implement `index.ts`**

The env-driven switch, as specified above.

- [ ] **Step 5: Commit**

```bash
git add frontend/templates/base/src/lib/api-client/types.ts frontend/templates/base/src/lib/api-client/api-client.ts frontend/templates/base/src/lib/api-client/mock-client.ts frontend/templates/base/src/lib/api-client/real-client.ts frontend/templates/base/src/lib/api-client/index.ts
git commit -m "feat: add mock/real API client behind one interface"
```

---

### Task 14: `lib/hooks/use-items.ts` — TanStack Query wiring

**Files:**
- Create: `frontend/templates/base/src/lib/hooks/use-items.ts`
- Modify: `frontend/templates/base/src/App.tsx` (Task 8) — wrap with `QueryClientProvider`

**Interfaces:**
- Consumes: `apiClient` from `@/lib/api-client` (Task 13).
- Produces: `useItems()` (wraps `useQuery(["items"], apiClient.listItems)`), `useCreateItem()`, `useUpdateItem()`, `useDeleteItem()` (each a `useMutation` that invalidates the `["items"]` query key on success) — consumed by Task 16's dashboard page and item form.

- [ ] **Step 1: Implement `use-items.ts`**

Four hooks per the signatures above, using `@tanstack/react-query`'s `useQuery`/`useMutation`/`useQueryClient`.

- [ ] **Step 2: Wrap `App.tsx` with `QueryClientProvider`**

Edit `frontend/templates/base/src/App.tsx`: instantiate `const queryClient = new QueryClient()` at module scope, wrap the existing `<BrowserRouter>` tree in `<QueryClientProvider client={queryClient}>`.

- [ ] **Step 3: Commit**

```bash
git add frontend/templates/base/src/lib/hooks/use-items.ts frontend/templates/base/src/App.tsx
git commit -m "feat: add TanStack Query hooks and wire QueryClientProvider"
```

---

### Task 15: `lib/utils/format.ts` — date/currency formatters

**Files:**
- Create: `frontend/templates/base/src/lib/utils/format.ts`

**Interfaces:**
- Produces: `formatDate(iso: string): string` (uses `Intl.DateTimeFormat`, medium style), `formatCurrency(amount: number, currency = "USD"): string` (uses `Intl.NumberFormat`).

- [ ] **Step 1: Implement both formatters**

```typescript
export function formatDate(iso: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(iso));
}

export function formatCurrency(amount: number, currency = "USD"): string {
  return new Intl.NumberFormat(undefined, { style: "currency", currency }).format(amount);
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/templates/base/src/lib/utils/format.ts
git commit -m "feat: add date/currency formatters"
```

---

### Task 16: `pages/dashboard/` — sample dashboard + form + component showcase

**Files:**
- Create: `frontend/templates/base/src/pages/dashboard/dashboard-page.tsx`
- Create: `frontend/templates/base/src/pages/dashboard/item-form.tsx`
- Create: `frontend/templates/base/src/pages/showcase/component-showcase-page.tsx`

**Interfaces:**
- Consumes: `useItems`/`useCreateItem`/`useUpdateItem`/`useDeleteItem` (Task 14), `DataTable` (Task 11), `Dialog`/`Form`/`Button`/`Input`/`Badge`/`Skeleton` (Tasks 10-11), `formatDate` (Task 15).
- Produces: `DashboardPage` (default export) — the page routed at `/` (wired in Task 17). `ItemForm({ item, onSuccess }: { item?: Item; onSuccess: () => void })` — the create/edit form. `ComponentShowcasePage` (default export) — the page routed at `/components` (wired in Task 17), giving the user a single screen to visually confirm every generated UI primitive against the theme before building real screens.

- [ ] **Step 1: Implement `item-form.tsx`**

`react-hook-form` + `zod` schema (`z.object({ name: z.string().min(1), status: z.enum(["active", "archived"]) })`), rendered via `Form`/`FormField` (Task 11). Submits via `useCreateItem()` when `item` is undefined, `useUpdateItem()` otherwise; calls `onSuccess()` after the mutation resolves.

- [ ] **Step 2: Implement `dashboard-page.tsx`**

`useItems()` for data; while loading, render `Skeleton` rows instead of the table (exercises the mock client's artificial delay from Task 13); columns for the `DataTable`: name, `Badge`-rendered status (`"active"` → default variant, `"archived"` → `"outline"` variant), `formatDate(createdAt)`, and a row-actions `DropdownMenu` (edit → opens a `Dialog` containing `ItemForm`; delete → `useDeleteItem()`). A "New Item" `Button` opens the same `Dialog`/`ItemForm` in create mode. Empty result set (zero items) renders `EmptyState` — a forward reference to Task 17's component; if Task 17 hasn't run yet in your execution order, implement this task's empty-state branch as a plain inline message here and let Task 17 refactor `dashboard-page.tsx` to import the shared `EmptyState` component instead (Task 17's Step list includes this edit explicitly).

- [ ] **Step 3: Implement `component-showcase-page.tsx`**

One scrollable page, organized into labeled sections (each a `<section>` with a `heading-3`-styled title), one section per component from Tasks 10-11, each rendering that component with representative mock data/variants so a user can see every generated primitive at a glance without wiring up real screens:

- **Buttons** — one of each `Button` `variant` (`default`, `secondary`, `outline`, `ghost`) side by side, plus a disabled state.
- **Inputs** — `Input` with a `Label`, one enabled and one `disabled`.
- **Cards** — a `Card` with `CardHeader`/`CardTitle`/`CardContent` filled with placeholder copy.
- **Badges** — one of each status variant (matching the `active`/`archived` styling used in Task 16's dashboard table).
- **Skeleton** — a row of `Skeleton` placeholders in a few sizes (text line, avatar circle, card block).
- **Table / DataTable** — the same `DataTable` component from Task 11, fed 3 hardcoded mock rows (name/status/date) with the same `columns` shape `dashboard-page.tsx` uses, so this page doubles as a live example of `DataTable`'s usage pattern independent of the API client.
- **Tabs** — a `Tabs` with 2-3 mock panels of placeholder text.
- **Select** — a `Select` with 3-4 mock options.
- **Dialog** — a `Button` that opens a `Dialog` with placeholder title/description/footer actions.
- **AlertDialog** — a `Button` that opens an `AlertDialog` with a mock "Are you sure?" confirmation.
- **DropdownMenu** — a trigger `Button` with 3 mock menu items.
- **Sonner (toast)** — a `Button` that calls `toast("This is a sample notification")` on click, to confirm the `Toaster` mounted in `App.tsx` (Task 17) actually renders.
- **Form** — a static (non-submitting) `Form`/`FormField` example with one text field and its label/description/validation-message slots all visibly populated, so the form primitives' typography and spacing are visible without needing `ItemForm`'s live validation.
- **Avatar** — an `Avatar` with a fallback initials and one with a mock image URL.

Wrap the whole page in `AppShell` (Task 12) so it's reachable through the same nav chrome as the dashboard. No live data, no `useItems`/API-client usage anywhere on this page — every value is a hardcoded mock, since its only job is to prove out the design system, not real functionality.

- [ ] **Step 4: Commit**

```bash
git add frontend/templates/base/src/pages/dashboard/dashboard-page.tsx frontend/templates/base/src/pages/dashboard/item-form.tsx frontend/templates/base/src/pages/showcase/component-showcase-page.tsx
git commit -m "feat: add sample dashboard page with CRUD form and component showcase page"
```

---

### Task 17: `pages/static/` — 404, error, loading, empty state; route wiring

**Files:**
- Create: `frontend/templates/base/src/pages/static/not-found-page.tsx`
- Create: `frontend/templates/base/src/pages/static/error-page.tsx`
- Create: `frontend/templates/base/src/pages/static/loading-page.tsx`
- Create: `frontend/templates/base/src/pages/static/empty-state.tsx`
- Modify: `frontend/templates/base/src/App.tsx` — add routes, `Toaster`
- Modify: `frontend/templates/base/src/pages/dashboard/dashboard-page.tsx` (Task 16) — use shared `EmptyState`

**Interfaces:**
- Produces: `NotFoundPage`, `ErrorPage` (accepts an optional `message?: string` prop; used both as a route and as a React Router `errorElement`), `LoadingPage` (full-page loading state using `Skeleton`), `EmptyState({ title, description, action }: { title: string; description: string; action?: React.ReactNode })` — consumed by `dashboard-page.tsx`.

- [ ] **Step 1: Implement all four static pages**

Each uses `AppShell` (Task 12) for layout consistency except `NotFoundPage`/`ErrorPage`, which render full-bleed (no sidebar) since they may fire before the shell's data is available. `docs/DESIGN.md` has no dedicated empty-state token in this version, so `EmptyState`'s surface reuses the same card chrome as `host-card`/`reservation-card`: `bg-surface-soft`, `rounded-md` (14px), generous `spacing-xxl` (48px) padding, `body-md` text in `--color-muted` for the description line.

- [ ] **Step 2: Wire routes into `App.tsx`**

Replace the `{/* routes added by Task 17 */}` placeholder comment (Task 8) with real `<Routes>`: `/` → `AppShell` wrapping `DashboardPage`, `/components` → `AppShell` wrapping `ComponentShowcasePage` (Task 16), `*` → `NotFoundPage`. Add `<Toaster />` (Task 11) once, outside `<Routes>`, inside the provider tree.

- [ ] **Step 3: Refactor `dashboard-page.tsx` to use `EmptyState`**

Replace Task 16 Step 2's inline empty-message branch with `<EmptyState title="No items yet" description="Create your first item to get started." action={<Button onClick={...}>New Item</Button>} />`.

- [ ] **Step 4: Commit**

```bash
git add frontend/templates/base/src/pages/static/not-found-page.tsx frontend/templates/base/src/pages/static/error-page.tsx frontend/templates/base/src/pages/static/loading-page.tsx frontend/templates/base/src/pages/static/empty-state.tsx frontend/templates/base/src/App.tsx frontend/templates/base/src/pages/dashboard/dashboard-page.tsx
git commit -m "feat: add static pages and wire application routes"
```

---

### Task 18: End-to-end generation test + final CLI wiring

**Files:**
- Modify: `frontend/cli.py` — populate `EXPECTED_STRUCTURAL_PATHS`
- Create: `frontend/tests/test_generation.py`

**Interfaces:**
- Consumes: every module from Tasks 1-17.
- Produces: the generator's own regression guarantee — a real render + real `npm install`/`npm run build`/`tsc --noEmit`/design-token check, run as part of `pytest frontend/tests -v`.

- [ ] **Step 1: Populate `EXPECTED_STRUCTURAL_PATHS` in `cli.py`**

List every file path created in Tasks 8-17 (relative to the rendered project root) — `package.json`, `tsconfig.json`, `index.html`, `.env.example`, `src/main.tsx`, `src/App.tsx`, `src/styles/theme.css`, every `src/components/ui/*.tsx` from Tasks 10-11, every `src/components/common/*.tsx` from Task 12, every `src/lib/api-client/*.ts` from Task 13, `src/lib/hooks/use-items.ts`, `src/lib/utils/format.ts`, `src/pages/dashboard/*.tsx`, `src/pages/showcase/component-showcase-page.tsx`, `src/pages/static/*.tsx`.

- [ ] **Step 2: Write `test_generation.py`**

```python
from pathlib import Path

from cli import EXPECTED_STRUCTURAL_PATHS, TEMPLATE_DIR
from core.config_schema import ForgeWebConfig
from core.renderer import render_tree
from core.validator import (
    check_no_hardcoded_design_values,
    check_structure,
    run_build,
    run_typecheck,
)


def test_generated_project_builds_and_typechecks(tmp_path):
    config = ForgeWebConfig(
        project_name="test-dashboard",
        target_path=tmp_path,
        api_base_url="http://localhost:8080/api",
    )
    render_tree(TEMPLATE_DIR, config.target_dir, config.template_context())

    structural = check_structure(config.target_dir, EXPECTED_STRUCTURAL_PATHS)
    assert structural.passed, structural.details

    build = run_build(config.target_dir)
    assert build.passed, build.details

    typecheck = run_typecheck(config.target_dir)
    assert typecheck.passed, typecheck.details

    tokens = check_no_hardcoded_design_values(config.target_dir)
    assert tokens.passed, tokens.details
```

- [ ] **Step 3: Run and fix**

Run: `pytest frontend/tests/test_generation.py -v`. This is the first point every file from Tasks 8-17 is exercised together — expect and fix real issues (missing imports, Jinja `StrictUndefined` errors from a template variable not in `template_context()`, TypeScript errors, stray hex literals, npm dependency mismatches between `package.json` and actual imports). Iterate until PASS. This step has no fixed expected output — the fix is whatever the actual failure says.

- [ ] **Step 4: Run the full test suite**

Run: `pytest frontend/tests -v`. Expected: all tests across every task pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/cli.py frontend/tests/test_generation.py
git commit -m "test: add end-to-end generation test covering build, typecheck, and design tokens"
```

---

## Manual Verification (after Task 18)

- [ ] Run `.venv\Scripts\forge-web new --name demo-app --path <scratch-dir> --api-base-url http://localhost:8080/api`, confirm the preview tree, let it generate.
- [ ] `cd` into the generated project, `npm run dev`, open the dashboard in a browser — confirm the mock data table renders, the create/edit dialog works, and the empty state appears after deleting all items.
- [ ] Navigate to `/components`, confirm every Task 10-11 component renders with its mock data (buttons, inputs, cards, badges, skeletons, table/data-table, tabs, select, dialog, alert-dialog, dropdown-menu, toast trigger, form fields, avatar).
- [ ] Navigate to a nonexistent route, confirm the 404 page renders.
- [ ] Edit `src/styles/theme.css`'s `--color-primary` value, confirm the change propagates to every button/link without touching any component file — this is the concrete proof of the "edit one file, whole app updates" requirement.
