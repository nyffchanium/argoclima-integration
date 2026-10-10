import json
import re
from pathlib import Path

COMPONENT = Path(__file__).parents[1] / "custom_components" / "argoclima"
TRANSLATIONS = COMPONENT / "translations"


def keys(data: dict, prefix: str = "") -> set[str]:
    result = set()
    for key, value in data.items():
        path = f"{prefix}.{key}" if prefix else key
        result |= keys(value, path) if isinstance(value, dict) else {path}
    return result


def test_languages_have_the_same_keys() -> None:
    en = json.loads((TRANSLATIONS / "en.json").read_text())
    de = json.loads((TRANSLATIONS / "de.json").read_text())

    assert keys(en) == keys(de)


def test_entities_have_translated_names() -> None:
    en = json.loads((TRANSLATIONS / "en.json").read_text())
    for platform in ("switch", "number", "select", "update"):
        source = (COMPONENT / f"{platform}.py").read_text()
        for name in re.findall(r'super\(\).__init__\(\s*"([^"]+)"', source):
            key = name.lower().replace(" ", "_")
            assert "name" in en["entity"][platform][key], key
