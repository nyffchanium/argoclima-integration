"""Regression coverage for the hub-child device identity fix.

Each hub-child device must keep the same permanent key for its whole
lifetime once it's added, even after its real CPU_ID becomes known
later (e.g. a device that was added manually by host only, and starts
pushing its CPU_ID afterwards). Before this fix, that key was derived
from the CPU_ID itself and got swapped out the moment the real CPU_ID
showed up, which changed every entity's unique_id and orphaned the
old entities. See entity.py's use of ArgoRuntimeDevice.device_id.
"""

import importlib.util
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARGOCLIMA_COMPONENT = ROOT / "custom_components" / "argoclima"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _drop_argoclima_modules() -> None:
    for name in list(sys.modules):
        if name.startswith("custom_components") or name.startswith("homeassistant"):
            del sys.modules[name]


def _install_argoclima_package_stub() -> None:
    custom_components = types.ModuleType("custom_components")
    custom_components.__path__ = [str(ROOT / "custom_components")]
    argoclima = types.ModuleType("custom_components.argoclima")
    argoclima.__path__ = [str(ARGOCLIMA_COMPONENT)]
    sys.modules["custom_components"] = custom_components
    sys.modules["custom_components.argoclima"] = argoclima


def _load_argoclima_module(module_name: str):
    spec = importlib.util.spec_from_file_location(
        f"custom_components.argoclima.{module_name}",
        ARGOCLIMA_COMPONENT / f"{module_name}.py",
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load argoclima module: {module_name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _install_runtime_dependency_stubs() -> None:
    device_type_module = types.ModuleType("custom_components.argoclima.device_type")

    class ArgoDeviceType:
        pass

    device_type_module.ArgoDeviceType = ArgoDeviceType

    update_coordinator_module = types.ModuleType(
        "custom_components.argoclima.update_coordinator"
    )

    class ArgoDataUpdateCoordinator:
        pass

    update_coordinator_module.ArgoDataUpdateCoordinator = ArgoDataUpdateCoordinator

    homeassistant = types.ModuleType("homeassistant")
    homeassistant.__path__ = []
    config_entries_module = types.ModuleType("homeassistant.config_entries")

    class ConfigEntry:
        pass

    config_entries_module.ConfigEntry = ConfigEntry

    core_module = types.ModuleType("homeassistant.core")
    core_module.HomeAssistant = object

    sys.modules.update(
        {
            device_type_module.__name__: device_type_module,
            update_coordinator_module.__name__: update_coordinator_module,
            "homeassistant": homeassistant,
            config_entries_module.__name__: config_entries_module,
            core_module.__name__: core_module,
        }
    )


class FakeConfigEntry:
    def __init__(self, entry_id: str, data: dict) -> None:
        self.entry_id = entry_id
        self.data = data


class FakeConfigEntries:
    """Mimics hass.config_entries.async_update_entry mutating entry.data."""

    def async_update_entry(self, entry: FakeConfigEntry, data: dict) -> None:
        entry.data = data


class FakeHass:
    def __init__(self) -> None:
        self.config_entries = FakeConfigEntries()


class HubDeviceIdentityTest(unittest.TestCase):
    def setUp(self) -> None:
        _drop_argoclima_modules()
        _install_argoclima_package_stub()
        _install_runtime_dependency_stubs()
        _load_argoclima_module("const")
        self.runtime = _load_argoclima_module("runtime")
        self.hass = FakeHass()
        self.const = sys.modules["custom_components.argoclima.const"]

    def test_match_by_cpu_id_takes_priority(self) -> None:
        devices = {
            "key-a": {self.const.CONF_CPU_ID: "ABC123", self.const.CONF_HOST: "10.0.0.5"},
        }
        matched = self.runtime.match_hub_device_id(devices, "ABC123", "10.0.0.9")
        self.assertEqual("key-a", matched)

    def test_match_by_host_only_against_unidentified_device(self) -> None:
        devices = {
            "key-a": {self.const.CONF_CPU_ID: None, self.const.CONF_HOST: "10.0.0.5"},
        }
        matched = self.runtime.match_hub_device_id(devices, "ABC123", "10.0.0.5")
        self.assertEqual("key-a", matched)

    def test_no_match_by_host_against_a_different_known_device(self) -> None:
        # Device at key-a is already identified as DEF456. A push
        # claiming a different CPU_ID (ABC123) at the same host must
        # not be merged into it.
        devices = {
            "key-a": {self.const.CONF_CPU_ID: "DEF456", self.const.CONF_HOST: "10.0.0.5"},
        }
        matched = self.runtime.match_hub_device_id(devices, "ABC123", "10.0.0.5")
        self.assertIsNone(matched)

    def test_no_match_returns_none(self) -> None:
        devices = {}
        self.assertIsNone(self.runtime.match_hub_device_id(devices, "ABC123", "10.0.0.5"))

    def test_device_keeps_its_key_once_identified_by_push(self) -> None:
        """The actual bug scenario this fix addresses end-to-end."""
        hub_entry = FakeConfigEntry("hub1", data={self.const.CONF_DEVICES: {}})

        # 1. Manually added via config_flow: host known, CPU_ID not yet.
        first_key = self.runtime.async_update_hub_device(
            self.hass,
            hub_entry,
            {
                self.const.CONF_HOST: "10.0.0.5",
                self.const.CONF_NAME: "Living Room",
            },
        )

        # 2. The device pushes its real CPU_ID for the first time.
        second_key = self.runtime.async_update_hub_device(
            self.hass,
            hub_entry,
            {
                self.const.CONF_HOST: "10.0.0.5",
                self.const.CONF_CPU_ID: "ABC123",
            },
        )

        self.assertEqual(
            first_key,
            second_key,
            "the device's permanent key must not change once its CPU_ID becomes known",
        )
        devices = hub_entry.data[self.const.CONF_DEVICES]
        self.assertEqual(1, len(devices), "no duplicate device record should be created")
        self.assertEqual("ABC123", devices[first_key][self.const.CONF_CPU_ID])

        # 3. Further pushes with the now-known CPU_ID keep matching too.
        third_key = self.runtime.async_update_hub_device(
            self.hass,
            hub_entry,
            {
                self.const.CONF_HOST: "10.0.0.6",  # device got a new DHCP lease
                self.const.CONF_CPU_ID: "ABC123",
            },
        )
        self.assertEqual(first_key, third_key)
        self.assertEqual(1, len(hub_entry.data[self.const.CONF_DEVICES]))

    def test_new_device_gets_its_own_key(self) -> None:
        hub_entry = FakeConfigEntry("hub1", data={self.const.CONF_DEVICES: {}})

        key_a = self.runtime.async_update_hub_device(
            self.hass, hub_entry, {self.const.CONF_HOST: "10.0.0.5"}
        )
        key_b = self.runtime.async_update_hub_device(
            self.hass, hub_entry, {self.const.CONF_HOST: "10.0.0.6"}
        )

        self.assertNotEqual(key_a, key_b)
        self.assertEqual(2, len(hub_entry.data[self.const.CONF_DEVICES]))

    def test_stale_duplicate_host_record_is_removed(self) -> None:
        hub_entry = FakeConfigEntry(
            "hub1",
            data={
                self.const.CONF_DEVICES: {
                    "stale-key": {
                        self.const.CONF_CPU_ID: None,
                        self.const.CONF_HOST: "10.0.0.5",
                    }
                }
            },
        )

        # A genuinely new device record (no CPU_ID/host match path taken
        # by the caller, e.g. a fresh discovered device) that happens to
        # reuse the same host should not leave the stale record behind.
        new_key = "fresh-key-from-discovery"
        hub_entry.data[self.const.CONF_DEVICES][new_key] = {}
        self.runtime._remove_duplicate_hosts(
            hub_entry.data[self.const.CONF_DEVICES], new_key, "10.0.0.5"
        )

        self.assertNotIn("stale-key", hub_entry.data[self.const.CONF_DEVICES])
        self.assertIn(new_key, hub_entry.data[self.const.CONF_DEVICES])


class RuntimeDevicesForEntryIdentityTest(unittest.TestCase):
    """A standalone device's unique_id must never depend on its CPU_ID."""

    def setUp(self) -> None:
        _drop_argoclima_modules()
        _install_argoclima_package_stub()
        _install_runtime_dependency_stubs()
        _load_argoclima_module("const")
        self.runtime = _load_argoclima_module("runtime")
        self.const = sys.modules["custom_components.argoclima.const"]

    def test_standalone_device_id_is_entry_id_regardless_of_cpu_id(self) -> None:
        device_type_module = sys.modules["custom_components.argoclima.device_type"]
        device_type_module.ArgoDeviceType.from_name = staticmethod(lambda name: object())

        update_coordinator_module = sys.modules[
            "custom_components.argoclima.update_coordinator"
        ]

        class FakeCoordinator(update_coordinator_module.ArgoDataUpdateCoordinator):
            pass

        coordinator = FakeCoordinator()

        hass = FakeHass()
        hass.data = {self.const.DOMAIN: {"entry-1": coordinator}}

        entry = FakeConfigEntry(
            "entry-1",
            data={self.const.CONF_DEVICE_TYPE: "whatever"},
        )
        entry.title = "Living Room Argoclima"

        devices_before = self.runtime.runtime_devices_for_entry(hass, entry)
        self.assertEqual(1, len(devices_before))
        self.assertEqual("entry-1", devices_before[0].device_id)

        # Simulate a push later setting CONF_CPU_ID on the same entry.
        entry.data = {
            **entry.data,
            self.const.CONF_CPU_ID: "ABC123",
        }
        devices_after = self.runtime.runtime_devices_for_entry(hass, entry)
        self.assertEqual(
            devices_before[0].device_id,
            devices_after[0].device_id,
            "device_id must stay entry_id even after CONF_CPU_ID becomes known",
        )


if __name__ == "__main__":
    unittest.main()
