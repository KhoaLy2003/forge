# Quick Reference

## Generate a project

```bash
.venv\Scripts\forge-web new
```

Prompts for anything not passed as a flag:

| Flag               | Prompt it skips                | Example                       |
| ------------------ | ------------------------------ | ----------------------------- |
| `--name`         | Project name                   | `my-dashboard`              |
| `--path`         | Target path (parent directory) | `C:\projects`               |
| `--api-base-url` | API base URL                   | `http://localhost:8080/api` |

Fully non-interactive example:

```bash
.venv\Scripts\forge-web new --name my-dashboard --path C:\projects --api-base-url http://localhost:8080/api
```

Mixed — only the flags you omit get prompted:

```bash
.venv\Scripts\forge-web new --name my-dashboard --path C:\projects
```

## What happens on each run

1. Collects parameters (wizard or flags)
2. Aborts immediately if `<path>\<name>` already exists — no overwrite, no merge
3. Shows a text preview of every file/folder that will be created, asks `[y/N]`
4. Writes the project and generates `.env` from your answers
5. Runs a structural check (expected files present), then `npm install && npm run build`, `tsc --noEmit`, and the design-token check
6. If any check fails, prompts to keep or delete the generated folder
7. On success, prints `cd` and `npm run dev`

## After generation

```bash
cd <generated-project>
npm run dev
```

Opens at http://localhost:5173 by default, running against **mock data** —
no backend needed to explore the dashboard or the `/components` showcase
page.

To point it at a real API instead, edit the generated project's `.env`:

```
VITE_API_MODE=true
VITE_API_BASE_URL=http://localhost:8080/api
```

## Run Forge Web's own tests

```bash
.venv\Scripts\pytest frontend/tests -v
```

`frontend/tests/test_generation.py` renders the template into a temp
directory and runs a real `npm install`, `npm run build`, `tsc --noEmit`,
and the design-token grep check — this requires `npm`/`npx` on PATH (no
Docker needed, unlike the backend generator's Maven checks).
