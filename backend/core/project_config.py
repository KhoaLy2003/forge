"""Build a ForgeConfig from the ``forge.yaml`` in the working directory, and write the starter file for ``forge init``."""

from pathlib import Path

from pydantic import ValidationError

from core.config_schema import ForgeConfig
from core.entity_spec import load_forge_yaml

CONFIG_FILENAME = "forge.yaml"
REQUIRED_KEYS = ("project_name", "target_path", "group_id", "artifact_id")

STARTER_TEMPLATE = """\
# Forge project file. Edit the values below, then run:  forge new
# Every key is read from this file; no command-line options are needed.

# Name of the project folder to create (lowercase letters, digits, hyphens; starts with a letter).
project_name: my-service

# Parent folder the project folder is created in. "." means the current folder.
target_path: .

# Maven group id, dot-separated lowercase segments (e.g. com.example).
group_id: com.example

# Maven artifact id (lowercase letters, digits, hyphens; starts with a letter).
artifact_id: my-service

# Template to generate: base-layered (full reference project) or minimal (no Liquibase, no notification module).
template: base-layered

# Optional. Uncomment to generate your own entities (CRUD, relations) instead of the sample "Example" entity.
# Requires template: base-layered.
#
# entities:
#   Customer:
#     fields:
#       name:
#         type: string
#         length: 120
#         required: true
#       email:
#         type: string
#         unique: true
#     relations:
#       invoices:
#         type: one-to-many
#         target: Invoice
#         mappedBy: customer
#   Invoice:
#     fields:
#       total:
#         type: decimal
#         precision: 10
#         scale: 2
#         required: true
#     relations:
#       customer:
#         type: many-to-one
#         target: Customer
#         required: true
"""


class MissingConfigError(FileNotFoundError):
    """Raised when the project file does not exist."""


def build_config(path: Path) -> ForgeConfig:
    """Load and validate ``path`` and return the ForgeConfig it describes.

    Raises ``MissingConfigError`` if the file does not exist, and ``ValueError`` (prefixed with the file path,
    listing every problem) if it is invalid.
    """
    path = Path(path)
    if not path.exists():
        raise MissingConfigError(path)
    project_file = load_forge_yaml(path)

    values = {key: getattr(project_file, key) for key in REQUIRED_KEYS}
    missing = [key for key, value in values.items() if value in (None, "")]
    if missing:
        lines = "\n".join(f"  - {key}: missing" for key in missing)
        raise ValueError(f"Invalid {path}:\n{lines}")

    try:
        return ForgeConfig(
            project_name=str(values["project_name"]),
            target_path=Path(values["target_path"]).expanduser().resolve(),
            group_id=str(values["group_id"]),
            artifact_id=str(values["artifact_id"]),
            template=project_file.template or "base-layered",
            entities=project_file.entities,
        )
    except ValidationError as exc:
        details = "\n".join(
            f"  - {'.'.join(str(p) for p in err['loc']) or '<root>'}: {err['msg'].removeprefix('Value error, ')}"
            for err in exc.errors()
        )
        raise ValueError(f"Invalid {path}:\n{details}") from exc


def write_starter(path: Path) -> None:
    """Write ``STARTER_TEMPLATE`` to ``path``. Raises ``FileExistsError`` (naming the path) if it already exists."""
    path = Path(path)
    if path.exists():
        raise FileExistsError(f"{path} already exists; delete or rename it first")
    path.write_text(STARTER_TEMPLATE, encoding="utf-8")
