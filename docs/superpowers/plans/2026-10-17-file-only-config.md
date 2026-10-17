# File-Only Project Config and `init` Implementation Plan

> **For agentic workers:** Execute inline (native). Steps use checkbox (`- [ ]`) syntax for tracking. Do not commit; leave changes in the working tree for review.

**Goal:** `forge new` / `forge-web new` take no parameters and read a config file from the current folder; `forge init` / `forge-web init` write a commented starter file; the READMEs are rewritten to match.

**Architecture:** Each package gets one new module that turns its config file into the existing validated config object (backend: `ForgeConfig`, frontend: `ForgeWebConfig`) and one that renders the starter file. The interactive wizard is removed. The render/validate pipeline is unchanged.

**Tech Stack:** Python 3.11+, Typer, Pydantic v2, PyYAML, pytest. Backend also uses Maven for compile checks; frontend uses npm for build checks.

**Spec:** `docs/superpowers/specs/2026-10-17-file-only-config-design.md`

## Global Constraints

- Backend config file name: `forge.yaml`. Frontend config file name: `forge-web.yaml`.
- Backend required keys: `project_name`, `target_path`, `group_id`, `artifact_id`. Optional: `template` (default `base-layered`), `entities`.
- Frontend required keys: `project_name`, `target_path`, `api_base_url`. Optional: `template` (default `base`).
- `init` refuses to overwrite an existing config file (exit 1; message names the file).
- `new` without a config file: exit 1, message `No <file> found in <cwd>. Run "<cli> init" first.`
- `new` never prompts. Invalid or missing values: print every problem, exit 1, write nothing.
- `--verbose` is the only option kept on `new`.
- Existing preview, confirm, render and validate steps are unchanged.

## Review Focus

- Config file exists but is empty (`""`) → reported as missing required keys, not a crash. Test in Task 1 and Task 4.
- `target_path` written with `~` or a relative path → expanded and resolved to an absolute path, as the wizard did. Test in Task 1 and Task 4.
- Config file with unknown key (typo such as `artifactId`) → rejected with the key named (already true via `extra="forbid"` for backend; frontend loader must do the same). Test in Task 4.
- `init` run in a folder that already has the file → exit 1 and file untouched. Test in Task 2 and Task 5.
- Starter file written by `init` parses and validates as-is except for the placeholder values, so `new` after editing the placeholders succeeds. Test in Task 2 and Task 5.

---

## Backend (`backend/`)

### Task 1: Project-file → ForgeConfig builder

**Files:**
- Create: `backend/core/project_config.py`
- Test: `backend/tests/test_project_config.py`

**Interfaces:**
- Consumes: `core.entity_spec.load_forge_yaml(path) -> ProjectFile` (existing, unchanged); `core.config_schema.ForgeConfig`.
- Produces:
  - `REQUIRED_KEYS: tuple[str, ...] = ("project_name", "target_path", "group_id", "artifact_id")`
  - `build_config(path: Path) -> ForgeConfig` — loads the file, checks required keys are present and non-empty, builds `ForgeConfig(project_name=..., target_path=Path(...).expanduser().resolve(), group_id=..., artifact_id=..., template=file.template or "base-layered", entities=file.entities)`. Raises `ValueError` with a message listing every missing key (one per line, `  - <key>: missing`) prefixed by `Invalid <path>:`. `ForgeConfig` validation errors are re-raised as `ValueError` with the same path prefix.
  - `MissingConfigError(FileNotFoundError)` raised when `path` does not exist, with the message from the spec (`No forge.yaml found in <cwd>. Run "forge init" first.` — the CLI formats it; the error carries only the path).

- [ ] **Step 1: Write failing tests** in `test_project_config.py`:
  - a complete file → `build_config` returns a `ForgeConfig` with the same values; `template` defaults to `base-layered`.
  - `target_path: ~/x` → resolved absolute path.
  - file missing a required key → `ValueError` containing that key name.
  - empty file → `ValueError` listing all four required keys.
  - unknown key → `ValueError` (from `load_forge_yaml`).
  - invalid `project_name` (e.g. `My_Service`) → `ValueError` mentioning `project_name`.
  - non-existent path → `MissingConfigError`.
- [ ] **Step 2: Run** `.venv\Scripts\pytest backend/tests/test_project_config.py -v` → expect FAIL (module missing).
- [ ] **Step 3: Implement** `core/project_config.py` per Interfaces. Reuse `load_forge_yaml`; do not duplicate its parsing.
- [ ] **Step 4: Run** the same command → expect PASS.

### Task 2: Starter file writer (`forge init` logic)

**Files:**
- Modify: `backend/core/project_config.py` (add functions)
- Test: `backend/tests/test_project_config.py` (add tests)

**Interfaces:**
- Consumes: Task 1.
- Produces:
  - `STARTER_TEMPLATE: str` — commented YAML with the four required keys set to placeholder values (`project_name: my-service`, `target_path: .`, `group_id: com.example`, `artifact_id: my-service`), `template: base-layered` with a comment listing `base-layered` and `minimal`, and a commented-out `entities:` example block (one entity with two fields and one relation). Each key has a one-line comment explaining allowed values.
  - `write_starter(path: Path) -> None` — raises `FileExistsError` (message names the path) if `path` exists; otherwise writes `STARTER_TEMPLATE`.

- [ ] **Step 1: Write failing tests**: `write_starter` creates the file; the file content loads via `load_forge_yaml` without error; `write_starter` on an existing file raises `FileExistsError` and leaves content unchanged.
- [ ] **Step 2: Run** the test file → FAIL.
- [ ] **Step 3: Implement** `STARTER_TEMPLATE` and `write_starter`.
- [ ] **Step 4: Run** → PASS.

### Task 3: Wire `init` and file-only `new` into the CLI

**Files:**
- Modify: `backend/cli.py` (`new` command at lines ~197–326; add `init` command; remove wizard/entity imports that become unused)
- Test: `backend/tests/test_cli.py` (update), `backend/tests/test_cli_from.py` (replace with file-only tests)

**Interfaces:**
- Consumes: `build_config`, `MissingConfigError`, `write_starter` from Tasks 1–2.
- Produces: CLI commands `forge init [--verbose]`… — `init` takes no options except none; `forge new [--verbose]`.

Behavior of `new` (in order):
1. Resolve `Path.cwd() / "forge.yaml"`. Missing → print the spec message, exit 1.
2. `build_config(path)`; `ValueError` → print `Error: <message>`, exit 1.
3. Print resolved values as a short block: project name, target dir (`config.target_dir`), group id, artifact id, template. Print `Config: <path>` first.
4. Target directory exists → exit 1 (existing check).
5. Continue with the existing preview / confirm / render / validate code unchanged. Remove the entity-step block and the "Save the model as forge.yaml?" prompt (the entities come from the file).

Behavior of `init`: `write_starter(cwd / "forge.yaml")`; `FileExistsError` → print `Error: <message>`, exit 1; success → print `Created forge.yaml. Edit it, then run "forge new".`

- [ ] **Step 1: Write failing CLI tests** (Typer `CliRunner`, `monkeypatch.chdir(tmp_path)`):
  - `init` creates `forge.yaml`; second `init` exits 1 and the file is unchanged.
  - `new` in a folder without `forge.yaml` exits 1 with the spec message; nothing created.
  - `new` with an invalid file exits 1 and lists the problem; nothing created.
  - `new` with a valid file: the preview is shown and generation proceeds (mock `confirm` → yes, mock `run_compile`/`check_observability` to pass, as the existing `test_cli.py` does); `forge new --name x` now fails with "No such option".
  - `new` never calls `input` (monkeypatch `builtins.input` to raise).
- [ ] **Step 2: Run** `.venv\Scripts\pytest backend/tests/test_cli.py backend/tests/test_cli_from.py -v` → expect FAIL.
- [ ] **Step 3: Implement** the changes in `cli.py` per Behavior above. Remove `from core.wizard import ...` and `ParameterSource` imports if no longer used.
- [ ] **Step 4: Run** the same command → PASS.

### Task 4: Remove the interactive wizard

**Files:**
- Delete: `backend/core/wizard.py`, `backend/tests/test_wizard.py`
- Modify: `backend/core/entity_spec.py` only if it imports from wizard (check); `CLAUDE.md` and `backend/QUICK_REFERENCE.md` mention of wizard are handled in Task 9.

**Interfaces:**
- Consumes: nothing new. Validators `validate_project_name`, `validate_group_id`, `validate_artifact_id` stay in `core/config_schema.py` and are used by `ForgeConfig`.

- [ ] **Step 1: Confirm no remaining imports** — `Grep` for `core.wizard` and `from core import wizard` across `backend/`. Expect only `cli.py` (already removed in Task 3) and the test file being deleted.
- [ ] **Step 2: Delete** `wizard.py` and `test_wizard.py`.
- [ ] **Step 3: Run** `.venv\Scripts\pytest backend/tests -q` → expect all remaining tests PASS (fix any test that imported the wizard by moving its still-relevant assertions to `test_project_config.py`).

### Task 5: Backend verification

- [ ] **Step 1:** Run `.venv\Scripts\pytest backend/tests -q` → all PASS, including `test_generation.py` (needs `mvn` on PATH; if unavailable, record that it was skipped and why).
- [ ] **Step 2:** Manual smoke: in a temp folder, run `forge init`, edit `forge.yaml` placeholders, run `forge new` with `mvn` available. Record the outcome. If Maven or Docker is not available, say so and rely on the automated tests.

---

## Frontend (`frontend/`)

### Task 6: Project-file → ForgeWebConfig builder and starter file

**Files:**
- Create: `frontend/forge_web/core/project_config.py`
- Test: `frontend/tests/test_project_config.py`

**Interfaces:**
- Consumes: `forge_web.core.config_schema.ForgeWebConfig`; PyYAML.
- Produces:
  - `CONFIG_FILENAME = "forge-web.yaml"`
  - `REQUIRED_KEYS = ("project_name", "target_path", "api_base_url")`
  - `ALLOWED_KEYS = REQUIRED_KEYS + ("template",)`
  - `build_config(path: Path) -> ForgeWebConfig` — read YAML (`safe_load`; empty file → `{}`); non-mapping top level → `ValueError`; unknown keys → `ValueError` naming them (the format is closed, mirroring the backend's `extra="forbid"`); missing/empty required keys → `ValueError` listing each; `template` defaults to `base`; `target_path` expanded and resolved; `ForgeWebConfig` `ValidationError` → `ValueError` with the same prefix `Invalid <path>:`. Non-existent file → `MissingConfigError(FileNotFoundError)`.
  - `STARTER_TEMPLATE: str` — commented YAML with `project_name: my-app`, `target_path: .`, `api_base_url: http://localhost:8080/api`, `template: base`, and comments listing `base` and `minimal`.
  - `write_starter(path: Path) -> None` — `FileExistsError` if present.

- [ ] **Step 1: Write failing tests**: complete file builds; `~` expansion; each missing required key reported; empty file reports all three; unknown key `apiBaseUrl` rejected by name; invalid `project_name` rejected; `template: minimal` honored; default `base`; starter loads and builds once placeholders are valid; `write_starter` refuses to overwrite and leaves content intact.
- [ ] **Step 2: Run** `.venv\Scripts\pytest frontend/tests/test_project_config.py -v` → FAIL.
- [ ] **Step 3: Implement** the module per Interfaces.
- [ ] **Step 4: Run** → PASS.

### Task 7: Wire `init` and file-only `new` into the frontend CLI

**Files:**
- Modify: `frontend/forge_web/cli.py` (`new` at lines ~86–179; add `init`)
- Test: `frontend/tests/test_cli.py` (update)

**Interfaces:**
- Consumes: Task 6.
- Produces: `forge-web init [--verbose]`… — `init` takes no options; `forge-web new [--verbose]`.

Behavior of `new`: missing file → spec message (`No forge-web.yaml found in <cwd>. Run "forge-web init" first.`), exit 1; `build_config` `ValueError` → `Error: …`, exit 1; print `Config: <path>` and the resolved name, target dir, API base URL, template; target dir exists → exit 1; the rest of the flow (`resolve_tree`, confirm, render, `.env` copy, validation, success message) is unchanged. Remove `collect_params` call and the `overrides` dict.

Behavior of `init`: `write_starter(cwd / "forge-web.yaml")`; errors → exit 1; success → `Created forge-web.yaml. Edit it, then run "forge-web new".`

- [ ] **Step 1: Write failing CLI tests** (CliRunner, `chdir(tmp_path)`): `init` creates file and second run fails unchanged; `new` without file exits 1 with the message; `new` with invalid file exits 1; `new` with valid file reaches the preview and proceeds (mock `confirm`, `run_build`, `run_typecheck`, `check_no_hardcoded_design_values`, `check_no_spacing_scale_width_collisions` to pass — follow the existing mocking in `test_cli.py`); `new --name x` → "No such option"; `input` is never called.
- [ ] **Step 2: Run** `.venv\Scripts\pytest frontend/tests/test_cli.py -v` → FAIL.
- [ ] **Step 3: Implement** per Behavior.
- [ ] **Step 4: Run** → PASS.

### Task 8: Remove frontend wizard and verify

**Files:**
- Delete: `frontend/forge_web/core/wizard.py`, `frontend/tests/test_wizard.py`

- [ ] **Step 1:** `Grep` for `core.wizard` in `frontend/`; expect none after Task 7.
- [ ] **Step 2:** Delete both files.
- [ ] **Step 3:** Run `.venv\Scripts\pytest frontend/tests -q` → all PASS, including `test_generation.py` (needs `npm`; if unavailable, record that it was skipped).

---

## Documentation

### Task 9: Rewrite READMEs and quick references

**Files:**
- Rewrite: `README.md` (root), `backend/README.md`, `frontend/README.md`
- Rewrite: `backend/QUICK_REFERENCE.md`, `frontend/QUICK_REFERENCE.md`
- Modify: `CONTRIBUTING.md` (remove any flag-based command examples), `CLAUDE.md` (the "Commands" and wizard/`--from` references describing removed behavior)
- Update: `backend/CHANGELOG.md`, `frontend/CHANGELOG.md` (new "Unreleased" entry: breaking change, file-only config, `init`, wizard removed)

**Content requirements (from the spec's README scope):**
- Root: what Forge is, prerequisites, install both packages, short quick start linking to each package README.
- Each package README sections in order: Prerequisites (backend: JDK 21, Maven, Docker for generated project; frontend: Node + npm), Install (editable install into `.venv`), Step-by-step guide (`init` → edit file → `new` → what is generated → next commands), Config reference (every key, required or optional, allowed values, default, one example), Templates, Troubleshooting (missing file, invalid key, folder exists, failed validation, `mvn`/`npm` not found).
- QUICK_REFERENCE: command list and config keys only, linking to the README.
- Every command and key shown must match the implementation from Tasks 1–8 — verify each against `cli.py` and the config module before saving.

- [ ] **Step 1:** Read the current READMEs and QUICK_REFERENCE files (for facts not in the spec, e.g. templates' contents and prerequisites).
- [ ] **Step 2:** Write the new files per the content requirements.
- [ ] **Step 3:** `Grep` the repo docs for `--name`, `--from`, `--group-id`, `--artifact-id`, `--api-base-url`, `wizard` → expect no matches outside CHANGELOG history lines.
- [ ] **Step 4:** Run `forge init` in a temp folder for each package and check the starter file matches what the README describes.

### Task 10: Final verification

- [ ] **Step 1:** `.venv\Scripts\pytest backend/tests frontend/tests -q` → report counts and any skipped tests with reason.
- [ ] **Step 2:** `git status` and report changed files. Do not commit.
