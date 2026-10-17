# Forge Web

Forge Web generates a ready-to-build **React + TypeScript + Vite + Tailwind v4 +
Shadcn/ui** dashboard. You describe the project in one small file,
`forge-web.yaml`, and Forge Web creates the whole app from it, checks that it
builds, and tells you the next command to run.

## Contents

1. [Prerequisites](#1-prerequisites)
2. [Install](#2-install)
3. [Step-by-step guide](#3-step-by-step-guide)
4. [`forge-web.yaml` reference](#4-forge-webyaml-reference)
5. [Templates](#5-templates)
6. [What gets generated](#6-what-gets-generated)
7. [Run the generated project](#7-run-the-generated-project)
8. [Troubleshooting](#8-troubleshooting)
9. [Development](#9-development)

---

## 1. Prerequisites

| Needed for | Tool | Notes |
|---|---|---|
| Running Forge Web | Python **3.11+** | `py --version` to check |
| Forge Web's build check | Node.js with `npm` and `npx` on `PATH` | `npm -v` to check |
| The generated app | Node.js **18+** | `node -v` to check |

The build check runs `npm install` and `npm run build` on the generated app,
then `tsc --noEmit`. This takes a few minutes the first time because npm
downloads the dependencies.

## 2. Install

Run from the repository root, in a virtual environment:

```bash
py -m venv .venv
.venv\Scripts\pip install -e "./frontend[dev]"
```

This installs the `forge-web` command into `.venv`. Check it:

```bash
.venv\Scripts\forge-web --help
```

You should see the two commands, `init` and `new`.

## 3. Step-by-step guide

Forge Web reads its settings only from `forge-web.yaml` in the folder where you
run it. There are no options to remember or type.

### Step 1 — Create the project file

Go to the folder where you want the new app to appear, then run:

```bash
cd C:\projects
forge-web init
```

Output:

```
Created C:\projects\forge-web.yaml. Edit it, then run "forge-web new".
```

`forge-web init` writes a commented starter file. It never overwrites an
existing `forge-web.yaml`; if one is already there, it stops and changes
nothing.

### Step 2 — Edit `forge-web.yaml`

```yaml
project_name: my-dashboard
target_path: C:\projects
api_base_url: http://localhost:8080/api
template: base
```

See [section 4](#4-forge-webyaml-reference) for what each key means.

### Step 3 — Generate

```bash
forge-web new
```

Forge Web then:

1. Reads and validates `forge-web.yaml`. Every problem is listed at once, and
   nothing is written if any exist.
2. Prints the values it will use:

   ```
   Config:   C:\projects\forge-web.yaml
   Project:  my-dashboard
   Target:   C:\projects\my-dashboard
   API URL:  http://localhost:8080/api
   Template: base
   ```

3. Shows a preview of every file and folder it will create, and asks
   `Generate this project? [y/N]`. Answer `n` to cancel without writing
   anything.
4. Writes the app, and copies `.env.example` to `.env` so the app is ready to
   run with your API URL.
5. Runs the checks: expected files present, `npm install && npm run build`,
   `tsc --noEmit`, and two source checks (no hardcoded colors outside
   `theme.css`, and no spacing/width collisions). If a check fails, Forge Web
   explains why and asks whether to delete the half-built folder.

On success it prints:

```
Project generated successfully!
cd C:\projects\my-dashboard
npm run dev
```

### Step 4 — Run it

Follow [section 7](#7-run-the-generated-project).

### Changing an app after generation

`forge-web new` never merges into or overwrites an existing folder. To
regenerate, delete or rename the existing app folder first, or change
`project_name` in `forge-web.yaml`.

---

## 4. `forge-web.yaml` reference

| Key | Required | Default | Allowed values | Meaning |
|---|---|---|---|---|
| `project_name` | yes | — | lowercase letters and digits, single hyphens between segments; starts with a letter; no leading, trailing or doubled hyphens | Name of the app folder. The display name is derived from it (`my-dashboard` → `My Dashboard`). |
| `target_path` | yes | — | any path; `~` and relative paths are resolved | Folder the app folder is created in. `.` means the folder containing `forge-web.yaml`. |
| `api_base_url` | yes | — | any non-empty string, usually `http(s)://host:port/path` | Backend API the app calls. Written into the app's `.env` as `VITE_API_BASE_URL`. |
| `template` | no | `base` | `base`, `minimal` | Which template to generate. See [section 5](#5-templates). |

Rules:

- Unknown keys are an error. A misspelled key (such as `apiBaseUrl`) is
  reported by name rather than silently ignored.
- Windows paths work as written, for example `target_path: C:\projects`.
- A value that is empty (`api_base_url:` with nothing after it) counts as
  missing.

---

## 5. Templates

| | `base` (default) | `minimal` |
|---|---|---|
| Routing, theme tokens, static pages (404, error, loading, empty state) | included | included |
| Shadcn component set (16 components) and the `/components` showcase | included | included |
| Sample CRUD dashboard (`/`) | included | excluded |
| Mock/real API client, TanStack Query hooks | included | excluded |
| `zod` and `@hookform/resolvers` dependencies | included | excluded |
| `react-hook-form` and `@tanstack/react-table` dependencies | included | included — the showcase page's live demo needs both |

Use `minimal` when you want the component set and design tokens without the
sample CRUD app and API client.

---

## 6. What gets generated

- **Stack:** React 18, TypeScript, Vite (single-page app), React Router,
  Tailwind v4, Shadcn/ui.
- **Components:** button, input, card, table, data-table, tabs, select,
  dialog, alert-dialog, dropdown-menu, toast, form, avatar, badge, skeleton.
  Every color, font, spacing, radius and shadow value comes from
  `src/styles/theme.css`, which is seeded from `docs/DESIGN.md`. Nothing is
  hardcoded in components.
- **Pages:** the `/components` showcase, and in `base` the sample dashboard
  (`/`) with its CRUD flow, plus 404, error, loading and empty-state pages.
- **API:** `.env` starts with `VITE_API_MODE=false`, so the app runs against
  mock data with no backend. Set `VITE_API_MODE=true` to call the API at
  `VITE_API_BASE_URL`. `.env.example` documents each variable.
- **Tests:** Vitest and React Testing Library, with an 80% line-coverage gate
  (`npm run test:coverage`). `npm test` runs the suite without the gate.
- **CI:** `.github/workflows/ci.yml` runs the build, the coverage-gated tests,
  CodeQL, a Trivy scan, PR dependency review and zizmor. The dependency-review
  job needs Dependabot and vulnerability alerts enabled on your GitHub repo.

---

## 7. Run the generated project

```bash
cd C:\projects\my-dashboard
npm install
npm run dev
```

Open the address Vite prints (by default `http://localhost:5173`). The app
starts on mock data (`VITE_API_MODE=false` in `.env`). To call your backend,
set `VITE_API_MODE=true` and check `VITE_API_BASE_URL` in `.env`.

Useful scripts:

| Command | What it does |
|---|---|
| `npm run dev` | Dev server with hot reload |
| `npm run build` | Typecheck and production build |
| `npm test` | Run the test suite |
| `npm run test:coverage` | Run the tests with the 80% coverage gate |

---

## 8. Troubleshooting

| Message | Cause | Fix |
|---|---|---|
| `No forge-web.yaml found in … Run "forge-web init" first.` | You ran `forge-web new` in a folder without the file | `cd` to the folder with `forge-web.yaml`, or run `forge-web init` there |
| `Invalid …forge-web.yaml:` followed by `- key: missing` | A required key is absent or empty | Set the key listed |
| `- <key>: unknown key …` | Misspelled or unsupported key | Fix the spelling; see [section 4](#4-forge-webyaml-reference) |
| `Error: target directory already exists` | `target_path/project_name` already exists | Delete or rename that folder, or change `project_name` |
| `Error: <file> already exists` on `init` | `forge-web.yaml` is already there | Keep it, or delete it and run `init` again |
| `Validation failed: npm executable not found on PATH` | Node.js/npm is not installed or not on `PATH` | Install Node.js 18+ and reopen the terminal |
| `Validation failed: npx executable not found on PATH` | `npx` is not on `PATH` | Reinstall Node.js, which provides `npx` |
| `Validation failed: npm install failed` or `npm run build failed` | The generated app does not install or build | Read the npm output under the message; delete the folder and regenerate after fixing the cause (a common cause is a blocked network) |
| `Validation failed: npm install timed out after …` (or `npm run build`) | The step took longer than the limit | Check your network or machine load, then delete the folder and regenerate |
| `Validation failed: tsc --noEmit failed` | The generated code has a type error | Read the output under the message; delete the folder and regenerate after fixing the cause |
| `Validation failed: Hardcoded design values found outside theme.css` | A hex color or pixel value was hardcoded outside `theme.css` | Read the file list under the message; regenerate after fixing the cause |
| `Validation failed: Width/height utility collides with a spacing-scale token name` | A width or height class name clashes with a spacing token name | Read the list under the message; regenerate after fixing the cause |

---

## 9. Development

Run from the repository root:

```bash
.venv\Scripts\pytest frontend/tests -v
```

`npm` and `npx` must be on `PATH` for `frontend/tests/test_generation.py` and
the build and typecheck checks, because both run against a real generated app.

Design specs and implementation plans live under
[`../docs/superpowers/specs/`](../docs/superpowers/specs/) and
[`../docs/superpowers/plans/`](../docs/superpowers/plans/). Version history is
in [CHANGELOG.md](CHANGELOG.md); a command and key cheat sheet is in
[QUICK_REFERENCE.md](QUICK_REFERENCE.md).
