# Forge

Two scaffolding CLIs that generate a ready-to-build project instead of a
bare skeleton, so starting new work is faster than copying an old project
by hand.

- **[`backend/`](backend/README.md)** — Forge: Java 21 + Spring Boot 4 +
  PostgreSQL project generator.
- **`frontend/`** — Forge Web: React + TypeScript + Vite + Shadcn project
  generator. Design finished (see
  [`docs/superpowers/specs/2026-08-14-frontend-generator-design.md`](docs/superpowers/specs/2026-08-14-frontend-generator-design.md)),
  implementation not yet started.

Both share the same wizard → preview → render → validate pipeline shape
and `core/` module layout — see [CLAUDE.md](CLAUDE.md) for the full
architecture rundown.

## Setup

```bash
py -m venv .venv
.venv\Scripts\pip install -e "./backend[dev]"
```

See each package's own README for usage.

## Shared docs

- [`docs/DESIGN.md`](docs/DESIGN.md) — the design-token system `frontend/`'s
  generated theme is seeded from.
- `docs/superpowers/specs/`, `docs/superpowers/plans/` — design specs and
  implementation plans for both packages.
