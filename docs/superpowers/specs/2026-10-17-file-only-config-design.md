# File-Only Project Config and `init` Command — Design

Status: draft, awaiting approval. No code has been written.

## Intent

Creating a project today means typing a long `forge new` command with many flags, and a copy-paste mistake can silently produce a project with inconsistent values. Make a small config file the only source of project parameters. The user runs `init` once to get a commented starter file, edits it, and then runs `new` with no arguments.

## Goals

- `forge new` takes no parameters. It reads the config file from the current folder.
- `forge init` writes a starter config file, commented field by field.
- Both packages work the same way: `backend/` (Forge) and `frontend/` (Forge Web).
- The READMEs are rewritten to match: setup, install, a step-by-step guide, and a field reference for each config file.

## Non-goals

- No change to what gets generated (templates, validation checks, entity model rules).
- No new templates.
- No config-file-driven template variables beyond the fields listed below.

## Anti-goals

- Two places that set the same value (a flag and a file). A flag must never silently override the file.
- A `new` run that prompts for missing values. Missing or invalid fields are reported, not asked for.

## Decisions

### Config file names (my call)

- Backend: `forge.yaml` (already the name used by `--from`, so existing files keep working).
- Frontend: `forge-web.yaml`. Both CLIs may run from the same folder, and a shared name would be ambiguous.

### Backend `forge.yaml`

Same schema as today's `forge.yaml`, with the project fields now expected in the file:

- `project_name`, `target_path`, `group_id`, `artifact_id` — required.
- `template` — optional, default `base-layered`.
- `entities` — optional; same format and validation as today (see `core/entity_spec.py`).

Validation errors are reported with the key path, all at once, and nothing is written.

### Frontend `forge-web.yaml`

- `project_name`, `target_path`, `api_base_url` — required.
- `template` — optional, default `base`.

### `forge init`

- Writes a starter file to the current folder with comments explaining each field and its allowed values. Backend's starter also includes a commented-out example entity block.
- Refuses to overwrite an existing config file (exit 1, message names the file). Overwriting needs the user to delete or rename the file first.
- Writes only the config file. Creates no project folder.

### `forge new` behaviour

1. If the config file is missing, print `No forge.yaml found in <cwd>. Run "forge init" first.` and exit 1.
2. Load and validate the file (same validation path as today). On error, print every problem and exit 1 before anything is written.
3. Print the resolved values (name, target path, group id, artifact id, template) so the user can see what will be generated.
4. Existing preview, confirm, render, and validate steps run unchanged. The target-folder-exists check stays.

### What is removed

- Backend: `--name`, `--path`, `--group-id`, `--artifact-id`, `--template`, `--from`.
- Frontend: `--name`, `--path`, `--api-base-url`, `--template`.
- Backend: the interactive entity wizard step and the "Save the model as forge.yaml?" prompt. Entities are written in the file (by hand, or by editing the starter from `init`). The wizard prompts in `core/wizard.py` that exist only for this are removed.
- `--verbose` stays on both commands, since it does not carry project data.

### Breaking change

Existing scripts and CI invocations that use flags will stop working. The CHANGELOG entry for each package must say so, and the version bump is a minor-version bump in pre-1.0 terms (to be confirmed at release time).

## Parts of the code affected

- `backend/cli.py`: `new` and new `init` command; remove flag and `--from` precedence logic.
- `backend/core/wizard.py`: the interactive parameter collection goes away; `needs_prompt`, `collect_params`, `collect_entities`, `save_forge_yaml` are candidates for removal. The starter-file writer is new.
- `backend/core/entity_spec.py`: reused as-is for loading; add a loader entry point for the project fields.
- `backend/core/config_schema.py`: reused; constructed from the file contents instead of overrides.
- `frontend/forge_web/cli.py`: same shape for `new` and `init`.
- `frontend/forge_web/core/config_schema.py`: reused; a new file loader is added.
- Tests: `tests/test_cli_from.py` and the wizard tests are rewritten around file-only behaviour. End-to-end tests (`test_generation.py`) keep building a config directly and are not affected.
- Docs: both package READMEs, both QUICK_REFERENCE files, the root README, both CHANGELOGs, CONTRIBUTING.md if it shows commands.

## README scope

- Root README: what Forge is, prerequisites, install for both packages, a one-screen quick start pointing to each package.
- Each package README:
  1. Prerequisites (Python, JDK 21 + Maven + Docker for backend; Node + npm for frontend).
  2. Install (editable install into a venv).
  3. Step-by-step guide: `init`, edit the file, `new`, what the output contains, next commands.
  4. Field reference for the config file, with allowed values and defaults.
  5. Templates (what each template includes).
  6. Troubleshooting (missing file, invalid field, existing folder, failed validation).
- QUICK_REFERENCE files shrink to the command list and config fields, linking to the README for detail.

## Open questions (for the approver)

1. Are the config file names right (`forge.yaml` for backend, `forge-web.yaml` for frontend)?
2. Dropping the interactive entity step: acceptable, or should entities stay wizard-driven through `init`?
3. Is a breaking change with a minor version bump acceptable, or should the bump be major?
