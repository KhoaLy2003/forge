"""Local web UI backend: a small FastAPI app over the same core modules `forge new` uses."""

from pathlib import Path

import yaml
from fastapi import Body, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from core.config_schema import ForgeConfig
from core.entity_spec import RELATION_TYPES, ProjectFile, parse_project_data
from core.generation import TEMPLATES, build_plan, preview_config, run_checks
from core.renderer import render_files, render_tree
from core.templates import ENTITY_DIR, JOIN_DIR, SHARED_DIR
from core.type_map import VALID_TYPES
from core.wizard import save_forge_yaml

STATIC_DIR = Path(__file__).parent / "static"
TOKEN_HEADER = "X-Forge-Token"
PROJECT_KEYS = ("project_name", "target_path", "group_id", "artifact_id", "template")


def _clean(data):
    """Recursively drop dict keys whose value is None or '' (False, 0 and empty containers stay)."""
    if isinstance(data, dict):
        return {k: _clean(v) for k, v in data.items() if v is not None and v != ""}
    if isinstance(data, list):
        return [_clean(v) for v in data]
    return data


def _parse(body: dict) -> ProjectFile:
    return parse_project_data(_clean(body), "model")


def _errors(exc: Exception) -> list[str]:
    """Flatten a loader ValueError or a ForgeConfig ValidationError into one message per problem."""
    if isinstance(exc, ValidationError):
        messages: list[str] = []
        for err in exc.errors():
            msg = err["msg"].removeprefix("Value error, ")
            if err["loc"]:
                messages.append(f"{err['loc'][0]}: {msg}")
                continue
            for line in msg.splitlines():
                line = line.strip().removeprefix("- ").strip()
                if line and line != "Invalid entity model:":
                    messages.append(line)
        return messages
    lines = str(exc).splitlines()
    rest = lines[1:] if len(lines) > 1 else lines
    return [line.strip().removeprefix("- ").strip() for line in rest if line.strip()]


def _fail(exc: Exception, status: int = 200) -> JSONResponse:
    return JSONResponse({"ok": False, "errors": _errors(exc)}, status_code=status)


def _model_dict(project_file: ProjectFile) -> dict:
    """The forge.yaml JSON shape for the UI (entity bodies are always mappings)."""
    model = project_file.model_dump(mode="json", exclude_none=True, exclude={"entities"})
    model["entities"] = {
        key: entity.model_dump(mode="json", by_alias=True, exclude_defaults=True, exclude={"name"})
        for key, entity in project_file.entities.items()
    }
    return model


def create_app(token: str) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def require_token(request: Request, call_next):
        if request.url.path.startswith("/api/") and request.headers.get(TOKEN_HEADER) != token:
            return JSONResponse({"errors": ["forbidden"]}, status_code=403)
        return await call_next(request)

    @app.get("/api/meta")
    def meta():
        return {
            "templates": sorted(TEMPLATES),
            "field_types": list(VALID_TYPES),
            "relation_types": list(RELATION_TYPES),
            "default_template": "base-layered",
            "default_target_path": str(Path.cwd()),
        }

    @app.post("/api/validate")
    def validate(body: dict = Body(...)):
        try:
            config = preview_config(_parse(body))
            context = config.template_context()
        except (ValueError, ValidationError) as exc:
            return _fail(exc)
        return {
            "ok": True,
            "entity_count": len(config.entities),
            "join_tables": [str(t.name) for t in context.get("join_tables", [])],
            "changelog_files": list(context.get("changelog_files", [])),
        }

    @app.post("/api/preview")
    def preview(body: dict = Body(...)):
        try:
            config = preview_config(_parse(body))
            context, excluded = build_plan(config)
            files = render_files(
                SHARED_DIR, context, excluded=excluded, entities_dir=ENTITY_DIR, join_dir=JOIN_DIR
            )
        except (ValueError, ValidationError) as exc:
            return _fail(exc)
        return {"files": [{"path": p.as_posix(), "content": c} for p, c in files.items()]}

    @app.post("/api/generate")
    def generate(body: dict = Body(...)):
        model = body.get("model") or {}
        with_compile = bool(body.get("run_compile", False))
        try:
            project_file = _parse(model)
            params = {k: getattr(project_file, k) for k in PROJECT_KEYS if getattr(project_file, k) is not None}
            config = ForgeConfig(**params, entities=project_file.entities)
            context, excluded = build_plan(config)
        except (ValueError, ValidationError) as exc:
            return _fail(exc)
        if config.target_dir.exists():
            return JSONResponse(
                {"ok": False, "errors": [f"target directory already exists: {config.target_dir}"]},
                status_code=409,
            )
        try:
            render_tree(
                SHARED_DIR,
                config.target_dir,
                context,
                excluded=excluded,
                entities_dir=ENTITY_DIR,
                join_dir=JOIN_DIR,
            )
        except Exception as exc:  # leave the folder for inspection; the user decides whether to delete it
            return JSONResponse({"ok": False, "errors": [f"failed to write project files: {exc}"]})
        results = run_checks(config, context, excluded, with_compile)
        ok = all(result.passed for _, result in results)
        if ok and config.has_entities:
            save_forge_yaml(config, config.target_dir / "forge.yaml")
        return {
            "ok": ok,
            "target_dir": str(config.target_dir),
            "checks": [
                {
                    "name": name,
                    "passed": result.passed,
                    "message": result.message,
                    "details": result.details,
                }
                for name, result in results
            ],
        }

    @app.post("/api/import")
    def import_model(body: dict = Body(...)):
        try:
            data = yaml.safe_load(body.get("text", ""))
            project_file = parse_project_data(data, "forge.yaml")
        except yaml.YAMLError as exc:
            return {"ok": False, "errors": [f"invalid YAML: {exc}"]}
        except ValueError as exc:
            return _fail(exc)
        return {"ok": True, "model": _model_dict(project_file)}

    @app.post("/api/export")
    def export(body: dict = Body(...)):
        return {"text": yaml.safe_dump(_clean(body), sort_keys=False, allow_unicode=True)}

    @app.get("/")
    def index():
        return FileResponse(STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app
