from datetime import time

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.argoclima.const import DOMAIN
from custom_components.argoclima.service import SERVICE_SET_TIME


async def setup_device(hass: HomeAssistant, entry: MockConfigEntry) -> str:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    [device] = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    return device.id


async def test_set_time(
    hass: HomeAssistant,
    mock_device: None,
    device_entry: MockConfigEntry,
    sent_requests: list[str],
) -> None:
    device_id = await setup_device(hass, device_entry)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_SET_TIME,
        {"device": device_id, "time": time(13, 37), "weekday": "Wednesday"},
        blocking=True,
    )
    await hass.async_block_till_done()

    values = sent_requests[-1].split(",")
    assert values[18] == "3"
    assert values[20] == str(13 * 60 + 37)


async def test_set_time_on_unloaded_device(
    hass: HomeAssistant, mock_device: None, device_entry: MockConfigEntry
) -> None:
    device_id = await setup_device(hass, device_entry)
    await hass.config_entries.async_unload(device_entry.entry_id)

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN, SERVICE_SET_TIME, {"device": device_id}, blocking=True
        )
