# Forge

[![CI](https://github.com/KhoaLy2003/forge/actions/workflows/ci.yml/badge.svg)](https://github.com/KhoaLy2003/forge/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Forge is two command-line tools that generate a complete, ready-to-build
project, so starting new work is faster than copying an old project by hand.

| Tool                                | Command       | Generates                                        | Guide                                   |
| ----------------------------------- | ------------- | ------------------------------------------------ | --------------------------------------- |
| **Forge** (`backend/`)      | `forge`     | Java 21 + Spring Boot 4 + PostgreSQL (Maven)     | [backend/README.md](backend/README.md)   |
| **Forge Web** (`frontend/`) | `forge-web` | React + TypeScript + Vite + Tailwind + Shadcn/ui | [frontend/README.md](frontend/README.md) |

Both work the same way. You edit one small file, and the command generates
the project from it:

1. `forge init` (or `forge-web init`) writes a commented config file,
   `forge.yaml` or `forge-web.yaml`, into the current folder.
2. You edit the file.
3. `forge new` (or `forge-web new`) reads the file, previews the files, asks
   for confirmation, generates the project, and checks that it builds.

There are no options to remember or copy-paste.

## Prerequisites

- **Python 3.11 or newer** (both tools)
- **Backend:** Maven 3.9+ and JDK 21 for the generated project; Docker to run it
- **Frontend:** Node.js 18+ with `npm` and `npx`

Each package README lists the exact requirements and how to check them.

## Install

Run from the repository root. Use one virtual environment for both tools:

```bash
py -m venv .venv
.venv\Scripts\pip install -e "./backend[dev]"
.venv\Scripts\pip install -e "./frontend[dev]"
```

Check both:

```bash
.venv\Scripts\forge --help
.venv\Scripts\forge-web --help
```

## Quick start

Backend service:

```bash
cd C:\projects
forge init                  # writes forge.yaml
# edit forge.yaml: project_name, group_id, artifact_id, ...
forge new                   # generates C:\projects\<project_name>
```

Frontend app:

```bash
cd C:\projects
forge-web init              # writes forge-web.yaml
# edit forge-web.yaml: project_name, api_base_url, ...
forge-web new               # generates C:\projects\<project_name>
```

For the full walkthrough, the field reference and troubleshooting, see
[backend/README.md](backend/README.md) or [frontend/README.md](frontend/README.md).

## Shared docs

- [`docs/DESIGN.md`](docs/DESIGN.md): the design-token system the frontend's
  generated theme is seeded from.
- [`docs/superpowers/specs/`](docs/superpowers/specs/) and
  [`docs/superpowers/plans/`](docs/superpowers/plans/): design specs and
  implementation plans for both packages.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for dev setup, how to run each
package's tests, and PR expectations. [CLAUDE.md](CLAUDE.md) has the
architecture behind both tools.

## License

Forge is licensed under the [MIT License](LICENSE).
