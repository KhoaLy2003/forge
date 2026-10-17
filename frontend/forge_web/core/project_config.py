"""Build a ForgeWebConfig from the ``forge-web.yaml`` in the working directory, and write the starter file for ``forge-web init``."""

from pathlib import Path

import yaml
from pydantic import ValidationError

from forge_web.core.config_schema import ForgeWebConfig

CONFIG_FILENAME = "forge-web.yaml"
REQUIRED_KEYS = ("project_name", "target_path", "api_base_url")
ALLOWED_KEYS = REQUIRED_KEYS + ("template",)

STARTER_TEMPLATE = """\
# Forge Web project file. Edit the values below, then run:  forge-web new
# Every key is read from this file; no command-line options are needed.

# Name of the project folder to create (lowercase letters, digits, hyphens; starts with a letter).
project_name: my-app

# Parent folder the project folder is created in. "." means the current folder.
target_path: .

# Base URL of the backend API the generated app calls (sets VITE_API_BASE_URL in .env).
api_base_url: http://localhost:8080/api

# Template to generate: base (full sample dashboard and API client) or minimal (no sample CRUD dashboard or API client).
template: base
"""


class MissingConfigError(FileNotFoundError):
    """Raised when the project file does not exist."""


def _invalid(path: Path, lines: list[str]) -> ValueError:
    return ValueError(f"Invalid {path}:\n" + "\n".join(f"  - {line}" for line in lines))


def build_config(path: Path) -> ForgeWebConfig:
    """Load and validate ``path`` and return the ForgeWebConfig it describes.

    Raises ``MissingConfigError`` if the file does not exist, and ``ValueError`` (prefixed with the file path,
    listing every problem) if it is invalid. Unknown keys are rejected, so a typo cannot be silently ignored.
    """
    path = Path(path)
    if not path.exists():
        raise MissingConfigError(path)
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in {path}: {exc}") from exc
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError(f"Invalid {path}: top level must be a mapping, got {type(data).__name__}")

    unknown = [key for key in data if key not in ALLOWED_KEYS]
    if unknown:
        raise _invalid(path, [f"{key}: unknown key (allowed: {', '.join(ALLOWED_KEYS)})" for key in unknown])

    missing = [key for key in REQUIRED_KEYS if data.get(key) in (None, "")]
    if missing:
        raise _invalid(path, [f"{key}: missing" for key in missing])

    try:
        return ForgeWebConfig(
            project_name=str(data["project_name"]),
            target_path=Path(str(data["target_path"])).expanduser().resolve(),
            api_base_url=str(data["api_base_url"]),
            template=str(data.get("template") or "base"),
        )
    except ValidationError as exc:
        details = [
            f"{'.'.join(str(p) for p in err['loc']) or '<root>'}: {err['msg'].removeprefix('Value error, ')}"
            for err in exc.errors()
        ]
        raise _invalid(path, details) from exc


def write_starter(path: Path) -> None:
    """Write ``STARTER_TEMPLATE`` to ``path``. Raises ``FileExistsError`` (naming the path) if it already exists."""
    path = Path(path)
    if path.exists():
        raise FileExistsError(f"{path} already exists; delete or rename it first")
    path.write_text(STARTER_TEMPLATE, encoding="utf-8")
