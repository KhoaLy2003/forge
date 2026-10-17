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
            "template": "base-layered",
        },
        prompt_fn=fail_if_called,
    )
    assert config.project_name == "demo-service"
    assert config.target_path == Path("/tmp/out").resolve()


def test_collect_params_prompts_for_missing_fields():
    responses = iter(["demo-service", "/tmp/out", "com.example", "demo-service"])
    config = collect_params({}, prompt_fn=lambda _label: next(responses))
    assert config.group_id == "com.example"
    assert config.artifact_id == "demo-service"
    assert config.template == "base-layered"


def test_collect_params_reprompts_on_invalid_group_id():
    responses = iter(
        [
            "demo-service",
            "/tmp/out",
            "BAD_GROUP",
            "com.example",
            "demo-service",
        ]
    )
    config = collect_params({}, prompt_fn=lambda _label: next(responses))
    assert config.group_id == "com.example"


def test_collect_params_mixes_overrides_and_prompts():
    responses = iter(["/tmp/out", "com.example"])
    config = collect_params(
        {
            "project_name": "demo-service",
            "artifact_id": "demo-service",
            "template": "base-layered",
        },
        prompt_fn=lambda _label: next(responses),
    )
    assert config.target_path == Path("/tmp/out").resolve()
    assert config.group_id == "com.example"


def test_collect_params_resolves_relative_target_path():
    config = collect_params(
        {
            "project_name": "demo-service",
            "target_path": "some/relative/dir",
            "group_id": "com.example",
            "artifact_id": "demo-service",
            "template": "base-layered",
        },
        prompt_fn=lambda _label: (_ for _ in ()).throw(
            AssertionError("prompt_fn should not be called")
        ),
    )
    assert config.target_path.is_absolute()
    assert config.target_path == Path("some/relative/dir").resolve()


def test_collect_params_expands_home_in_target_path():
    config = collect_params(
        {
            "project_name": "demo-service",
            "target_path": "~/somedir",
            "group_id": "com.example",
            "artifact_id": "demo-service",
            "template": "base-layered",
        },
        prompt_fn=lambda _label: (_ for _ in ()).throw(
            AssertionError("prompt_fn should not be called")
        ),
    )
    assert "~" not in str(config.target_path)
    assert config.target_path == Path("~/somedir").expanduser().resolve()


def test_collect_params_defaults_template_when_omitted():
    """`template` is deliberately NOT wizard-prompted (see cli.py's --template default) —
    omitting it from overrides falls through to ForgeConfig's own default so existing
    flag-complete, non-interactive invocations aren't newly blocked on a prompt."""
    config = collect_params(
        {
            "project_name": "demo-service",
            "target_path": "/tmp/out",
            "group_id": "com.example",
            "artifact_id": "demo-service",
        },
        prompt_fn=lambda _label: (_ for _ in ()).throw(
            AssertionError("prompt_fn should not be called")
        ),
    )
    assert config.template == "base-layered"


# ----------------------------------------------------------------------------- entity step

import pytest
import yaml

from core.config_schema import ForgeConfig
from core.entity_spec import load_forge_yaml
from core.wizard import collect_entities, needs_prompt, save_forge_yaml


def _answers(*items):
    it = iter(items)
    return lambda _label: next(it)


def test_needs_prompt_false_when_all_four_given():
    full = {"project_name": "a", "target_path": "/t", "group_id": "com.x", "artifact_id": "a"}
    assert needs_prompt(full) is False
    assert needs_prompt({**full, "group_id": None}) is True
    assert needs_prompt({**full, "template": "base-layered"}) is False


def test_collect_entities_declined_returns_empty():
    assert collect_entities(prompt_fn=_answers("n"), print_fn=lambda *_: None) == {}
    assert collect_entities(prompt_fn=_answers(""), print_fn=lambda *_: None) == {}


def test_collect_entities_builds_fields_and_relations():
    prompt = _answers(
        "y",
        # Customer
        "Customer",
        "y", "name", "string", "100", "y",
        "y", "status", "enum", "ACTIVE, SUSPENDED", "n",
        "n",  # no more fields
        # (no earlier entities -> relation step skipped)
        "y",  # another entity
        "Purchase",
        "y", "total", "decimal", "12", "2", "y",
        "n",
        "y", "customer", "many-to-one", "Customer", "y",
        "n",
        "n",  # no more entities
    )
    entities = collect_entities(prompt_fn=prompt, print_fn=lambda *_: None)
    assert list(entities) == ["Customer", "Purchase"]
    name = entities["Customer"].fields["name"]
    assert (name.type, name.length, name.required) == ("string", 100, True)
    assert entities["Customer"].fields["status"].values == ["ACTIVE", "SUSPENDED"]
    total = entities["Purchase"].fields["total"]
    assert (total.precision, total.scale, total.required) == (12, 2, True)
    rel = entities["Purchase"].relations["customer"]
    assert (rel.type, rel.target, rel.required) == ("many-to-one", "Customer", True)


def test_collect_entities_reprompts_with_message_on_invalid_name():
    printed = []
    prompt = _answers("y", "Customers", "Customer", "n", "n")
    entities = collect_entities(prompt_fn=prompt, print_fn=printed.append)
    assert list(entities) == ["Customer"]
    assert any("singular" in m for m in printed)


def test_collect_entities_asks_for_table_when_name_is_reserved_sql_word():
    printed = []
    prompt = _answers("y", "Order", "customer_orders", "n", "n")
    entities = collect_entities(prompt_fn=prompt, print_fn=printed.append)
    assert entities["Order"].table == "customer_orders"
    assert any("reserved SQL word" in m for m in printed)


def test_collect_entities_rejects_duplicate_entity_and_bad_field_name():
    printed = []
    prompt = _answers(
        "y", "Customer", "n",
        "y", "Customer", "Product",   # duplicate -> reprompt
        "y", "id", "sku", "string", "", "n",   # 'id' collides with BaseEntity -> reprompt
        "n", "n", "n",
    )
    entities = collect_entities(prompt_fn=prompt, print_fn=printed.append)
    assert list(entities) == ["Customer", "Product"]
    assert "sku" in entities["Product"].fields
    assert any("already" in m for m in printed)
    assert any("BaseEntity" in m for m in printed)


def test_collect_entities_reprompts_on_unknown_relation_target():
    printed = []
    prompt = _answers(
        "y", "Customer", "n",
        "y", "Purchase", "n",
        "y", "customer", "many-to-one", "Nope", "Customer", "n",
        "n",
        "n",
    )
    entities = collect_entities(prompt_fn=prompt, print_fn=printed.append)
    assert entities["Purchase"].relations["customer"].target == "Customer"
    assert any("Nope" in m for m in printed)


def test_collect_entities_unknown_field_type_reprompts():
    printed = []
    prompt = _answers("y", "Customer", "y", "age", "number", "int", "n", "n", "n")
    entities = collect_entities(prompt_fn=prompt, print_fn=printed.append)
    assert entities["Customer"].fields["age"].type == "int"
    assert any("number" in m for m in printed)


def _config(tmp_path, entities=None):
    return ForgeConfig(
        project_name="demo-service", target_path=tmp_path, group_id="com.example",
        artifact_id="demo-service", entities=entities or {},
    )


def test_save_forge_yaml_round_trips(tmp_path):
    entities = collect_entities(
        prompt_fn=_answers(
            "y", "Customer",
            "y", "name", "string", "100", "y",
            "y", "status", "enum", "ACTIVE, SUSPENDED", "n",
            "n",
            "y", "Purchase", "n",
            "y", "customer", "many-to-one", "Customer", "y",
            "n", "n",
        ),
        print_fn=lambda *_: None,
    )
    config = _config(tmp_path, entities)
    path = tmp_path / "forge.yaml"
    save_forge_yaml(config, path)

    loaded = load_forge_yaml(path)
    assert loaded.entities == config.entities
    assert loaded.project_name == "demo-service"
    assert loaded.group_id == "com.example"
    assert loaded.artifact_id == "demo-service"
    assert loaded.template == "base-layered"
    assert loaded.target_path == config.target_path
    # the saved file produces an equal config again
    again = ForgeConfig(**{k: v for k, v in loaded.model_dump().items() if v is not None})
    assert again.entities == config.entities


def test_save_forge_yaml_round_trips_aliases_and_defaults(tmp_path):
    src = tmp_path / "in.yaml"
    src.write_text(
        "entities:\n"
        "  Purchase:\n"
        "    relations:\n"
        "      items: { type: one-to-many, target: PurchaseItem, mappedBy: purchase, cascade: all, orphanRemoval: true }\n"
        "  PurchaseItem:\n"
        "    table: purchase_lines\n"
        "    fields:\n"
        "      qty: { type: int, default: 1, required: true }\n"
        "    relations:\n"
        "      purchase: { type: many-to-one, target: Purchase, required: true }\n",
        encoding="utf-8",
    )
    entities = load_forge_yaml(src).entities
    config = _config(tmp_path, entities)
    out = tmp_path / "out.yaml"
    save_forge_yaml(config, out)
    assert load_forge_yaml(out).entities == entities


def test_save_forge_yaml_omits_entities_when_empty(tmp_path):
    out = tmp_path / "forge.yaml"
    save_forge_yaml(_config(tmp_path), out)
    data = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert "entities" not in data
    assert data["project_name"] == "demo-service"
    assert load_forge_yaml(out).entities == {}
