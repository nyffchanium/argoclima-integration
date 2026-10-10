import re
from pathlib import Path

from custom_components.argoclima.unique_id import ENTITY_NAMES
from custom_components.argoclima.unique_id import entity_unique_id
from custom_components.argoclima.unique_id import legacy_unique_id_migrations

from .test_init import upstream_unique_id

COMPONENT = Path(__file__).parents[1] / "custom_components" / "argoclima"
ENTRY_ID = "01JABCDEF0123456789ABCDEFG"
TITLE = "Living Room"
CPU_ID = "A1B2C3D4E5F6"


def test_entity_names_match_platforms() -> None:
    found = set()
    for platform in (
        "climate",
        "switch",
        "number",
        "select",
        "update",
        "binary_sensor",
    ):
        source = (COMPONENT / f"{platform}.py").read_text()
        found.update(re.findall(r'super\(\).__init__\(\s*"([^"]+)"', source))
    assert found == set(ENTITY_NAMES)


def test_migrates_upstream_ids() -> None:
    registered = {upstream_unique_id(ENTRY_ID, TITLE, name) for name in ENTITY_NAMES}

    assert legacy_unique_id_migrations(ENTRY_ID, TITLE, None, registered) == {
        upstream_unique_id(ENTRY_ID, TITLE, name): entity_unique_id(ENTRY_ID, name)
        for name in ENTITY_NAMES
    }


def test_prefers_cpu_id_based_id_over_upstream_id() -> None:
    upstream = upstream_unique_id(ENTRY_ID, TITLE, "Climate")
    cpu_id_based = entity_unique_id(CPU_ID, "Climate")

    migrations = legacy_unique_id_migrations(
        ENTRY_ID, TITLE, CPU_ID, {upstream, cpu_id_based}
    )

    assert migrations == {cpu_id_based: entity_unique_id(ENTRY_ID, "Climate")}


def test_current_ids_need_no_migration() -> None:
    registered = {entity_unique_id(ENTRY_ID, name) for name in ENTITY_NAMES}

    assert legacy_unique_id_migrations(ENTRY_ID, TITLE, CPU_ID, registered) == {}


def test_ignores_ids_built_from_another_title() -> None:
    registered = {upstream_unique_id(ENTRY_ID, "Bedroom", "Climate")}

    assert legacy_unique_id_migrations(ENTRY_ID, TITLE, None, registered) == {}
