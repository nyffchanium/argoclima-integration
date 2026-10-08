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


def _install_dummy_server_dependency_stubs() -> None:
    data_module = types.ModuleType("custom_components.argoclima.data")

    class ArgoData:
        pass

    class InvalidResponseFormatError(Exception):
        pass

    data_module.ArgoData = ArgoData
    data_module.InvalidResponseFormatError = InvalidResponseFormatError

    device_type_module = types.ModuleType("custom_components.argoclima.device_type")

    class ArgoDeviceType:
        @staticmethod
        def from_name(name):
            return None

    device_type_module.ArgoDeviceType = ArgoDeviceType

    runtime_module = types.ModuleType("custom_components.argoclima.runtime")

    class ArgoHubRuntime:
        pass

    runtime_module.ArgoHubRuntime = ArgoHubRuntime

    # dummy_server.py imports these for hub-child device bookkeeping; the
    # tests in this file don't exercise that path, so stand-ins that are
    # merely importable are enough.
    def _unused_async_entry_role(entry):
        raise NotImplementedError

    def _unused_async_update_hub_device(hass, hub_entry, device_data):
        raise NotImplementedError

    def _unused_hub_entry_for_id(hass, hub_id):
        raise NotImplementedError

    def _unused_match_hub_device_id(devices, cpu_id, host):
        raise NotImplementedError

    runtime_module.async_entry_role = _unused_async_entry_role
    runtime_module.async_update_hub_device = _unused_async_update_hub_device
    runtime_module.hub_entry_for_id = _unused_hub_entry_for_id
    runtime_module.match_hub_device_id = _unused_match_hub_device_id

    update_coordinator_module = types.ModuleType(
        "custom_components.argoclima.update_coordinator"
    )

    class ArgoDataUpdateCoordinator:
        pass

    update_coordinator_module.ArgoDataUpdateCoordinator = ArgoDataUpdateCoordinator

    homeassistant = types.ModuleType("homeassistant")
    homeassistant.__path__ = []
    config_entries_module = types.ModuleType("homeassistant.config_entries")
    config_entries_module.SOURCE_INTEGRATION_DISCOVERY = "integration_discovery"

    class ConfigEntry:
        pass

    config_entries_module.ConfigEntry = ConfigEntry

    core_module = types.ModuleType("homeassistant.core")
    core_module.HomeAssistant = object

    sys.modules.update(
        {
            data_module.__name__: data_module,
            device_type_module.__name__: device_type_module,
            runtime_module.__name__: runtime_module,
            update_coordinator_module.__name__: update_coordinator_module,
            "homeassistant": homeassistant,
            config_entries_module.__name__: config_entries_module,
            core_module.__name__: core_module,
        }
    )


HUB_ID = "dummy_server_hub:test"


class DummyServerPushValidationTest(unittest.TestCase):
    def setUp(self) -> None:
        _drop_argoclima_modules()
        _install_argoclima_package_stub()
        _install_dummy_server_dependency_stubs()
        _load_argoclima_module("const")
        self.dummy_server = _load_argoclima_module("dummy_server")

    def test_accepts_push_when_claimed_ip_matches_connection_source(self) -> None:
        push_data = self.dummy_server._push_data_from_params(
            {"IP": "10.0.0.5", "CPU_ID": "ABC123", "HMI": "N"},
            HUB_ID,
            "10.0.0.5",
        )

        self.assertIsNotNone(push_data)
        self.assertEqual("10.0.0.5", push_data.host)
        self.assertEqual("ABC123", push_data.cpu_id)

    def test_rejects_push_when_claimed_ip_does_not_match_connection_source(
        self,
    ) -> None:
        push_data = self.dummy_server._push_data_from_params(
            {"IP": "10.0.0.5", "CPU_ID": "ABC123", "HMI": "N"},
            HUB_ID,
            "10.0.0.99",
        )

        self.assertIsNone(push_data)

    def test_rejects_push_when_connection_source_is_unknown(self) -> None:
        push_data = self.dummy_server._push_data_from_params(
            {"IP": "10.0.0.5", "CPU_ID": "ABC123", "HMI": "N"},
            HUB_ID,
            None,
        )

        self.assertIsNone(push_data)

    def test_accepts_ipv4_mapped_ipv6_peer_address(self) -> None:
        # A dual-stack socket can report an IPv4 peer as an IPv4-mapped IPv6
        # address; that must still match the device's plain IPv4 claim.
        peer_ip = self.dummy_server._valid_host("::ffff:10.0.0.5")

        push_data = self.dummy_server._push_data_from_params(
            {"IP": "10.0.0.5", "CPU_ID": "ABC123", "HMI": "N"},
            HUB_ID,
            peer_ip,
        )

        self.assertIsNotNone(push_data)
        self.assertEqual("10.0.0.5", push_data.host)

    def test_peer_host_reads_normalized_address_from_writer(self) -> None:
        class FakeWriter:
            def get_extra_info(self, name):
                assert name == "peername"
                return ("10.0.0.5", 54321)

        self.assertEqual("10.0.0.5", self.dummy_server._peer_host(FakeWriter()))

    def test_peer_host_returns_none_without_peername(self) -> None:
        class FakeWriter:
            def get_extra_info(self, name):
                return None

        self.assertIsNone(self.dummy_server._peer_host(FakeWriter()))


if __name__ == "__main__":
    unittest.main()
