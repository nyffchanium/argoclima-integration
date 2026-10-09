"""Coverage for migrating entities of older versions to the current unique_id.

Users switching from nyffchanium/argoclima-integration keep their config
entries (same domain), but entity unique_ids were built differently
there. Without migration every entity would be duplicated and the old
ones (history, names, automations) orphaned.
"""

import hashlib
import importlib.util
import re
import sys
import types
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARGOCLIMA_COMPONENT = ROOT / "custom_components" / "argoclima"


def _load_unique_id_module():
    for name in list(sys.modules):
        if name.startswith("custom_components"):
            del sys.modules[name]
    custom_components = types.ModuleType("custom_components")
    custom_components.__path__ = [str(ROOT / "custom_components")]
    argoclima = types.ModuleType("custom_components.argoclima")
    argoclima.__path__ = [str(ARGOCLIMA_COMPONENT)]
    sys.modules["custom_components"] = custom_components
    sys.modules["custom_components.argoclima"] = argoclima

    spec = importlib.util.spec_from_file_location(
        "custom_components.argoclima.unique_id",
        ARGOCLIMA_COMPONENT / "unique_id.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _upstream_unique_id(entry_id: str, title: str, entity_name: str) -> str:
    # Verbatim from nyffchanium/argoclima-integration entity.py, where
    # self.name is f"{self._entry.title} {self._entity_name}".
    name = f"{title} {entity_name}"
    return uuid.UUID(hashlib.md5((entry_id + name).encode("utf-8")).hexdigest()).hex


ENTRY_ID = "01JABCDEF0123456789ABCDEFG"
TITLE = "Wohnzimmer"
CPU_ID = "A1B2C3D4E5F6"


class LegacyUniqueIdMigrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.unique_id = _load_unique_id_module()

    def test_entity_names_match_platforms(self) -> None:
        found = set()
        for platform in ("climate", "switch", "number", "select"):
            source = (ARGOCLIMA_COMPONENT / f"{platform}.py").read_text()
            found.update(
                re.findall(r'ArgoEntity\.__init__\(\s*self,\s*"([^"]+)"', source)
            )
        self.assertEqual(set(self.unique_id.ENTITY_NAMES), found)

    def test_migrates_upstream_ids(self) -> None:
        registered = {
            _upstream_unique_id(ENTRY_ID, TITLE, name)
            for name in self.unique_id.ENTITY_NAMES
        }
        migrations = self.unique_id.legacy_unique_id_migrations(
            ENTRY_ID, TITLE, None, registered
        )
        self.assertEqual(
            {
                _upstream_unique_id(
                    ENTRY_ID, TITLE, name
                ): self.unique_id.entity_unique_id(ENTRY_ID, name)
                for name in self.unique_id.ENTITY_NAMES
            },
            migrations,
        )

    def test_migrates_cpu_id_based_ids(self) -> None:
        old_id = self.unique_id.entity_unique_id(CPU_ID, "Climate")
        migrations = self.unique_id.legacy_unique_id_migrations(
            ENTRY_ID, TITLE, CPU_ID, {old_id}
        )
        self.assertEqual(
            {old_id: self.unique_id.entity_unique_id(ENTRY_ID, "Climate")},
            migrations,
        )

    def test_prefers_cpu_id_based_over_upstream_id(self) -> None:
        upstream_id = _upstream_unique_id(ENTRY_ID, TITLE, "Climate")
        cpu_id_based = self.unique_id.entity_unique_id(CPU_ID, "Climate")
        migrations = self.unique_id.legacy_unique_id_migrations(
            ENTRY_ID, TITLE, CPU_ID, {upstream_id, cpu_id_based}
        )
        self.assertEqual([cpu_id_based], list(migrations))

    def test_leaves_existing_current_entity_alone(self) -> None:
        registered = {
            _upstream_unique_id(ENTRY_ID, TITLE, "Climate"),
            self.unique_id.entity_unique_id(ENTRY_ID, "Climate"),
        }
        migrations = self.unique_id.legacy_unique_id_migrations(
            ENTRY_ID, TITLE, None, registered
        )
        self.assertEqual({}, migrations)

    def test_current_ids_need_no_migration(self) -> None:
        registered = {
            self.unique_id.entity_unique_id(ENTRY_ID, name)
            for name in self.unique_id.ENTITY_NAMES
        }
        migrations = self.unique_id.legacy_unique_id_migrations(
            ENTRY_ID, TITLE, CPU_ID, registered
        )
        self.assertEqual({}, migrations)

    def test_ignores_ids_of_another_title(self) -> None:
        # Upstream ids include the title; an id built from a title the
        # entry no longer has belongs to an already orphaned entity.
        registered = {_upstream_unique_id(ENTRY_ID, "Schlafzimmer", "Climate")}
        migrations = self.unique_id.legacy_unique_id_migrations(
            ENTRY_ID, TITLE, None, registered
        )
        self.assertEqual({}, migrations)


if __name__ == "__main__":
    unittest.main()
