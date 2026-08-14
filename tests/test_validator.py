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


def test_run_compile_fails_for_broken_java_test_source(tmp_path):
    (tmp_path / "pom.xml").write_text(MINIMAL_POM, encoding="utf-8")
    main_dir = tmp_path / "src" / "main" / "java" / "com" / "example"
    main_dir.mkdir(parents=True)
    (main_dir / "Hello.java").write_text(MINIMAL_JAVA, encoding="utf-8")
    test_dir = tmp_path / "src" / "test" / "java" / "com" / "example"
    test_dir.mkdir(parents=True)
    (test_dir / "HelloTest.java").write_text("this is not valid java", encoding="utf-8")

    result = run_compile(tmp_path)

    assert result.passed is False
    assert result.details
