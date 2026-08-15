# Contributing to Forge

Thanks for considering a contribution. Forge is a monorepo of two
independent scaffolding CLIs — see [CLAUDE.md](CLAUDE.md) for the full
architecture rundown before making non-trivial changes.

## Dev setup

Both packages install editable into a single venv:

```bash
py -m venv .venv
.venv\Scripts\pip install -e "./backend[dev]"
.venv\Scripts\pip install -e "./frontend[dev]"
```

## Running tests

```bash
# backend (Forge) — requires mvn on PATH; test_generation.py shells out to a
# real `mvn compile` against a generated project
.venv\Scripts\pytest backend/tests -v

# frontend (Forge Web) — requires npm/npx on PATH; test_generation.py runs a
# real `npm install`, `npm run build`, and `npx tsc --noEmit`
.venv\Scripts\pytest frontend/tests -v

# a single test
.venv\Scripts\pytest backend/tests/test_renderer.py::test_name -v
```

CI (`.github/workflows/ci.yml`) runs the same suite on every push and PR to
`main`.

## Making changes

- Follow the existing module shape in each package's `core/` — see
  [CLAUDE.md](CLAUDE.md) for what each module owns.
- If you add a template variable, it must be added to the corresponding
  `ForgeConfig`/`ForgeWebConfig.template_context()` — both packages use
  `jinja2.StrictUndefined`, so an unregistered variable fails the render
  immediately.
- Keep changes to `backend/` and `frontend/` in separate commits/PRs where
  possible; the two packages share no code.

## Submitting a PR

1. Fork the repo and create a branch off `main`.
2. Make your change, and add/update tests so the change is covered.
3. Run the relevant test suite locally (see above) — CI will run it again on
   the PR.
4. Open a PR with a clear description of what changed and why.

## Reporting bugs / requesting features

Open a GitHub issue. Include the CLI (`forge` or `forge-web`), the command
you ran, and what you expected vs. what happened.
