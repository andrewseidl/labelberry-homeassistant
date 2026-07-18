import json
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components" / "labelberry"


def test_hacs_repository_metadata_is_complete() -> None:
    manifest = json.loads((INTEGRATION / "manifest.json").read_text())
    hacs = json.loads((ROOT / "hacs.json").read_text())

    assert manifest == {
        "codeowners": ["@andrewseidl"],
        "config_flow": True,
        "documentation": "https://github.com/andrewseidl/labelberry-homeassistant",
        "domain": "labelberry",
        "integration_type": "device",
        "iot_class": "local_polling",
        "issue_tracker": "https://github.com/andrewseidl/labelberry-homeassistant/issues",
        "name": "LabelBerry",
        "requirements": [],
        "single_config_entry": True,
        "version": "0.1.0",
        "zeroconf": ["_labelberry._tcp.local."],
    }
    assert list(manifest) == [
        "domain",
        "name",
        "codeowners",
        "config_flow",
        "documentation",
        "integration_type",
        "iot_class",
        "issue_tracker",
        "requirements",
        "single_config_entry",
        "version",
        "zeroconf",
    ]
    assert hacs == {"homeassistant": "2026.7.0", "name": "LabelBerry"}
    assert (INTEGRATION / "brand" / "icon.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert (ROOT / "LICENSE").read_text().startswith("MIT License\n")


def test_python_floor_matches_home_assistant() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())

    assert pyproject["project"]["requires-python"] == ">=3.14.2"


def test_distribution_documentation_is_complete() -> None:
    readme = (ROOT / "README.md").read_text()

    assert "https://github.com/andrewseidl/labelberry-homeassistant" in readme
    assert "labelberry.print_label" in readme
    assert "left" in readme
    assert "right" in readme
    assert "text: |\n    Cold\n    Wash" in readme
    assert not (INTEGRATION / "strings.json").exists()


def test_github_workflows_cover_tests_and_distribution_validation() -> None:
    test_workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "test.yml").read_text())
    validate_workflow = yaml.safe_load(
        (ROOT / ".github" / "workflows" / "validate.yml").read_text()
    )

    test_steps = test_workflow["jobs"]["test"]["steps"]
    test_commands = "\n".join(step.get("run", "") for step in test_steps)
    assert "uv sync --frozen" in test_commands
    assert "uv run ruff check ." in test_commands
    assert "uv run ruff format --check ." in test_commands
    assert "uv run pytest" in test_commands

    test_actions = {step.get("uses") for step in test_steps}
    assert "actions/checkout@v6" in test_actions
    assert "astral-sh/setup-uv@08807647e7069bb48b6ef5acd8ec9567f424441b" in test_actions

    validate_steps = [
        step for job in validate_workflow["jobs"].values() for step in job.get("steps", [])
    ]
    hacs_step = next(step for step in validate_steps if step.get("uses") == "hacs/action@main")
    assert hacs_step["with"]["category"] == "integration"
    assert any(
        step.get("uses") == "home-assistant/actions/hassfest@master" for step in validate_steps
    )
    assert any(step.get("uses") == "actions/checkout@v6" for step in validate_steps)
