"""Tests for the local web UI API (`core/ui/server.py`)."""

import copy
from pathlib import Path

import pytest
import yaml

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from core.ui.server import create_app  # noqa: E402

FIXTURE = Path(__file__).parent / "fixtures" / "entities.forge.yaml"
TOKEN = "test-token"


@pytest.fixture
def client():
    return TestClient(create_app(TOKEN), headers={"X-Forge-Token": TOKEN})


@pytest.fixture
def model():
    data = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    return copy.deepcopy(data)


def test_api_requires_token():
    anonymous = TestClient(create_app(TOKEN))
    assert anonymous.get("/api/meta").status_code == 403
    assert anonymous.post("/api/validate", json={}).status_code == 403
    assert anonymous.get("/api/meta", headers={"X-Forge-Token": "wrong"}).status_code == 403
    assert anonymous.get("/").status_code == 200
    assert anonymous.get("/static/app.js").status_code == 200


def test_meta(client):
    data = client.get("/api/meta").json()
    assert "base-layered" in data["templates"] and "uuid" in data["field_types"]
    assert "many-to-many" in data["relation_types"]


def test_validate_fixture_without_project_params(client, model):
    data = client.post("/api/validate", json=model).json()
    assert data["ok"] is True
    assert data["entity_count"] == 5 and data["changelog_files"]
    assert data["join_tables"]


def test_validate_reports_unknown_target(client, model):
    model["entities"]["Order"]["relations"]["customer"]["target"] = "Nope"
    data = client.post("/api/validate", json=model).json()
    assert data["ok"] is False
    assert any("Nope" in e for e in data["errors"])


def test_validate_ignores_blank_ui_values(client):
    body = {"project_name": "", "template": "base-layered", "entities": {"Tag": {"table": "", "fields": {}}}}
    assert client.post("/api/validate", json=body).json()["ok"] is True


def test_preview_returns_rendered_files(client, model):
    files = client.post("/api/preview", json=model).json()["files"]
    pom = next(f for f in files if f["path"] == "pom.xml")
    assert isinstance(pom["content"], str) and "<artifactId>" in pom["content"]


def test_generate_writes_project_and_model(client, model, tmp_path):
    model.update(project_name="demo-service", target_path=str(tmp_path), group_id="com.example", artifact_id="demo-service")
    data = client.post("/api/generate", json={"model": model}).json()
    assert data["ok"] is True, data
    assert [c["name"] for c in data["checks"]] == ["structure", "observability"]
    project = tmp_path / "demo-service"
    assert (project / "pom.xml").is_file() and (project / "forge.yaml").is_file()

    again = client.post("/api/generate", json={"model": model})
    assert again.status_code == 409
    assert again.json()["ok"] is False


def test_generate_reports_missing_project_name(client, model, tmp_path):
    model.update(target_path=str(tmp_path), group_id="com.example", artifact_id="x")
    data = client.post("/api/generate", json={"model": model}).json()
    assert data["ok"] is False
    assert any(e.startswith("project_name") for e in data["errors"])
    assert not list(tmp_path.iterdir())


def test_export_import_round_trip(client, model):
    text = client.post("/api/export", json=model).json()["text"]
    imported = client.post("/api/import", json={"text": text}).json()
    assert imported["ok"] is True
    assert imported["model"]["entities"].keys() == model["entities"].keys()
    reexported = client.post("/api/export", json=imported["model"]).json()["text"]
    assert yaml.safe_load(reexported)["entities"] == yaml.safe_load(text)["entities"]


def test_import_rejects_bad_yaml_and_bad_model(client):
    assert client.post("/api/import", json={"text": "a: [1"}).json()["ok"] is False
    bad = client.post("/api/import", json={"text": "entities:\n  Thing:\n    fields:\n      x: {type: strng}\n"}).json()
    assert bad["ok"] is False and any("strng" in e for e in bad["errors"])
