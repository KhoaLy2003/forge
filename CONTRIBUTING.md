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

### Adding a new template

Both packages render from `templates/_shared/` (backend) /
`forge_web/templates/_shared/` (frontend) plus a per-template exclude list.
To add a new template:

1. Create `templates/<name>/manifest.py` exporting `EXCLUDES: tuple[str, ...]`
   — glob patterns matched against the unrendered `_shared`-relative path
   (`fnmatch` semantics: a single `*` already matches across `/`, no need
   for `**`). An empty `EXCLUDES = ()` includes everything.
2. If the new template needs a *shared* file's content (not just its
   presence) to differ, add a boolean to `template_context()` (see
   `use_liquibase` in `backend/core/config_schema.py` or
   `include_data_fetching` in `frontend/forge_web/core/config_schema.py` for
   the pattern) and wrap the relevant lines in `{% if %}...{% endif %}`.
   Watch for two easy-to-miss spots: files that reference an excluded file
   by import/route (e.g. a shared `App.tsx` importing an excluded page —
   must be made conditional too, not just the excluded file itself) and
   TypeScript files under a `noUnusedLocals: true` tsconfig (an import that
   becomes unused under the new template must be made conditional as well,
   or `tsc --noEmit` fails).
3. `discover_templates()` (`core/templates.py` in each package) picks up the
   new `manifest.py` automatically — no registry to hand-edit.
4. Do **not** add the new template name to `FIELD_PROMPTS` in `core/wizard.py`
   — `--template` is deliberately not wizard-prompted (see `cli.py`'s
   `--template` default) so that existing non-interactive, flag-complete
   invocations never start blocking on a new prompt.
5. Add a manifest-sanity assertion and extend the parametrized
   `test_generation.py` — see `backend/tests/test_template_manifests.py` /
   `frontend/tests/test_template_manifests.py` for the pattern.

## Submitting a PR

1. Fork the repo and create a branch off `main`.
2. Make your change, and add/update tests so the change is covered.
3. Run the relevant test suite locally (see above) — CI will run it again on
   the PR.
4. Open a PR with a clear description of what changed and why.

## Changelog

Each package's `CHANGELOG.md` keeps a permanent `## [Unreleased]` section at
the top. If your PR changes behavior, add a bullet there — **don't** invent a
version number or date; that happens once, at release time. This keeps
concurrent PRs from fighting over "what's the next version" on the same
lines (a `merge=union` `.gitattributes` entry also lets simultaneous
`[Unreleased]` additions merge automatically in the common case).

CI (`changelog-check` in `ci.yml`) fails a PR if a package's `CHANGELOG.md`
top released-version heading doesn't match its `pyproject.toml` version — if
you see that failure, someone (possibly you) forgot to run the release
script below, or hand-edited a version heading directly.

### Cutting a release

Don't hand-edit the version heading or `pyproject.toml`'s version — run:

```bash
python scripts/prepare_release.py --package backend --version 0.3.0
```

This renames `## [Unreleased]` to `## 0.3.0 — <today>`, inserts a fresh
empty `[Unreleased]` section above it, and bumps `pyproject.toml` — all in
one atomic edit, so the two can't drift apart. Review the diff and commit/PR
it through the normal flow, same as any other change. Once merged, trigger
the `Release` workflow (`.github/workflows/release.yml`) with the matching
version.

## Reporting bugs / requesting features

Open a GitHub issue. Include the CLI (`forge` or `forge-web`), the command
you ran, and what you expected vs. what happened.
