import asyncio
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
        if name.startswith("custom_components"):
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


def _install_async_timeout_stub(timeout_calls: list[int]) -> None:
    module = types.ModuleType("async_timeout")

    class TimeoutContext:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    def timeout(seconds: int) -> TimeoutContext:
        timeout_calls.append(seconds)
        return TimeoutContext()

    setattr(module, "timeout", timeout)
    sys.modules["async_timeout"] = module


def _install_api_dependency_stubs() -> None:
    data_module = types.ModuleType("custom_components.argoclima.data")

    class ArgoData:
        pass

    setattr(data_module, "ArgoData", ArgoData)
    sys.modules[data_module.__name__] = data_module

    device_type_module = types.ModuleType("custom_components.argoclima.device_type")

    class ArgoDeviceType:
        pass

    setattr(device_type_module, "ArgoDeviceType", ArgoDeviceType)
    sys.modules[device_type_module.__name__] = device_type_module


def _install_homeassistant_stubs() -> None:
    climate_const = types.ModuleType("homeassistant.components.climate.const")
    climate_const.DOMAIN = "climate"
    climate_const.FAN_AUTO = "auto"
    climate_const.FAN_HIGH = "high"
    climate_const.FAN_LOW = "low"
    climate_const.FAN_MEDIUM = "medium"

    class HVACMode:
        COOL = "cool"
        DRY = "dry"
        HEAT = "heat"
        FAN_ONLY = "fan_only"
        AUTO = "auto"

    climate_const.HVACMode = HVACMode

    number_module = types.ModuleType("homeassistant.components.number")
    number_module.DOMAIN = "number"

    select_const = types.ModuleType("homeassistant.components.select.const")
    select_const.DOMAIN = "select"

    switch_module = types.ModuleType("homeassistant.components.switch")
    switch_module.DOMAIN = "switch"

    ha_const = types.ModuleType("homeassistant.const")

    class UnitOfTemperature:
        CELSIUS = "°C"
        FAHRENHEIT = "°F"

    ha_const.UnitOfTemperature = UnitOfTemperature

    sys.modules.update(
        {
            "homeassistant.components.climate.const": climate_const,
            "homeassistant.components.number": number_module,
            "homeassistant.components.select.const": select_const,
            "homeassistant.components.switch": switch_module,
            "homeassistant.const": ha_const,
        }
    )


def _install_update_coordinator_dependency_stubs() -> None:
    api_module = types.ModuleType("custom_components.argoclima.api")

    class ArgoApiClient:
        pass

    api_module.ArgoApiClient = ArgoApiClient

    const_module = types.ModuleType("custom_components.argoclima.const")
    const_module.DOMAIN = "argoclima"

    data_module = types.ModuleType("custom_components.argoclima.data")

    class ArgoData:
        def __init__(self, type):
            self.type = type

    data_module.ArgoData = ArgoData

    device_type_module = types.ModuleType("custom_components.argoclima.device_type")

    class ArgoDeviceType:
        update_interval = 60

    device_type_module.ArgoDeviceType = ArgoDeviceType

    homeassistant = types.ModuleType("homeassistant")
    homeassistant.__path__ = []
    homeassistant_core = types.ModuleType("homeassistant.core")
    homeassistant_core.HomeAssistant = object
    homeassistant_helpers = types.ModuleType("homeassistant.helpers")
    homeassistant_helpers.__path__ = []
    update_coordinator = types.ModuleType("homeassistant.helpers.update_coordinator")

    class DataUpdateCoordinator:
        def __init__(self, hass, logger, name, update_interval, update_method):
            self.hass = hass
            self.logger = logger
            self.name = name
            self.update_interval = update_interval
            self.update_method = update_method

        @classmethod
        def __class_getitem__(cls, item):
            return cls

    update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator

    sys.modules.update(
        {
            api_module.__name__: api_module,
            const_module.__name__: const_module,
            data_module.__name__: data_module,
            device_type_module.__name__: device_type_module,
            "homeassistant": homeassistant,
            homeassistant_core.__name__: homeassistant_core,
            "homeassistant.helpers": homeassistant_helpers,
            update_coordinator.__name__: update_coordinator,
        }
    )


class FakeDeviceType:
    port = 1001
    update_interval = 60


class FakeArgoData:
    def __init__(self) -> None:
        self.parsed_texts: list[str] = []

    def to_parameter_string(self) -> str:
        return "N,N,N"

    def is_update_pending(self) -> bool:
        return False

    def parse_response_parameter_string(self, text: str) -> None:
        self.parsed_texts.append(text)


class FakeResponse:
    def __init__(self, session: "FakeSession") -> None:
        self._session = session

    def __await__(self):
        async def _await_request():
            await self.__aenter__()
            return self

        return _await_request().__await__()

    async def __aenter__(self):
        self._session.active_requests += 1
        self._session.max_active_requests = max(
            self._session.max_active_requests, self._session.active_requests
        )
        await asyncio.sleep(0.01)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self._session.active_requests -= 1
        return False

    def raise_for_status(self) -> None:
        self._session.raise_for_status_calls += 1

    async def text(self) -> str:
        return "response-body"


class FakeSession:
    def __init__(self) -> None:
        self.active_requests = 0
        self.max_active_requests = 0
        self.raise_for_status_calls = 0

    def get(self, url, headers):
        return FakeResponse(self)


class ArgoApiClientSafetyTest(unittest.TestCase):
    def setUp(self) -> None:
        _drop_argoclima_modules()
        self.timeout_calls: list[int] = []
        _install_argoclima_package_stub()
        _install_async_timeout_stub(self.timeout_calls)
        _install_api_dependency_stubs()
        self.api = _load_argoclima_module("api")

    def test_uses_balanced_timeout_for_fragile_local_device(self) -> None:
        self.assertEqual(8, self.api.TIMEOUT)

        session = FakeSession()
        client = self.api.ArgoApiClient(FakeDeviceType(), "10.10.10.44", session)
        data = FakeArgoData()

        asyncio.run(client.async_sync_data(data))

        self.assertEqual([8], self.timeout_calls)
        self.assertEqual(["response-body"], data.parsed_texts)

    def test_serializes_requests_to_avoid_overlapping_device_polls(self) -> None:
        session = FakeSession()
        client = self.api.ArgoApiClient(FakeDeviceType(), "10.10.10.44", session)

        async def run_concurrent_syncs() -> None:
            await asyncio.gather(
                client.async_sync_data(FakeArgoData()),
                client.async_sync_data(FakeArgoData()),
            )

        asyncio.run(run_concurrent_syncs())

        self.assertEqual(1, session.max_active_requests)
        self.assertEqual(2, session.raise_for_status_calls)


class ArgoDeviceTypePollingTest(unittest.TestCase):
    def test_ulisse_eco_polls_less_aggressively_than_request_timeout(self) -> None:
        _drop_argoclima_modules()
        _install_argoclima_package_stub()
        _install_homeassistant_stubs()

        const = _load_argoclima_module("const")
        _load_argoclima_module("types")
        device_type = _load_argoclima_module("device_type")

        device = device_type.ArgoDeviceType.from_name(const.ARGO_DEVICE_ULISSE_ECO)

        self.assertEqual(60, device.update_interval)


class FakeCoordinatorApi:
    def __init__(self, results):
        self.results = list(results)

    async def async_sync_data(self, data):
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class ArgoDataUpdateCoordinatorFailureToleranceTest(unittest.TestCase):
    def setUp(self) -> None:
        _drop_argoclima_modules()
        _install_argoclima_package_stub()
        _install_update_coordinator_dependency_stubs()
        self.update_coordinator = _load_argoclima_module("update_coordinator")

    def test_keeps_last_state_for_first_two_failed_updates(self) -> None:
        client = FakeCoordinatorApi([TimeoutError("one"), TimeoutError("two")])
        coordinator = self.update_coordinator.ArgoDataUpdateCoordinator(
            object(), client, FakeDeviceType()
        )
        last_known_data = coordinator.data

        first_result = asyncio.run(coordinator._async_update())
        second_result = asyncio.run(coordinator._async_update())

        self.assertIs(last_known_data, first_result)
        self.assertIs(last_known_data, second_result)
        self.assertEqual(2, coordinator._consecutive_update_failures)

    def test_marks_unavailable_after_third_failed_update(self) -> None:
        client = FakeCoordinatorApi(
            [TimeoutError("one"), TimeoutError("two"), TimeoutError("three")]
        )
        coordinator = self.update_coordinator.ArgoDataUpdateCoordinator(
            object(), client, FakeDeviceType()
        )

        asyncio.run(coordinator._async_update())
        asyncio.run(coordinator._async_update())

        with self.assertRaises(TimeoutError):
            asyncio.run(coordinator._async_update())

        self.assertEqual(3, coordinator._consecutive_update_failures)

    def test_resets_failure_count_after_successful_update(self) -> None:
        recovered_data = object()
        client = FakeCoordinatorApi([TimeoutError("one"), recovered_data])
        coordinator = self.update_coordinator.ArgoDataUpdateCoordinator(
            object(), client, FakeDeviceType()
        )

        asyncio.run(coordinator._async_update())
        result = asyncio.run(coordinator._async_update())

        self.assertIs(recovered_data, result)
        self.assertEqual(0, coordinator._consecutive_update_failures)


if __name__ == "__main__":
    unittest.main()
