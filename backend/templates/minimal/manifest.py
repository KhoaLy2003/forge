"""Exclude-glob manifest for the minimal template — drops Liquibase migrations and the
Testcontainers-backed repository test; keeps the example CRUD slice and MapStruct."""

EXCLUDES: tuple[str, ...] = (
    "src/main/resources/db/changelog/*",
    "src/test/java/{{ package_path }}/example/repository/ExampleRepositoryTest.java",
    "src/test/java/{{ package_path }}/common/config/ManagementConfigTest.java",
    "observability/*",
    "docker-compose.observability.yml",
    "docs/observability/runbook.md",
    "src/main/java/{{ package_path }}/notification/*",
    "src/test/java/{{ package_path }}/notification/*",
)
