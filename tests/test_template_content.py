from pathlib import Path

TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "base-layered"

EXPECTED_TEMPLATE_FILES = [
    "pom.xml",
    "docker-compose.yml",
    ".gitignore",
    "README.md",
    "src/main/resources/application.yml",
    "src/main/resources/db/changelog/db.changelog-master.xml",
    "src/main/resources/db/changelog/001-create-example-table.sql",
    "src/main/java/{{ package_path }}/{{ app_class_name }}Application.java",
    "src/main/java/{{ package_path }}/entity/Example.java",
    "src/main/java/{{ package_path }}/repository/ExampleRepository.java",
    "src/main/java/{{ package_path }}/service/ExampleService.java",
    "src/main/java/{{ package_path }}/controller/ExampleController.java",
]


def test_all_expected_template_files_exist():
    missing = [f for f in EXPECTED_TEMPLATE_FILES if not (TEMPLATE_DIR / f).exists()]
    assert missing == []
