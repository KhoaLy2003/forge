"""Shared fixtures for the Forge backend tests."""

from pathlib import Path

import pytest

from core.config_schema import ForgeConfig
from core.renderer import render_tree
from core.templates import SHARED_DIR, discover_templates


@pytest.fixture(scope="session")
def rendered(tmp_path_factory) -> dict[str, Path]:
    """Each registered template rendered once (group com.example, artifact demo-service)."""
    projects = {}
    for template in sorted(discover_templates()):
        config = ForgeConfig(
            project_name="demo-service",
            target_path=tmp_path_factory.mktemp(template),
            group_id="com.example",
            artifact_id="demo-service",
            template=template,
        )
        render_tree(
            SHARED_DIR,
            config.target_dir,
            config.template_context(),
            excluded=discover_templates()[template],
        )
        projects[template] = config.target_dir
    return projects
