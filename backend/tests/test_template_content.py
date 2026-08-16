from pathlib import Path

TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "_shared"

EXPECTED_TEMPLATE_FILES = [
    "pom.xml",
    ".github/workflows/ci.yml",
    "docker-compose.yml",
    ".gitignore",
    "README.md",
    "src/main/resources/application.yml",
    "src/main/resources/application-dev.yml",
    "src/main/resources/application-prod.yml",
    "src/main/resources/db/changelog/db.changelog-master.xml",
    "src/main/resources/db/changelog/001-create-example-table.sql",
    "src/main/java/{{ package_path }}/{{ app_class_name }}Application.java",
    "src/main/java/{{ package_path }}/common/entity/BaseEntity.java",
    "src/main/java/{{ package_path }}/common/dto/ApiResponse.java",
    "src/main/java/{{ package_path }}/common/dto/PageResponse.java",
    "src/main/java/{{ package_path }}/common/dto/PaginationMeta.java",
    "src/main/java/{{ package_path }}/common/util/PaginationUtils.java",
    "src/main/java/{{ package_path }}/common/util/DateTimeUtils.java",
    "src/main/java/{{ package_path }}/common/util/SlugUtils.java",
    "src/main/java/{{ package_path }}/common/util/JsonUtils.java",
    "src/main/java/{{ package_path }}/common/exception/ResourceNotFoundException.java",
    "src/main/java/{{ package_path }}/common/exception/ConflictException.java",
    "src/main/java/{{ package_path }}/common/exception/ErrorDetails.java",
    "src/main/java/{{ package_path }}/common/exception/ValidationErrorDetails.java",
    "src/main/java/{{ package_path }}/common/exception/GlobalExceptionHandler.java",
    "src/main/java/{{ package_path }}/common/config/JpaAuditingConfig.java",
    "src/main/java/{{ package_path }}/common/config/CorrelationIdFilter.java",
    "src/main/java/{{ package_path }}/common/config/OpenApiConfig.java",
    "src/main/java/{{ package_path }}/example/entity/ExampleStatus.java",
    "src/main/java/{{ package_path }}/example/entity/Example.java",
    "src/main/java/{{ package_path }}/example/dto/CreateExampleRequest.java",
    "src/main/java/{{ package_path }}/example/dto/UpdateExampleRequest.java",
    "src/main/java/{{ package_path }}/example/dto/ExampleResponse.java",
    "src/main/java/{{ package_path }}/example/mapper/ExampleMapper.java",
    "src/main/java/{{ package_path }}/example/repository/ExampleRepository.java",
    "src/main/java/{{ package_path }}/example/service/ExampleService.java",
    "src/main/java/{{ package_path }}/example/service/ExampleServiceImpl.java",
    "src/main/java/{{ package_path }}/example/controller/ExampleController.java",
    "src/test/java/{{ package_path }}/common/util/PaginationUtilsTest.java",
    "src/test/java/{{ package_path }}/common/util/DateTimeUtilsTest.java",
    "src/test/java/{{ package_path }}/common/util/SlugUtilsTest.java",
    "src/test/java/{{ package_path }}/common/util/JsonUtilsTest.java",
    "src/test/java/{{ package_path }}/common/exception/GlobalExceptionHandlerTest.java",
    "src/test/java/{{ package_path }}/common/config/CorrelationIdFilterTest.java",
    "src/test/java/{{ package_path }}/example/repository/ExampleRepositoryTest.java",
    "src/test/java/{{ package_path }}/example/mapper/ExampleMapperTest.java",
    "src/test/java/{{ package_path }}/example/service/ExampleServiceImplTest.java",
    "src/test/java/{{ package_path }}/example/controller/ExampleControllerTest.java",
]


def test_all_expected_template_files_exist():
    missing = [f for f in EXPECTED_TEMPLATE_FILES if not (TEMPLATE_DIR / f).exists()]
    assert missing == []
