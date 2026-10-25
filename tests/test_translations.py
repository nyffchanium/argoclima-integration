import json
import re
from pathlib import Path

import pytest

from custom_components.argoclima.switch import ANTI_MOLD_MODE_NAMES

COMPONENT = Path(__file__).parents[1] / "custom_components" / "argoclima"
TRANSLATIONS = COMPONENT / "translations"


def keys(data: dict, prefix: str = "") -> set[str]:
    result = set()
    for key, value in data.items():
        path = f"{prefix}.{key}" if prefix else key
        result |= keys(value, path) if isinstance(value, dict) else {path}
    return result


def placeholders(data: dict) -> dict[str, set[str]]:
    result = {}
    for key, value in data.items():
        if isinstance(value, dict):
            result |= {f"{key}.{k}": v for k, v in placeholders(value).items()}
        else:
            result[key] = set(re.findall(r"{(\w+)}", value))
    return result


@pytest.mark.parametrize(
    "path",
    [p for p in sorted(TRANSLATIONS.glob("*.json")) if p.name != "en.json"],
    ids=lambda p: p.stem,
)
def test_translation_matches_english(path: Path) -> None:
    en = json.loads((TRANSLATIONS / "en.json").read_text())
    translation = json.loads(path.read_text())

    assert keys(translation) == keys(en)
    assert placeholders(translation) == placeholders(en)


def test_entities_have_translated_names() -> None:
    en = json.loads((TRANSLATIONS / "en.json").read_text())
    for platform in ("switch", "number", "select", "update", "binary_sensor", "sensor"):
        source = (COMPONENT / f"{platform}.py").read_text()
        names = re.findall(r'super\(\).__init__\(\s*"([^"]+)"', source)
        if platform == "switch":
            names += ANTI_MOLD_MODE_NAMES.values()
        for name in names:
            key = name.lower().replace(" ", "_")
            assert "name" in en["entity"][platform][key], key


def test_icons_belong_to_translated_entities() -> None:
    en = json.loads((TRANSLATIONS / "en.json").read_text())
    icons = json.loads((COMPONENT / "icons.json").read_text())

    for platform, entities in icons["entity"].items():
        for key in entities:
            assert key in en["entity"][platform], f"{platform}.{key}"
    assert icons["services"].keys() <= en["services"].keys()
