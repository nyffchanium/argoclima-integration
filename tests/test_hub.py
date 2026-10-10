from collections.abc import Generator
from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.argoclima.const import ARGO_DEVICE_ULISSE_ECO
from custom_components.argoclima.const import CONF_CPU_ID
from custom_components.argoclima.const import CONF_DEVICE_TYPE
from custom_components.argoclima.const import CONF_DEVICES
from custom_components.argoclima.const import CONF_HOST
from custom_components.argoclima.const import CONF_NAME
from custom_components.argoclima.const import CONF_NAT_GATEWAY
from custom_components.argoclima.const import CONF_PORT
from custom_components.argoclima.const import CONF_ROLE
from custom_components.argoclima.const import DOMAIN
from custom_components.argoclima.const import ENTRY_ROLE_HUB
from custom_components.argoclima.dummy_server import ArgoDummyServer
from custom_components.argoclima.dummy_server import ArgoPushData
from custom_components.argoclima.dummy_server import async_handle_push_data
from custom_components.argoclima.runtime import dummy_server_hub_id

from .conftest import HOST
from .conftest import TITLE
from .conftest import device_response

CPU_ID = "A1B2C3D4E5F6"


@pytest.fixture(autouse=True)
def mock_listener() -> Generator[None]:
    with (
        patch.object(ArgoDummyServer, "async_start"),
        patch.object(ArgoDummyServer, "async_stop"),
    ):
        yield


@pytest.fixture
def hub() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="Argoclima Dummy Server (8080)",
        data={
            CONF_ROLE: ENTRY_ROLE_HUB,
            CONF_PORT: 8080,
            CONF_DEVICES: {
                "device-key": {
                    CONF_DEVICE_TYPE: ARGO_DEVICE_ULISSE_ECO,
                    CONF_HOST: HOST,
                    CONF_CPU_ID: CPU_ID,
                    CONF_NAME: TITLE,
                }
            },
        },
    )


async def test_push_updates_hub_device(
    hass: HomeAssistant, hub: MockConfigEntry
) -> None:
    hub.add_to_hass(hass)
    assert await hass.config_entries.async_setup(hub.entry_id)
    await hass.async_block_till_done()
    assert hub.state is ConfigEntryState.LOADED

    await async_handle_push_data(
        hass,
        ArgoPushData(
            cpu_id=CPU_ID,
            host=HOST,
            hmi=device_response(),
            hub_id=dummy_server_hub_id(hub),
        ),
    )
    await hass.async_block_till_done()

    state = hass.states.get("climate.living_room")
    assert state.state == "cool"
    assert state.attributes["current_temperature"] == 23.5


async def test_unload_hub(hass: HomeAssistant, hub: MockConfigEntry) -> None:
    hub.add_to_hass(hass)
    assert await hass.config_entries.async_setup(hub.entry_id)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_unload(hub.entry_id)
    assert hub.state is ConfigEntryState.NOT_LOADED


async def test_push_through_nat_gateway(hass: HomeAssistant) -> None:
    hub = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_ROLE: ENTRY_ROLE_HUB,
            CONF_PORT: 8080,
            CONF_NAT_GATEWAY: "192.168.1.1",
        },
    )
    hub.add_to_hass(hass)
    assert await hass.config_entries.async_setup(hub.entry_id)
    await hass.async_block_till_done()

    server = hass.data[DOMAIN][hub.entry_id].server
    body = await server._async_response_body(
        "GET", f"/?CM=UI_FLG&IP={HOST}&CPU_ID={CPU_ID}", "192.168.1.1"
    )
    await hass.async_block_till_done()

    assert body.startswith("{|1|0|")
    [flow] = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert flow["context"]["unique_id"] == CPU_ID


async def test_push_shows_firmware_versions(
    hass: HomeAssistant, hub: MockConfigEntry
) -> None:
    hub.add_to_hass(hass)
    assert await hass.config_entries.async_setup(hub.entry_id)
    await hass.async_block_till_done()

    await async_handle_push_data(
        hass,
        ArgoPushData(
            cpu_id=CPU_ID,
            host=HOST,
            hmi=device_response(),
            hub_id=dummy_server_hub_id(hub),
            wifi_firmware="00003",
        ),
    )
    await hass.async_block_till_done()

    [device] = dr.async_entries_for_config_entry(dr.async_get(hass), hub.entry_id)
    assert device.sw_version == "01416 (WiFi 00003)"


async def test_unconfirmed_change_is_resent_on_push(
    hass: HomeAssistant,
    hub: MockConfigEntry,
    sent_requests: list[str],
    mock_device: None,
) -> None:
    hub.add_to_hass(hass)
    assert await hass.config_entries.async_setup(hub.entry_id)
    await hass.async_block_till_done()
    push = ArgoPushData(
        cpu_id=CPU_ID, host=HOST, hmi=device_response(), hub_id=dummy_server_hub_id(hub)
    )
    await async_handle_push_data(hass, push)
    await hass.async_block_till_done()

    coordinator = hass.data[DOMAIN][hub.entry_id].devices["device-key"].coordinator
    coordinator.data.light = False
    sent_requests.clear()

    await async_handle_push_data(hass, push)
    await hass.async_block_till_done()

    assert sent_requests and sent_requests[-1].split(",")[11] == "0"


async def test_diagnostics_redact_device_addresses(
    hass: HomeAssistant, hub: MockConfigEntry, hass_client: ClientSessionGenerator
) -> None:
    hub.add_to_hass(hass)
    assert await hass.config_entries.async_setup(hub.entry_id)
    await hass.async_block_till_done()

    diagnostics = await get_diagnostics_for_config_entry(hass, hass_client, hub)

    assert HOST not in str(diagnostics)
    assert CPU_ID not in str(diagnostics)
    assert TITLE not in str(diagnostics)
    assert diagnostics["dummy_server"]["running"] is False
    assert len(diagnostics["devices"]) == 1
