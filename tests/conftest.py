from collections.abc import Generator
from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.argoclima.api import ArgoApiClient
from custom_components.argoclima.const import ARGO_DEVICE_ULISSE_ECO
from custom_components.argoclima.const import CONF_DEVICE_TYPE
from custom_components.argoclima.const import CONF_HOST
from custom_components.argoclima.const import CONF_ROLE
from custom_components.argoclima.const import DOMAIN
from custom_components.argoclima.const import ENTRY_ROLE_DEVICE
from custom_components.argoclima.data import RESPONSE_VALUE_COUNT
from custom_components.argoclima.data import ArgoData

pytest_plugins = "pytest_homeassistant_custom_component"

HOST = "192.168.1.50"
TITLE = "Living Room"

DEFAULT_RESPONSE_VALUES = {
    0: 220,  # target temperature in 1/10 °C
    1: 235,  # current temperature in 1/10 °C
    2: 1,  # operating
    3: 1,  # mode: cool
    4: 0,  # fan: auto
    11: 1,  # device light
    22: 75,  # eco limit
    23: 41,  # firmware version
    24: 0,  # unit: celsius
}


def device_response(overrides: dict[int, int] | None = None) -> str:
    values = {**DEFAULT_RESPONSE_VALUES, **(overrides or {})}
    return ",".join(str(values.get(i, 0)) for i in range(RESPONSE_VALUE_COUNT))


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    return


@pytest.fixture
def sent_requests() -> list[str]:
    return []


@pytest.fixture
def mock_device(sent_requests: list[str]) -> Generator[None]:
    """Answer device requests like an idle Ulisse and record what was sent."""

    async def sync(self: ArgoApiClient, data: ArgoData | None) -> ArgoData:
        if data is None:
            data = ArgoData(self._type)
        sent_requests.append(data.to_parameter_string())
        data.parse_response_parameter_string(device_response())
        return data

    with patch.object(ArgoApiClient, "async_sync_data", sync):
        yield


@pytest.fixture
def device_entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title=TITLE,
        data={
            CONF_ROLE: ENTRY_ROLE_DEVICE,
            CONF_DEVICE_TYPE: ARGO_DEVICE_ULISSE_ECO,
            CONF_HOST: HOST,
        },
    )
