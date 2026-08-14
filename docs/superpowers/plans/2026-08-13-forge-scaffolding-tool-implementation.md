# Forge Scaffolding Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Forge, a Python CLI that generates a working Maven + Spring Boot 4 + Java 21 + PostgreSQL project from a single base-layered template, with an interactive wizard, a tree preview before writing, and structural + compile validation after.

**Architecture:** A Typer CLI (`cli.py`) wires together small, independently-testable core modules — `config_schema` (Pydantic parameter model), `wizard` (interactive prompts), `renderer` (custom Jinja2 tree renderer, applied to both file/folder names and contents), `tree_preview` (text tree + y/n confirm), `progress` (status printer), and `validator` (structural + `mvn compile` checks) — operating on a single template tree at `templates/base-layered/`.

**Tech Stack:** Python 3.11+, Typer, Jinja2, Pydantic v2, pytest. Generated projects: Java 21, Spring Boot 4, Maven, Liquibase, PostgreSQL via docker-compose.

## Global Constraints

- Java version: 21 (fixed constant in generated projects, not a wizard parameter)
- Spring Boot version: 4 (fixed constant, not a wizard parameter)
- Build tool: Maven only — no Gradle support in v1
- Package structure: pure layered (`controller/`, `service/`, `repository/`, `entity/`) — no hexagonal/DDD, no package-by-feature in v1
- DB migration tool: Liquibase only
- Exactly one template in v1: `base-layered` — no feature-module system (Kafka, Redis, security, testcontainers)
- Exactly one example entity shipped, full CRUD stack — no wizard-driven multi-entity generation
- If the target directory already exists, abort immediately with a clear error before any writes — no merge, no `--force`, no overwrite prompt
- On validation failure (structural or compile), prompt the user to keep or delete the generated folder — never decide automatically
- Validation command is `mvn compile` only — not `package`/`install`
- Parameter input: interactive wizard by default; CLI flags skip individual prompts
- Templating engine: custom Jinja2 renderer (not Cookiecutter/Copier)

**Note on `java-spring-boot` skill conventions:** the generated example entity in
Task 7 deliberately does **not** follow this org's `java-spring-boot` skill
standards (UUID+BaseEntity, Lombok, DTOs/mappers, `ApiResponse<T>` wrapper,
`GlobalExceptionHandler`, `/api/v1` versioning, Liquibase formatted-SQL
migrations). This was a reviewed and confirmed decision: v1's job is to prove
the scaffold boots and compiles, not to be a production-grade feature
template. Those conventions are guidance for what users add to their own
feature code after generation, not for Forge's bootstrap example.

---

## Task 0: Environment & Project Setup

**Files:**
- Create: `pyproject.toml`
- Create: `tests/test_sanity.py`
- Create: `.gitignore` (repo root, for the Forge tool's own repo — distinct from the generated-project `.gitignore` template in Task 7)

**Interfaces:**
- Consumes: nothing
- Produces: an installable `forge` package (modules `core.*`, `cli`) and a working pytest harness that every later task's tests run under

- [ ] **Step 1: Verify required tools are on PATH**

Run:
```bash
py --version
mvn --version
docker --version
```
Expected: all three print version info without error. `py` should report Python 3.11 or later. If any command fails, stop and report to the user — do not proceed until all three are available.

- [ ] **Step 2: Create `pyproject.toml`**

```toml
[project]
name = "forge"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "typer>=0.12",
    "jinja2>=3.1",
    "pydantic>=2.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[project.scripts]
forge = "cli:main"

[tool.setuptools]
py-modules = ["cli"]
packages = ["core"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"
```

- [ ] **Step 3: Create root `.gitignore` for the Forge tool's own repo**

```
.venv/
__pycache__/
*.pyc
.pytest_cache/
*.egg-info/
```

- [ ] **Step 4: Create venv and install in editable/dev mode**

Run:
```bash
py -m venv .venv
.venv\Scripts\pip install -e ".[dev]"
```
Expected: installs without error (this will fail until Step 2's `pyproject.toml` exists — run this after Step 2).

- [ ] **Step 5: Write the sanity test**

```python
# tests/test_sanity.py
def test_pytest_runs():
    assert True
```

- [ ] **Step 6: Run the test suite to confirm the harness works**

Run: `.venv\Scripts\pytest -v`
Expected: `tests/test_sanity.py::test_pytest_runs PASSED`, 1 passed.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml .gitignore tests/test_sanity.py
git commit -m "chore: set up Python project scaffolding and test harness"
```

---

## Task 1: Config Schema

**Files:**
- Create: `core/__init__.py` (empty)
- Create: `core/config_schema.py`
- Test: `tests/test_config_schema.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `ForgeConfig` (Pydantic `BaseModel`) with fields `project_name: str`, `target_path: Path`, `group_id: str`, `artifact_id: str`
  - `ForgeConfig.target_dir -> Path` (property: `target_path / project_name`)
  - `ForgeConfig.base_package -> str` (property)
  - `ForgeConfig.package_path -> str` (property)
  - `ForgeConfig.app_class_name -> str` (property, PascalCase, no "Application" suffix)
  - `ForgeConfig.template_context() -> dict` — keys: `project_name`, `group_id`, `artifact_id`, `base_package`, `package_path`, `app_class_name`
  - Module-level functions `validate_project_name(value: str) -> str`, `validate_group_id(value: str) -> str`, `validate_artifact_id(value: str) -> str` — each raises `ValueError` with a human-readable message on invalid input, otherwise returns the value unchanged. These are used both as Pydantic field validators here and directly by `wizard.py` (Task 6) for per-field reprompt loops.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_config_schema.py
from pathlib import Path

import pytest
from pydantic import ValidationError

from core.config_schema import (
    ForgeConfig,
    validate_artifact_id,
    validate_group_id,
    validate_project_name,
)


def make_config(**overrides):
    values = dict(
        project_name="demo-service",
        target_path=Path("/tmp/out"),
        group_id="com.example",
        artifact_id="demo-service",
    )
    values.update(overrides)
    return ForgeConfig(**values)


def test_valid_config_accepted():
    config = make_config()
    assert config.project_name == "demo-service"


def test_target_dir_is_target_path_joined_with_project_name():
    config = make_config()
    assert config.target_dir == Path("/tmp/out/demo-service")


def test_base_package_strips_hyphens_from_artifact_id():
    config = make_config(group_id="com.example", artifact_id="demo-service")
    assert config.base_package == "com.example.demoservice"


def test_package_path_replaces_dots_with_slashes():
    config = make_config(group_id="com.example", artifact_id="demo-service")
    assert config.package_path == "com/example/demoservice"


def test_app_class_name_is_pascal_case_without_application_suffix():
    config = make_config(artifact_id="demo-service")
    assert config.app_class_name == "DemoService"


def test_template_context_has_expected_keys():
    config = make_config()
    context = config.template_context()
    assert set(context) == {
        "project_name",
        "group_id",
        "artifact_id",
        "base_package",
        "package_path",
        "app_class_name",
    }


def test_invalid_project_name_rejected():
    with pytest.raises(ValidationError):
        make_config(project_name="Not_Valid!")


def test_invalid_group_id_rejected():
    with pytest.raises(ValidationError):
        make_config(group_id="Com.Example")


def test_invalid_artifact_id_rejected():
    with pytest.raises(ValidationError):
        make_config(artifact_id="Not Valid")


def test_validate_project_name_raises_value_error_with_message():
    with pytest.raises(ValueError, match="lowercase"):
        validate_project_name("Bad Name")


def test_validate_group_id_raises_value_error_with_message():
    with pytest.raises(ValueError, match="dot-separated"):
        validate_group_id("BAD")


def test_validate_artifact_id_raises_value_error_with_message():
    with pytest.raises(ValueError, match="lowercase"):
        validate_artifact_id("Bad Name")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\pytest tests/test_config_schema.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.config_schema'` (or `core` package doesn't exist yet).

- [ ] **Step 3: Write `core/__init__.py`**

```python
```
(empty file — makes `core` a package)

- [ ] **Step 4: Write `core/config_schema.py`**

```python
import re
from pathlib import Path

from pydantic import BaseModel, field_validator

PROJECT_NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")
GROUP_ID_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$")
ARTIFACT_ID_RE = re.compile(r"^[a-z][a-z0-9-]*$")


def validate_project_name(value: str) -> str:
    if not PROJECT_NAME_RE.match(value):
        raise ValueError(
            "must be lowercase letters, digits, or hyphens, starting with a letter"
        )
    return value


def validate_group_id(value: str) -> str:
    if not GROUP_ID_RE.match(value):
        raise ValueError(
            "must be dot-separated lowercase segments, e.g. com.example"
        )
    return value


def validate_artifact_id(value: str) -> str:
    if not ARTIFACT_ID_RE.match(value):
        raise ValueError(
            "must be lowercase letters, digits, or hyphens, starting with a letter"
        )
    return value


class ForgeConfig(BaseModel):
    project_name: str
    target_path: Path
    group_id: str
    artifact_id: str

    @field_validator("project_name")
    @classmethod
    def _check_project_name(cls, v: str) -> str:
        return validate_project_name(v)

    @field_validator("group_id")
    @classmethod
    def _check_group_id(cls, v: str) -> str:
        return validate_group_id(v)

    @field_validator("artifact_id")
    @classmethod
    def _check_artifact_id(cls, v: str) -> str:
        return validate_artifact_id(v)

    @property
    def target_dir(self) -> Path:
        return self.target_path / self.project_name

    @property
    def base_package(self) -> str:
        return f"{self.group_id}.{self.artifact_id.replace('-', '')}"

    @property
    def package_path(self) -> str:
        return self.base_package.replace(".", "/")

    @property
    def app_class_name(self) -> str:
        return "".join(part.capitalize() for part in self.artifact_id.split("-"))

    def template_context(self) -> dict:
        return {
            "project_name": self.project_name,
            "group_id": self.group_id,
            "artifact_id": self.artifact_id,
            "base_package": self.base_package,
            "package_path": self.package_path,
            "app_class_name": self.app_class_name,
        }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv\Scripts\pytest tests/test_config_schema.py -v`
Expected: all 12 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add core/__init__.py core/config_schema.py tests/test_config_schema.py
git commit -m "feat: add ForgeConfig parameter schema with validation"
```

---

## Task 2: Renderer

**Files:**
- Create: `core/renderer.py`
- Test: `tests/test_renderer.py`

**Interfaces:**
- Consumes: a `context: dict` shaped like `ForgeConfig.template_context()` output (Task 1), but works with any dict for its own unit tests
- Produces:
  - `TargetExistsError(Exception)`
  - `resolve_tree(template_dir: Path, context: dict) -> list[Path]` — sorted list of rendered relative output paths, no filesystem writes
  - `render_tree(template_dir: Path, target_dir: Path, context: dict) -> None` — writes the rendered tree to `target_dir`; raises `TargetExistsError` if `target_dir` already exists, before writing anything

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_renderer.py
from pathlib import Path

import pytest

from core.renderer import TargetExistsError, render_tree, resolve_tree


def make_template(tmp_path: Path) -> Path:
    template_dir = tmp_path / "template"
    (template_dir / "{{ group_id }}").mkdir(parents=True)
    (template_dir / "{{ group_id }}" / "hello.txt").write_text(
        "Hello {{ name }}!", encoding="utf-8"
    )
    (template_dir / "static.txt").write_text("no variables here", encoding="utf-8")
    return template_dir


def test_resolve_tree_renders_names_without_writing(tmp_path):
    template_dir = make_template(tmp_path)
    context = {"group_id": "acme", "name": "World"}

    result = resolve_tree(template_dir, context)

    assert result == sorted(
        [Path("acme/hello.txt"), Path("static.txt")]
    )
    assert not (tmp_path / "out").exists()


def test_render_tree_writes_rendered_names_and_contents(tmp_path):
    template_dir = make_template(tmp_path)
    target_dir = tmp_path / "out"
    context = {"group_id": "acme", "name": "World"}

    render_tree(template_dir, target_dir, context)

    rendered_file = target_dir / "acme" / "hello.txt"
    assert rendered_file.read_text(encoding="utf-8") == "Hello World!"
    assert (target_dir / "static.txt").read_text(encoding="utf-8") == "no variables here"


def test_render_tree_supports_slash_producing_directory_tokens(tmp_path):
    template_dir = tmp_path / "template2"
    (template_dir / "src" / "{{ package_path }}").mkdir(parents=True)
    (template_dir / "src" / "{{ package_path }}" / "App.java").write_text(
        "package {{ base_package }};", encoding="utf-8"
    )
    target_dir = tmp_path / "out2"
    context = {"package_path": "com/example/demo", "base_package": "com.example.demo"}

    render_tree(template_dir, target_dir, context)

    written = target_dir / "src" / "com" / "example" / "demo" / "App.java"
    assert written.read_text(encoding="utf-8") == "package com.example.demo;"


def test_render_tree_raises_if_target_exists(tmp_path):
    template_dir = make_template(tmp_path)
    target_dir = tmp_path / "out"
    target_dir.mkdir()

    with pytest.raises(TargetExistsError):
        render_tree(template_dir, target_dir, {"group_id": "acme", "name": "World"})

    assert list(target_dir.iterdir()) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\pytest tests/test_renderer.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.renderer'`.

- [ ] **Step 3: Write `core/renderer.py`**

```python
from pathlib import Path

import jinja2


class TargetExistsError(Exception):
    pass


def _iter_rendered_files(template_dir: Path, context: dict):
    env = jinja2.Environment()
    for path in sorted(template_dir.rglob("*")):
        if path.is_dir():
            continue
        rel_parts = [
            env.from_string(part).render(**context)
            for part in path.relative_to(template_dir).parts
        ]
        yield path, Path(*rel_parts)


def resolve_tree(template_dir: Path, context: dict) -> list[Path]:
    return sorted(rel for _, rel in _iter_rendered_files(template_dir, context))


def render_tree(template_dir: Path, target_dir: Path, context: dict) -> None:
    if target_dir.exists():
        raise TargetExistsError(f"Target directory already exists: {target_dir}")

    env = jinja2.Environment()
    for template_file, rel_path in _iter_rendered_files(template_dir, context):
        out_path = target_dir / rel_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        content = template_file.read_text(encoding="utf-8")
        rendered = env.from_string(content).render(**context)
        out_path.write_text(rendered, encoding="utf-8")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv\Scripts\pytest tests/test_renderer.py -v`
Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add core/renderer.py tests/test_renderer.py
git commit -m "feat: add Jinja2 tree renderer for file/folder names and contents"
```

---

## Task 3: Tree Preview

**Files:**
- Create: `core/tree_preview.py`
- Test: `tests/test_tree_preview.py`

**Interfaces:**
- Consumes: `list[Path]` as produced by `resolve_tree` (Task 2)
- Produces:
  - `format_tree(paths: list[Path]) -> str` — newline-joined, forward-slash-normalized, sorted relative paths
  - `confirm(tree_text: str, prompt_fn=input) -> bool` — prints `tree_text`, prompts, returns `True` only for `y`/`yes` (case-insensitive), `False` otherwise (including empty input)

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_tree_preview.py
from pathlib import Path

from core.tree_preview import confirm, format_tree


def test_format_tree_sorts_and_normalizes_separators():
    paths = [Path("b/file.txt"), Path("a.txt")]
    assert format_tree(paths) == "a.txt\nb/file.txt"


def test_confirm_returns_true_on_yes(capsys):
    result = confirm("tree here", prompt_fn=lambda _: "y")
    assert result is True
    assert "tree here" in capsys.readouterr().out


def test_confirm_returns_true_on_full_word_yes():
    assert confirm("tree", prompt_fn=lambda _: "YES") is True


def test_confirm_returns_false_on_no():
    assert confirm("tree", prompt_fn=lambda _: "n") is False


def test_confirm_returns_false_on_empty_input():
    assert confirm("tree", prompt_fn=lambda _: "") is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\pytest tests/test_tree_preview.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.tree_preview'`.

- [ ] **Step 3: Write `core/tree_preview.py`**

```python
from pathlib import Path


def format_tree(paths: list[Path]) -> str:
    normalized = [str(p).replace("\\", "/") for p in paths]
    return "\n".join(sorted(normalized))


def confirm(tree_text: str, prompt_fn=input) -> bool:
    print(tree_text)
    answer = prompt_fn("Generate this project? [y/N]: ")
    return answer.strip().lower() in ("y", "yes")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv\Scripts\pytest tests/test_tree_preview.py -v`
Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add core/tree_preview.py tests/test_tree_preview.py
git commit -m "feat: add tree preview formatting and y/n confirmation"
```

---

## Task 4: Progress Reporter

**Files:**
- Create: `core/progress.py`
- Test: `tests/test_progress.py`

**Interfaces:**
- Consumes: nothing
- Produces: `step(message: str) -> None` — prints `f"-> {message}"` to stdout

- [ ] **Step 1: Write the failing test**

```python
# tests/test_progress.py
from core.progress import step


def test_step_prints_arrow_prefixed_message(capsys):
    step("Writing project files...")
    assert capsys.readouterr().out == "-> Writing project files...\n"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest tests/test_progress.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.progress'`.

- [ ] **Step 3: Write `core/progress.py`**

```python
def step(message: str) -> None:
    print(f"-> {message}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest tests/test_progress.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/progress.py tests/test_progress.py
git commit -m "feat: add simple progress step printer"
```

---

## Task 5: Validator

**Files:**
- Create: `core/validator.py`
- Test: `tests/test_validator.py`

**Interfaces:**
- Consumes: a `target_dir: Path` pointing at a generated (or fixture) project directory
- Produces:
  - `ValidationResult` (dataclass): `passed: bool`, `message: str`, `details: str = ""`
  - `check_structure(target_dir: Path, expected_paths: list[Path]) -> ValidationResult`
  - `run_compile(target_dir: Path, timeout: int = 300) -> ValidationResult` — shells out to `mvn -q compile` in `target_dir` via the resolved executable path (`shutil.which("mvn")`, falling back to `"mvn"`)

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_validator.py
from pathlib import Path

from core.validator import ValidationResult, check_structure, run_compile

MINIMAL_POM = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>minimal</artifactId>
  <version>0.0.1-SNAPSHOT</version>
  <properties>
    <maven.compiler.source>21</maven.compiler.source>
    <maven.compiler.target>21</maven.compiler.target>
  </properties>
</project>
"""

MINIMAL_JAVA = """package com.example;

public class Hello {
    public static void main(String[] args) {
        System.out.println("hi");
    }
}
"""


def test_check_structure_passes_when_all_expected_files_exist(tmp_path):
    (tmp_path / "pom.xml").write_text("x", encoding="utf-8")
    result = check_structure(tmp_path, [Path("pom.xml")])
    assert result == ValidationResult(True, "Structural check passed")


def test_check_structure_fails_and_lists_missing_files(tmp_path):
    result = check_structure(tmp_path, [Path("pom.xml"), Path("docker-compose.yml")])
    assert result.passed is False
    assert "pom.xml" in result.details
    assert "docker-compose.yml" in result.details


def test_run_compile_passes_for_a_valid_minimal_maven_project(tmp_path):
    (tmp_path / "pom.xml").write_text(MINIMAL_POM, encoding="utf-8")
    java_dir = tmp_path / "src" / "main" / "java" / "com" / "example"
    java_dir.mkdir(parents=True)
    (java_dir / "Hello.java").write_text(MINIMAL_JAVA, encoding="utf-8")

    result = run_compile(tmp_path)

    assert result.passed is True, result.details


def test_run_compile_fails_for_broken_java_source(tmp_path):
    (tmp_path / "pom.xml").write_text(MINIMAL_POM, encoding="utf-8")
    java_dir = tmp_path / "src" / "main" / "java" / "com" / "example"
    java_dir.mkdir(parents=True)
    (java_dir / "Hello.java").write_text("this is not valid java", encoding="utf-8")

    result = run_compile(tmp_path)

    assert result.passed is False
    assert result.details
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\pytest tests/test_validator.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.validator'`.

- [ ] **Step 3: Write `core/validator.py`**

```python
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ValidationResult:
    passed: bool
    message: str
    details: str = ""


def check_structure(target_dir: Path, expected_paths: list[Path]) -> ValidationResult:
    missing = [str(p) for p in expected_paths if not (target_dir / p).exists()]
    if missing:
        return ValidationResult(
            False, "Structural check failed: missing files", "\n".join(missing)
        )
    return ValidationResult(True, "Structural check passed")


def run_compile(target_dir: Path, timeout: int = 300) -> ValidationResult:
    mvn_cmd = shutil.which("mvn") or "mvn"
    try:
        result = subprocess.run(
            [mvn_cmd, "-q", "compile"],
            cwd=target_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return ValidationResult(False, "mvn executable not found on PATH")
    except subprocess.TimeoutExpired:
        return ValidationResult(False, f"mvn compile timed out after {timeout}s")

    if result.returncode != 0:
        return ValidationResult(
            False, "mvn compile failed", result.stdout + result.stderr
        )
    return ValidationResult(True, "Compile check passed")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv\Scripts\pytest tests/test_validator.py -v`
Expected: all 4 tests PASS. (The two `run_compile` tests shell out to real Maven and may take several seconds each — this is expected.)

- [ ] **Step 5: Commit**

```bash
git add core/validator.py tests/test_validator.py
git commit -m "feat: add structural and mvn compile validation checks"
```

---

## Task 6: Wizard

**Files:**
- Create: `core/wizard.py`
- Test: `tests/test_wizard.py`

**Interfaces:**
- Consumes: `ForgeConfig`, `validate_project_name`, `validate_group_id`, `validate_artifact_id` (Task 1)
- Produces: `collect_params(overrides: dict, prompt_fn=input) -> ForgeConfig` — for each of `project_name`, `target_path`, `group_id`, `artifact_id`: uses `overrides[field]` if present and non-empty, otherwise prompts via `prompt_fn`; re-prompts on validation failure (printing the error) until a valid value is entered; returns a fully-constructed `ForgeConfig`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_wizard.py
from pathlib import Path

from core.wizard import collect_params


def test_collect_params_uses_overrides_without_prompting():
    def fail_if_called(_label):
        raise AssertionError("prompt_fn should not be called")

    config = collect_params(
        {
            "project_name": "demo-service",
            "target_path": "/tmp/out",
            "group_id": "com.example",
            "artifact_id": "demo-service",
        },
        prompt_fn=fail_if_called,
    )
    assert config.project_name == "demo-service"
    assert config.target_path == Path("/tmp/out")


def test_collect_params_prompts_for_missing_fields():
    responses = iter(["demo-service", "/tmp/out", "com.example", "demo-service"])
    config = collect_params({}, prompt_fn=lambda _label: next(responses))
    assert config.group_id == "com.example"
    assert config.artifact_id == "demo-service"


def test_collect_params_reprompts_on_invalid_group_id():
    responses = iter(
        ["demo-service", "/tmp/out", "BAD_GROUP", "com.example", "demo-service"]
    )
    config = collect_params({}, prompt_fn=lambda _label: next(responses))
    assert config.group_id == "com.example"


def test_collect_params_mixes_overrides_and_prompts():
    responses = iter(["/tmp/out", "com.example"])
    config = collect_params(
        {"project_name": "demo-service", "artifact_id": "demo-service"},
        prompt_fn=lambda _label: next(responses),
    )
    assert config.target_path == Path("/tmp/out")
    assert config.group_id == "com.example"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\pytest tests/test_wizard.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.wizard'`.

- [ ] **Step 3: Write `core/wizard.py`**

```python
from pathlib import Path

from core.config_schema import (
    ForgeConfig,
    validate_artifact_id,
    validate_group_id,
    validate_project_name,
)

FIELD_PROMPTS = [
    ("project_name", "Project name", validate_project_name),
    ("target_path", "Target path (parent directory)", None),
    ("group_id", "Group id (e.g. com.example)", validate_group_id),
    ("artifact_id", "Artifact id (e.g. my-service)", validate_artifact_id),
]


def _prompt_field(label, validator, prompt_fn):
    while True:
        raw = prompt_fn(f"{label}: ").strip()
        if validator is None:
            return raw
        try:
            return validator(raw)
        except ValueError as exc:
            print(f"Invalid value: {exc}")


def collect_params(overrides: dict, prompt_fn=input) -> ForgeConfig:
    values = dict(overrides)
    for field, label, validator in FIELD_PROMPTS:
        if values.get(field) in (None, ""):
            values[field] = _prompt_field(label, validator, prompt_fn)
    values["target_path"] = Path(values["target_path"])
    return ForgeConfig(**values)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv\Scripts\pytest tests/test_wizard.py -v`
Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add core/wizard.py tests/test_wizard.py
git commit -m "feat: add interactive wizard with per-field reprompt on invalid input"
```

---

## Task 7: Base-Layered Template Content

**Files:**
- Create: `templates/base-layered/pom.xml`
- Create: `templates/base-layered/docker-compose.yml`
- Create: `templates/base-layered/.gitignore`
- Create: `templates/base-layered/README.md`
- Create: `templates/base-layered/src/main/resources/application.yml`
- Create: `templates/base-layered/src/main/resources/db/changelog/db.changelog-master.yaml`
- Create: `templates/base-layered/src/main/resources/db/changelog/001-create-example-table.yaml`
- Create: `templates/base-layered/src/main/java/{{ package_path }}/{{ app_class_name }}Application.java`
- Create: `templates/base-layered/src/main/java/{{ package_path }}/entity/Example.java`
- Create: `templates/base-layered/src/main/java/{{ package_path }}/repository/ExampleRepository.java`
- Create: `templates/base-layered/src/main/java/{{ package_path }}/service/ExampleService.java`
- Create: `templates/base-layered/src/main/java/{{ package_path }}/controller/ExampleController.java`
- Test: `tests/test_template_content.py`

**Interfaces:**
- Consumes: nothing (static content authoring); the `{{ package_path }}` and `{{ app_class_name }}` directory/file name tokens are rendered by `core.renderer` (Task 2) at generation time, and the `{{ ... }}` content tokens are populated from `ForgeConfig.template_context()` (Task 1)
- Produces: `templates/base-layered/` — the single v1 template tree, consumed by Task 8 (CLI) and Task 9 (end-to-end test)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_template_content.py
from pathlib import Path

TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "base-layered"

EXPECTED_TEMPLATE_FILES = [
    "pom.xml",
    "docker-compose.yml",
    ".gitignore",
    "README.md",
    "src/main/resources/application.yml",
    "src/main/resources/db/changelog/db.changelog-master.yaml",
    "src/main/resources/db/changelog/001-create-example-table.yaml",
    "src/main/java/{{ package_path }}/{{ app_class_name }}Application.java",
    "src/main/java/{{ package_path }}/entity/Example.java",
    "src/main/java/{{ package_path }}/repository/ExampleRepository.java",
    "src/main/java/{{ package_path }}/service/ExampleService.java",
    "src/main/java/{{ package_path }}/controller/ExampleController.java",
]


def test_all_expected_template_files_exist():
    missing = [f for f in EXPECTED_TEMPLATE_FILES if not (TEMPLATE_DIR / f).exists()]
    assert missing == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest tests/test_template_content.py -v`
Expected: FAIL — `missing` is non-empty (no template files exist yet).

- [ ] **Step 3: Create `templates/base-layered/pom.xml`**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>

  <parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>4.0.0</version>
    <relativePath/>
  </parent>

  <groupId>{{ group_id }}</groupId>
  <artifactId>{{ artifact_id }}</artifactId>
  <version>0.0.1-SNAPSHOT</version>
  <name>{{ project_name }}</name>

  <properties>
    <java.version>21</java.version>
  </properties>

  <dependencies>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-data-jpa</artifactId>
    </dependency>
    <dependency>
      <groupId>org.liquibase</groupId>
      <artifactId>liquibase-core</artifactId>
    </dependency>
    <dependency>
      <groupId>org.postgresql</groupId>
      <artifactId>postgresql</artifactId>
      <scope>runtime</scope>
    </dependency>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-test</artifactId>
      <scope>test</scope>
    </dependency>
  </dependencies>

  <build>
    <plugins>
      <plugin>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-maven-plugin</artifactId>
      </plugin>
    </plugins>
  </build>
</project>
```

- [ ] **Step 4: Create `templates/base-layered/docker-compose.yml`**

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: {{ artifact_id.replace('-', '_') }}
      POSTGRES_USER: forge
      POSTGRES_PASSWORD: forge
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

- [ ] **Step 5: Create `templates/base-layered/.gitignore`**

```
target/
.idea/
*.class
*.log
```

- [ ] **Step 6: Create `templates/base-layered/README.md`**

```markdown
# {{ project_name }}

Generated by Forge.

## Run locally

    docker compose up -d
    mvn spring-boot:run
```

- [ ] **Step 7: Create `templates/base-layered/src/main/resources/application.yml`**

```yaml
spring:
  application:
    name: {{ artifact_id }}
  datasource:
    url: jdbc:postgresql://localhost:5432/{{ artifact_id.replace('-', '_') }}
    username: forge
    password: forge
  liquibase:
    change-log: classpath:db/changelog/db.changelog-master.yaml
  jpa:
    hibernate:
      ddl-auto: none

server:
  port: 8080
```

- [ ] **Step 8: Create `templates/base-layered/src/main/resources/db/changelog/db.changelog-master.yaml`**

```yaml
databaseChangeLog:
  - include:
      file: db/changelog/001-create-example-table.yaml
```

- [ ] **Step 9: Create `templates/base-layered/src/main/resources/db/changelog/001-create-example-table.yaml`**

```yaml
databaseChangeLog:
  - changeSet:
      id: 001-create-example-table
      author: forge
      changes:
        - createTable:
            tableName: example
            columns:
              - column:
                  name: id
                  type: BIGINT
                  autoIncrement: true
                  constraints:
                    primaryKey: true
                    nullable: false
              - column:
                  name: name
                  type: VARCHAR(255)
```

- [ ] **Step 10: Create `templates/base-layered/src/main/java/{{ package_path }}/{{ app_class_name }}Application.java`**

Create the directory `templates/base-layered/src/main/java/{{ package_path }}/` (literal folder name containing the Jinja2 token — this is valid on both Windows and POSIX filesystems), then create the file `{{ app_class_name }}Application.java` inside it:

```java
package {{ base_package }};

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class {{ app_class_name }}Application {
    public static void main(String[] args) {
        SpringApplication.run({{ app_class_name }}Application.class, args);
    }
}
```

- [ ] **Step 11: Create `templates/base-layered/src/main/java/{{ package_path }}/entity/Example.java`**

```java
package {{ base_package }}.entity;

import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;

@Entity
public class Example {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String name;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }
}
```

- [ ] **Step 12: Create `templates/base-layered/src/main/java/{{ package_path }}/repository/ExampleRepository.java`**

```java
package {{ base_package }}.repository;

import {{ base_package }}.entity.Example;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ExampleRepository extends JpaRepository<Example, Long> {
}
```

- [ ] **Step 13: Create `templates/base-layered/src/main/java/{{ package_path }}/service/ExampleService.java`**

```java
package {{ base_package }}.service;

import {{ base_package }}.entity.Example;
import {{ base_package }}.repository.ExampleRepository;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.NoSuchElementException;

@Service
public class ExampleService {

    private final ExampleRepository repository;

    public ExampleService(ExampleRepository repository) {
        this.repository = repository;
    }

    public List<Example> findAll() {
        return repository.findAll();
    }

    public Example findById(Long id) {
        return repository.findById(id)
                .orElseThrow(() -> new NoSuchElementException("Example not found: " + id));
    }

    public Example save(Example example) {
        return repository.save(example);
    }

    public Example update(Long id, Example example) {
        Example existing = findById(id);
        existing.setName(example.getName());
        return repository.save(existing);
    }

    public void delete(Long id) {
        repository.deleteById(id);
    }
}
```

- [ ] **Step 14: Create `templates/base-layered/src/main/java/{{ package_path }}/controller/ExampleController.java`**

```java
package {{ base_package }}.controller;

import {{ base_package }}.entity.Example;
import {{ base_package }}.service.ExampleService;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/examples")
public class ExampleController {

    private final ExampleService service;

    public ExampleController(ExampleService service) {
        this.service = service;
    }

    @GetMapping
    public List<Example> findAll() {
        return service.findAll();
    }

    @GetMapping("/{id}")
    public Example findById(@PathVariable Long id) {
        return service.findById(id);
    }

    @PostMapping
    public Example create(@RequestBody Example example) {
        return service.save(example);
    }

    @PutMapping("/{id}")
    public Example update(@PathVariable Long id, @RequestBody Example example) {
        return service.update(id, example);
    }

    @DeleteMapping("/{id}")
    public void delete(@PathVariable Long id) {
        service.delete(id);
    }
}
```

- [ ] **Step 15: Run test to verify it passes**

Run: `.venv\Scripts\pytest tests/test_template_content.py -v`
Expected: PASS.

- [ ] **Step 16: Commit**

```bash
git add templates/
git commit -m "feat: add base-layered Spring Boot template with example CRUD entity"
```

---

## Task 8: CLI Wiring

**Files:**
- Create: `cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `ForgeConfig` (Task 1), `render_tree`/`resolve_tree`/`TargetExistsError` (Task 2), `format_tree`/`confirm` (Task 3), `step` (Task 4), `check_structure`/`run_compile`/`ValidationResult` (Task 5), `collect_params` (Task 6), `templates/base-layered/` (Task 7)
- Produces:
  - `app: typer.Typer` with command `new`
  - `main() -> None` — console-script entry point, calls `app()`
  - `TEMPLATE_DIR: Path` — `Path(__file__).parent / "templates" / "base-layered"`
  - `EXPECTED_STRUCTURAL_PATHS: list[Path]` — `[Path("pom.xml"), Path("docker-compose.yml"), Path(".gitignore"), Path("src/main/resources/application.yml")]`

- [ ] **Step 1: Write the failing tests**

Uses Typer's `CliRunner` and monkeypatches `core.validator.run_compile` so this test suite stays fast (Task 9 covers the real `mvn compile` path end-to-end).

```python
# tests/test_cli.py
from pathlib import Path

from typer.testing import CliRunner

import cli
from core.validator import ValidationResult

runner = CliRunner()


def test_new_aborts_if_target_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "TEMPLATE_DIR", cli.TEMPLATE_DIR)
    existing = tmp_path / "demo-service"
    existing.mkdir()

    result = runner.invoke(
        cli.app,
        [
            "new",
            "--name", "demo-service",
            "--path", str(tmp_path),
            "--group-id", "com.example",
            "--artifact-id", "demo-service",
        ],
    )

    assert result.exit_code == 1
    assert "already exists" in result.output


def test_new_generates_project_on_confirm(tmp_path, monkeypatch):
    monkeypatch.setattr(
        cli, "run_compile", lambda target_dir: ValidationResult(True, "ok")
    )

    result = runner.invoke(
        cli.app,
        [
            "new",
            "--name", "demo-service",
            "--path", str(tmp_path),
            "--group-id", "com.example",
            "--artifact-id", "demo-service",
        ],
        input="y\n",
    )

    assert result.exit_code == 0, result.output
    assert (tmp_path / "demo-service" / "pom.xml").exists()
    assert "Project generated successfully" in result.output


def test_new_cancels_on_no_confirm(tmp_path):
    result = runner.invoke(
        cli.app,
        [
            "new",
            "--name", "demo-service",
            "--path", str(tmp_path),
            "--group-id", "com.example",
            "--artifact-id", "demo-service",
        ],
        input="n\n",
    )

    assert result.exit_code == 0
    assert not (tmp_path / "demo-service").exists()
    assert "Cancelled" in result.output


def test_new_prompts_to_delete_on_validation_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(
        cli,
        "run_compile",
        lambda target_dir: ValidationResult(False, "mvn compile failed", "boom"),
    )

    result = runner.invoke(
        cli.app,
        [
            "new",
            "--name", "demo-service",
            "--path", str(tmp_path),
            "--group-id", "com.example",
            "--artifact-id", "demo-service",
        ],
        input="y\ny\n",
    )

    assert result.exit_code == 1
    assert "Validation failed" in result.output
    assert not (tmp_path / "demo-service").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\pytest tests/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cli'`.

- [ ] **Step 3: Write `cli.py`**

```python
import shutil
from pathlib import Path

import typer

from core.config_schema import ForgeConfig
from core.progress import step
from core.renderer import render_tree, resolve_tree
from core.tree_preview import confirm, format_tree
from core.validator import check_structure, run_compile
from core.wizard import collect_params

app = typer.Typer()

TEMPLATE_DIR = Path(__file__).parent / "templates" / "base-layered"

EXPECTED_STRUCTURAL_PATHS = [
    Path("pom.xml"),
    Path("docker-compose.yml"),
    Path(".gitignore"),
    Path("src/main/resources/application.yml"),
]


@app.command()
def new(
    project_name: str = typer.Option(None, "--name"),
    target_path: str = typer.Option(None, "--path"),
    group_id: str = typer.Option(None, "--group-id"),
    artifact_id: str = typer.Option(None, "--artifact-id"),
):
    overrides = {
        "project_name": project_name,
        "target_path": target_path,
        "group_id": group_id,
        "artifact_id": artifact_id,
    }
    config = collect_params(overrides)

    if config.target_dir.exists():
        typer.echo(f"Error: target directory already exists: {config.target_dir}")
        raise typer.Exit(code=1)

    context = config.template_context()
    tree = resolve_tree(TEMPLATE_DIR, context)
    if not confirm(format_tree(tree)):
        typer.echo("Cancelled.")
        raise typer.Exit(code=0)

    step("Writing project files...")
    render_tree(TEMPLATE_DIR, config.target_dir, context)

    step("Running structural check...")
    structural = check_structure(config.target_dir, EXPECTED_STRUCTURAL_PATHS)

    compile_result = None
    if structural.passed:
        step("Running compile check...")
        compile_result = run_compile(config.target_dir)

    failure = structural if not structural.passed else (
        compile_result if compile_result and not compile_result.passed else None
    )
    if failure is not None:
        typer.echo(f"Validation failed: {failure.message}\n{failure.details}")
        if typer.confirm("Delete the generated folder?", default=False):
            shutil.rmtree(config.target_dir)
        raise typer.Exit(code=1)

    typer.echo("Project generated successfully!")
    typer.echo(f"cd {config.target_dir}")
    typer.echo("docker compose up -d")
    typer.echo("mvn spring-boot:run")


def main():
    app()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv\Scripts\pytest tests/test_cli.py -v`
Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add cli.py tests/test_cli.py
git commit -m "feat: wire up forge new CLI command (wizard, preview, render, validate)"
```

---

## Task 9: End-to-End Generation Test

**Files:**
- Test: `tests/test_generation.py`

**Interfaces:**
- Consumes: `ForgeConfig` (Task 1), `render_tree` (Task 2), `check_structure`/`run_compile` (Task 5), `TEMPLATE_DIR`/`EXPECTED_STRUCTURAL_PATHS` (Task 8)
- Produces: nothing consumed by later tasks — this is Forge's own regression safety net, run in CI to catch template drift that breaks generated projects

- [ ] **Step 1: Write the end-to-end test**

```python
# tests/test_generation.py
from pathlib import Path

from cli import EXPECTED_STRUCTURAL_PATHS, TEMPLATE_DIR
from core.config_schema import ForgeConfig
from core.renderer import render_tree
from core.validator import check_structure, run_compile


def test_generated_project_passes_structural_and_compile_checks(tmp_path):
    config = ForgeConfig(
        project_name="demo-service",
        target_path=tmp_path,
        group_id="com.example",
        artifact_id="demo-service",
    )

    render_tree(TEMPLATE_DIR, config.target_dir, config.template_context())

    structural = check_structure(config.target_dir, EXPECTED_STRUCTURAL_PATHS)
    assert structural.passed, structural.details

    compile_result = run_compile(config.target_dir)
    assert compile_result.passed, compile_result.details

    app_file = (
        config.target_dir
        / "src/main/java/com/example/demoservice/DemoServiceApplication.java"
    )
    assert app_file.exists()
```

- [ ] **Step 2: Run test to verify it currently passes**

Run: `.venv\Scripts\pytest tests/test_generation.py -v`
Expected: PASS. (Unlike earlier tasks, this test isn't expected to fail first — all the pieces it exercises were already built and individually tested in Tasks 1, 2, 5, 7, and 8. This step is the integration proof that they compose correctly, particularly the real `mvn compile` run against the full generated project, which no earlier unit test exercised.)

If it fails, the failure is a real integration bug (e.g. a mismatch between a template file's Jinja2 tokens and the context keys in `ForgeConfig.template_context()`, or a Java compile error in the template content) — fix the root cause in the relevant Task 1–8 file, not in this test.

- [ ] **Step 3: Run the full test suite**

Run: `.venv\Scripts\pytest -v`
Expected: all tests across every task PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/test_generation.py
git commit -m "test: add end-to-end generation test validating full mvn compile"
```

---

## Post-Plan Verification

After Task 9, manually run the CLI once against a real target directory to confirm the interactive wizard and preview work as intended (this exercises the `input()`-based prompt path that the automated tests bypass via `prompt_fn` injection):

```bash
.venv\Scripts\python cli.py new
```

Follow the prompts, confirm the tree preview, and verify the generated project builds and boots:

```bash
cd <generated-project-dir>
docker compose up -d
mvn spring-boot:run
```
