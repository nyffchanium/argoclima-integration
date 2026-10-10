from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from .conftest import HOST
from .conftest import TITLE


async def test_diagnostics(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    mock_device: None,
    device_entry: MockConfigEntry,
) -> None:
    device_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(device_entry.entry_id)
    await hass.async_block_till_done()

    diagnostics = await get_diagnostics_for_config_entry(
        hass, hass_client, device_entry
    )

    assert HOST not in str(diagnostics)
    assert TITLE not in str(diagnostics)
    assert diagnostics["entry"]["data"]["host"] == "**REDACTED**"
    assert diagnostics["dummy_server"] is None
    [device] = diagnostics["devices"]
    assert device["type"] == "Ulisse 13 DCI Eco WiFi"
    assert device["push_updates"] is False
    assert device["last_seen"] is not None
    assert device["state"]["mode"] == "cool"
    assert device["state"]["temperature"] == 23.5
    assert device["state"]["firmware_version"] == 1416
