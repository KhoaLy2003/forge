# Quick Reference (Forge Web, frontend)

Full guide: [README.md](README.md).

## Commands

| Command | What it does |
|---|---|
| `forge-web init` | Writes a commented `forge-web.yaml` into the current folder. Refuses to overwrite. |
| `forge-web new` | Generates the app described by `./forge-web.yaml`. No options. |
| `forge-web new --verbose` | Same, with full tracebacks on failure. |

```bash
.venv\Scripts\forge-web init
# edit forge-web.yaml
.venv\Scripts\forge-web new
```

## `forge-web.yaml`

```yaml
project_name: my-dashboard                    # required; lowercase, digits, single hyphens; starts with a letter
target_path: C:\projects                      # required; parent folder for the app
api_base_url: http://localhost:8080/api       # required; written to .env as VITE_API_BASE_URL
template: base                                # optional; base (default) or minimal
```

Unknown keys are an error. Relative and `~` paths in `target_path` are resolved.

## Templates

| Template | Use it for |
|---|---|
| `base` (default) | Full app: sample CRUD dashboard, API client, TanStack Query, forms |
| `minimal` | Component set, design tokens and `/components` showcase only |

## What `forge-web new` does

1. Reads and validates `forge-web.yaml`. Problems are listed together; nothing is written.
2. Prints the resolved values.
3. Aborts if `<target_path>\<project_name>` already exists. No overwrite, no merge.
4. Shows the file tree and asks `Generate this project? [y/N]`.
5. Writes the app and copies `.env.example` to `.env`.
6. Checks: expected files, `npm install && npm run build`, `tsc --noEmit`, the design-token check, and the spacing/width collision check.
7. On a failed check, asks whether to delete the generated folder.
8. On success, prints `cd` and `npm run dev`.

## After generation

```bash
cd <generated-app>
npm install
npm run dev
```

Opens at http://localhost:5173 by default. `.env` starts with
`VITE_API_MODE=false`, so the app runs against **mock data** and needs no
backend. To use a real API, set in `.env`:

```
VITE_API_MODE=true
VITE_API_BASE_URL=http://localhost:8080/api
```

| Script | What it does |
|---|---|
| `npm run dev` | Dev server |
| `npm run build` | Typecheck and production build |
| `npm test` | Tests |
| `npm run test:coverage` | Tests with the 80% coverage gate |

## Forge Web's own tests

```bash
.venv\Scripts\pytest frontend/tests -v
```

Needs `npm` and `npx` on `PATH` for the generation tests, which run a real
`npm install`, build and typecheck against a generated app. Docker is not needed.
