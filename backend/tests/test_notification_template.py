"""Rendered-output checks for the notification module (no Maven, no Docker)."""

import re
from pathlib import Path

MIGRATION = "src/main/resources/db/changelog/002-create-notifications.sql"
MAIN = "src/main/java/com/example/demoservice/notification"
TEST = "src/test/java/com/example/demoservice/notification"


def _read(project: Path, relative: str) -> str:
    return (project / relative).read_text(encoding="utf-8")


def test_migration_creates_the_four_notification_tables(rendered):
    sql = _read(rendered["base-layered"], MIGRATION)

    for table in ("notification_templates", "notifications", "deliveries", "notification_preferences"):
        assert re.search(rf"CREATE TABLE {table}\b", sql), table


def test_migration_does_not_include_push_or_device_tokens_or_all_audience(rendered):
    sql = _read(rendered["base-layered"], MIGRATION)

    assert "device_tokens" not in sql
    assert "push_enabled" not in sql
    assert "'push'" not in sql
    assert "fanout" not in sql
    assert "'all'" not in sql


def test_migration_restricts_channels_to_in_app_and_email(rendered):
    sql = _read(rendered["base-layered"], MIGRATION)

    assert "channel IN ('in_app', 'email')" in sql


def test_migration_has_idempotency_unique_index_and_delivery_uniqueness(rendered):
    sql = _read(rendered["base-layered"], MIGRATION)

    assert re.search(
        r"CREATE UNIQUE INDEX uq_notifications_idempotency_key\s+ON notifications \(idempotency_key\) WHERE idempotency_key IS NOT NULL",
        sql,
    )
    assert "uq_deliveries_notification_recipient_channel" in sql
    assert "(notification_id, recipient_id, channel)" in sql


def test_migration_does_not_reference_a_users_table_from_deliveries(rendered):
    sql = _read(rendered["base-layered"], MIGRATION)
    deliveries = sql[sql.index("CREATE TABLE deliveries"): sql.index("CREATE TABLE notification_preferences")]

    assert "recipient_id" in deliveries
    assert not re.search(r"recipient_id\s+UUID\s+NOT NULL\s+REFERENCES", deliveries)
    assert deliveries.count("REFERENCES") == 1  # only notification_id -> notifications


def test_migration_has_a_dismissed_at_and_provider_message_id_on_deliveries(rendered):
    sql = _read(rendered["base-layered"], MIGRATION)

    assert "dismissed_at" in sql
    assert "provider_message_id" in sql


def test_migration_seeds_a_welcome_template_for_in_app_and_email_in_english(rendered):
    sql = _read(rendered["base-layered"], MIGRATION)

    assert "INSERT INTO notification_templates" in sql
    assert "('welcome', 'in_app', 'en'" in sql
    assert "('welcome', 'email', 'en'" in sql
    assert "{{name}}" in sql  # a literal placeholder, not consumed by Jinja
    assert "{%" not in sql


def test_migration_has_a_rollback_for_every_table(rendered):
    sql = _read(rendered["base-layered"], MIGRATION)

    rollbacks = re.findall(r"^-- rollback (.+)$", sql, re.MULTILINE)
    assert len(rollbacks) >= 4
    joined = "\n".join(rollbacks)
    for table in ("notification_templates", "notifications", "deliveries", "notification_preferences"):
        assert f"DROP TABLE {table}" in joined


def test_master_changelog_includes_notifications_after_the_example_table(rendered):
    master = _read(rendered["base-layered"], "src/main/resources/db/changelog/db.changelog-master.xml")

    first = master.index("001-create-example-table.sql")
    second = master.index("002-create-notifications.sql")
    assert first < second


def test_minimal_has_no_changelog_at_all(rendered):
    assert not (rendered["minimal"] / "src/main/resources/db/changelog").exists()


def test_base_layered_has_mail_starter_scheduling_and_notification_settings(rendered):
    base = rendered["base-layered"]

    assert "spring-boot-starter-mail" in _read(base, "pom.xml")
    app = _read(base, "src/main/java/com/example/demoservice/DemoServiceApplication.java")
    assert "@EnableScheduling" in app
    assert "import org.springframework.scheduling.annotation.EnableScheduling;" in app

    config = _read(base, "src/main/resources/application.yml")
    for expected in (
        "worker-delay-ms: 3000",
        "batch-size: 100",
        "lease-seconds: 300",
        "max-attempts: 5",
        "default-locale: en",
        "host: ${MAIL_HOST:}",
        "port: ${MAIL_PORT:587}",
        "username: ${MAIL_USERNAME:}",
        "password: ${MAIL_PASSWORD:}",
        "from: ${MAIL_FROM:}",
        "starttls: ${MAIL_STARTTLS:true}",
    ):
        assert expected in config, expected


def test_minimal_has_no_mail_starter_scheduling_or_notification_settings(rendered):
    minimal = rendered["minimal"]

    assert "spring-boot-starter-mail" not in _read(minimal, "pom.xml")
    app = _read(minimal, "src/main/java/com/example/demoservice/DemoServiceApplication.java")
    assert "EnableScheduling" not in app
    config = _read(minimal, "src/main/resources/application.yml")
    assert "notifications:" not in config
    assert "MAIL_HOST" not in config


def test_application_yml_parses_with_notification_settings(rendered):
    import yaml

    for project in rendered.values():
        yaml.safe_load(_read(project, "src/main/resources/application.yml"))


def test_base_layered_readme_documents_the_notification_module(rendered):
    readme = _read(rendered["base-layered"], "README.md")

    assert "## Notifications" in readme
    assert "`{{name}}`" in readme  # the placeholder syntax is shown literally, not consumed by Jinja
    for expected in ("RecipientDirectory", "CurrentRecipientProvider", "ChannelSender", "MAIL_HOST"):
        assert expected in readme, expected
    assert "{%" not in readme


def test_minimal_readme_does_not_mention_the_notification_module(rendered):
    readme = _read(rendered["minimal"], "README.md")

    assert "Notifications" not in readme
    assert "RecipientDirectory" not in readme
    assert "{%" not in readme


def test_base_layered_ships_the_worker_switch_in_the_default_configuration(rendered):
    import yaml

    config = yaml.safe_load(_read(rendered["base-layered"], "src/main/resources/application.yml"))

    assert config["app"]["notifications"]["worker-enabled"] is True
    assert config["app"]["notifications"]["default-locale"] == "en"
