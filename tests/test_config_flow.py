from collections.abc import Generator
from unittest.mock import patch

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.argoclima.const import ARGO_DEVICE_ULISSE_ECO
from custom_components.argoclima.const import CONF_DEVICE_TYPE
from custom_components.argoclima.const import CONF_HOST
from custom_components.argoclima.const import CONF_NAME
from custom_components.argoclima.const import CONF_PORT
from custom_components.argoclima.const import CONF_ROLE
from custom_components.argoclima.const import DOMAIN
from custom_components.argoclima.const import ENTRY_ROLE_DEVICE
from custom_components.argoclima.const import ENTRY_ROLE_HUB

from .conftest import HOST
from .conftest import TITLE

DEVICE_INPUT = {
    CONF_DEVICE_TYPE: ARGO_DEVICE_ULISSE_ECO,
    CONF_NAME: TITLE,
    CONF_HOST: HOST,
}


@pytest.fixture(autouse=True)
def skip_setup() -> Generator[None]:
    with patch("custom_components.argoclima.async_setup_entry", return_value=True):
        yield


def mock_host_reachable(reachable: bool):
    return patch(
        "custom_components.argoclima.config_flow.async_test_host",
        return_value=reachable,
    )


async def start_flow(hass: HomeAssistant, step: str) -> dict:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.MENU
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": step}
    )


async def test_add_device(hass: HomeAssistant) -> None:
    result = await start_flow(hass, "device")
    assert result["step_id"] == "device"

    with mock_host_reachable(True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], DEVICE_INPUT
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TITLE
    assert result["data"] == {
        CONF_ROLE: ENTRY_ROLE_DEVICE,
        CONF_DEVICE_TYPE: ARGO_DEVICE_ULISSE_ECO,
        CONF_HOST: HOST,
    }


async def test_add_device_unreachable(hass: HomeAssistant) -> None:
    result = await start_flow(hass, "device")

    with mock_host_reachable(False):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], DEVICE_INPUT
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "host"}


async def test_add_dummy_server(hass: HomeAssistant) -> None:
    result = await start_flow(hass, "server")

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PORT: 8081}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Argoclima Dummy Server (8081)"
    assert result["data"] == {CONF_ROLE: ENTRY_ROLE_HUB, CONF_PORT: 8081}


async def test_dummy_server_port_in_use(hass: HomeAssistant) -> None:
    result = await start_flow(hass, "server")
    await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_PORT: 8081})

    result = await start_flow(hass, "server")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PORT: 8081}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "port_in_use"}


async def test_change_host_in_options(hass: HomeAssistant) -> None:
    result = await start_flow(hass, "device")
    with mock_host_reachable(True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], DEVICE_INPUT
        )
    entry = result["result"]

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["step_id"] == "user"
    with mock_host_reachable(True):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {CONF_HOST: "192.168.1.51"}
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.data[CONF_HOST] == "192.168.1.51"
