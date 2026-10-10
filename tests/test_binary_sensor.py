from datetime import timedelta

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import STATE_OFF
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.argoclima.api import ArgoApiClient
from custom_components.argoclima.binary_sensor import ArgoConnectionSensor

ENTITY_ID = "binary_sensor.living_room_connection"


async def test_connection_state(
    hass: HomeAssistant,
    mock_device: None,
    device_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    device_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(device_entry.entry_id)
    await hass.async_block_till_done()

    first = hass.states.get(ENTITY_ID)
    assert first.state == STATE_ON
    first_seen = first.attributes["last_seen"]

    for _ in range(3):
        freezer.tick(timedelta(seconds=15))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
    state = hass.states.get(ENTITY_ID)
    assert state.state == STATE_ON
    assert state.attributes["last_seen"] > first_seen
    # Only state changes end up in the logbook.
    assert state.last_changed == first.last_changed

    async def offline(self: ArgoApiClient, data: object) -> None:
        raise TimeoutError

    monkeypatch.setattr(ArgoApiClient, "async_sync_data", offline)
    for _ in range(5):
        freezer.tick(timedelta(seconds=15))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()

    state = hass.states.get(ENTITY_ID)
    assert state.state == STATE_OFF
    assert state.attributes["last_seen"] > first_seen


def test_last_seen_is_not_recorded() -> None:
    assert "last_seen" in ArgoConnectionSensor._unrecorded_attributes
