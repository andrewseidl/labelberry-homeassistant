import json
import tomllib
from pathlib import Path

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
    }
    assert hacs == {"homeassistant": "2026.7.0", "name": "LabelBerry"}
    assert (INTEGRATION / "brand" / "icon.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_python_floor_matches_home_assistant() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())

    assert pyproject["project"]["requires-python"] == ">=3.14.2"
