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
        template="base-layered",
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
        "template",
        "use_liquibase",
        "include_monitoring",
        "has_entities",
        "entities",
        "join_tables",
        "fk_constraints",
        "changelog_start",
        "changelog_files",
        "constraints_changelog_file",
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


def test_validate_group_id_rejects_reserved_java_keyword():
    with pytest.raises(ValueError, match="reserved"):
        validate_group_id("com.new")


def test_validate_group_id_accepts_non_reserved_segments():
    assert validate_group_id("com.example") == "com.example"


def test_validate_artifact_id_rejects_reserved_java_keyword():
    with pytest.raises(ValueError, match="reserved"):
        validate_artifact_id("class")


def test_validate_artifact_id_accepts_non_reserved_id():
    assert validate_artifact_id("my-service") == "my-service"


def test_validate_artifact_id_accepts_id_that_is_only_reserved_before_hyphen_strip():
    # "my-class" strips to "myclass", which is not a reserved word.
    assert validate_artifact_id("my-class") == "my-class"


def test_template_context_includes_use_liquibase_flag_true_for_base_layered():
    config = ForgeConfig(project_name="demo", target_path=Path("."), group_id="com.example", artifact_id="demo", template="base-layered")
    assert config.template_context()["use_liquibase"] is True


def test_template_context_includes_use_liquibase_flag_false_for_minimal():
    config = ForgeConfig(project_name="demo", target_path=Path("."), group_id="com.example", artifact_id="demo", template="minimal")
    assert config.template_context()["use_liquibase"] is False


def test_template_context_includes_include_monitoring_flag_true_for_base_layered():
    config = ForgeConfig(project_name="demo", target_path=Path("."), group_id="com.example", artifact_id="demo", template="base-layered")
    assert config.include_monitoring is True
    assert config.template_context()["include_monitoring"] is True


def test_template_context_includes_include_monitoring_flag_false_for_minimal():
    config = ForgeConfig(project_name="demo", target_path=Path("."), group_id="com.example", artifact_id="demo", template="minimal")
    assert config.include_monitoring is False
    assert config.template_context()["include_monitoring"] is False


def test_unknown_template_raises_validation_error():
    with pytest.raises(ValidationError):
        ForgeConfig(project_name="demo", target_path=Path("."), group_id="com.example", artifact_id="demo", template="nonexistent")


# ---------------------------------------------------------------- entities

from core.entity_spec import EntitySpec, FieldSpec, RelationSpec  # noqa: E402


def _entity(name, table=None, fields=None, relations=None):
    return EntitySpec(
        name=name,
        table=table,
        fields={k: FieldSpec(**v) for k, v in (fields or {}).items()},
        relations={k: RelationSpec(**v) for k, v in (relations or {}).items()},
    )


def _customer_order():
    return {
        "Customer": _entity("Customer", fields={"name": {"type": "string", "required": True}}),
        "Order": _entity(
            "Order",
            table="customer_orders",
            relations={"customer": {"type": "many-to-one", "target": "Customer", "required": True, "inverse": "orders"}},
        ),
    }


def test_no_entities_context_has_empty_entity_keys_and_unchanged_old_keys():
    context = make_config().template_context()
    assert context["has_entities"] is False
    assert context["entities"] == []
    assert context["join_tables"] == []
    assert context["fk_constraints"] == []
    assert context["changelog_start"] == 3
    assert context["changelog_files"] == ["001-create-example-table.sql", "002-create-notifications.sql"]
    assert context["project_name"] == "demo-service"
    assert context["base_package"] == "com.example.demoservice"
    assert context["use_liquibase"] is True


def test_has_entities_property():
    assert make_config().has_entities is False
    assert make_config(entities=_customer_order()).has_entities is True


def test_entities_exposed_in_topological_order():
    # declared Order first, but Order depends on Customer
    entities = _customer_order()
    config = make_config(entities=dict(reversed(list(entities.items()))))
    context = config.template_context()
    assert context["has_entities"] is True
    assert [e.name for e in context["entities"]] == ["Customer", "Order"]
    assert context["changelog_files"] == [
        "002-create-notifications.sql",
        "003-create-customers-table.sql",
        "004-create-customer_orders-table.sql",
    ]


def test_context_objects_work_with_strict_undefined():
    import jinja2

    env = jinja2.Environment(undefined=jinja2.StrictUndefined)
    template = env.from_string(
        "{% for e in entities %}{{ e.name }}:{{ e.table }}:{% for f in e.fields %}{{ f.column }}{% endfor %};{% endfor %}"
    )
    assert template.render(**make_config(entities=_customer_order()).template_context()) == "Customer:customers:name;Order:customer_orders:;"


def test_invalid_entities_raise_one_validation_error_with_all_messages():
    entities = {
        "Order": _entity("Order"),
        "Thing": _entity("Thing", relations={"owner": {"type": "many-to-one", "target": "Nobody"}}),
    }
    with pytest.raises(ValidationError) as exc:
        make_config(entities=entities)
    message = str(exc.value)
    assert "reserved SQL word" in message and "Nobody" in message


def test_required_cycle_rejected_by_config():
    entities = {
        "Alpha": _entity("Alpha", relations={"b": {"type": "many-to-one", "target": "Beta", "required": True}}),
        "Beta": _entity("Beta", relations={"a": {"type": "many-to-one", "target": "Alpha", "required": True}}),
    }
    with pytest.raises(ValidationError, match="cycle between Alpha, Beta"):
        make_config(entities=entities)


def test_minimal_template_with_entities_rejected():
    with pytest.raises(ValidationError, match="minimal"):
        make_config(template="minimal", entities=_customer_order())


def test_minimal_template_without_entities_still_fine():
    config = make_config(template="minimal")
    assert config.template_context()["has_entities"] is False
