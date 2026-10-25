from datetime import timedelta

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.climate import SERVICE_SET_TEMPERATURE
from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.const import SERVICE_TURN_OFF
from homeassistant.const import SERVICE_TURN_ON
from homeassistant.const import STATE_OFF
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.core import State
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.common import async_fire_time_changed
from pytest_homeassistant_custom_component.common import mock_restore_cache

from .helpers import call
from .helpers import sent_value
from .helpers import setup_integration

CLIMATE = "climate.living_room"
ENABLED = "switch.living_room_anti_mold"
AFTER_REMOTE_OFF = "switch.living_room_anti_mold_after_remote_off"
DRYING = "binary_sensor.living_room_anti_mold_drying"
AFTER_COOLING = "switch.living_room_anti_mold_after_cooling"
AFTER_AUTO = "switch.living_room_anti_mold_after_auto"

OPERATING, MODE, FAN = 2, 3, 4


async def advance(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, minutes: float
) -> None:
    freezer.tick(timedelta(minutes=minutes))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def test_turns_off_normally_when_disabled(
    hass: HomeAssistant,
    mock_device: None,
    device_entry: MockConfigEntry,
    sent_requests: list[str],
) -> None:
    await setup_integration(hass, device_entry)

    await call(hass, CLIMATE_DOMAIN, SERVICE_TURN_OFF, CLIMATE)

    assert sent_value(sent_requests, OPERATING) == "0"
    assert hass.states.get(DRYING).state == STATE_OFF


@pytest.mark.parametrize("device_state", [{MODE: 1}, {MODE: 2}, {MODE: 5}])
async def test_dries_after_cooling(
    hass: HomeAssistant,
    mock_device: None,
    device_entry: MockConfigEntry,
    sent_requests: list[str],
    freezer: FrozenDateTimeFactory,
) -> None:
    await setup_integration(hass, device_entry)
    await call(hass, "switch", SERVICE_TURN_ON, ENABLED)

    await call(hass, CLIMATE_DOMAIN, SERVICE_TURN_OFF, CLIMATE)

    assert sent_value(sent_requests, MODE) == "4"
    assert sent_value(sent_requests, FAN) == "3"
    assert sent_value(sent_requests, OPERATING) != "0"
    assert hass.states.get(DRYING).state == STATE_ON

    await advance(hass, freezer, 14)
    assert hass.states.get(DRYING).state == STATE_ON

    await advance(hass, freezer, 1.1)
    assert sent_value(sent_requests, OPERATING) == "0"
    assert hass.states.get(DRYING).state == STATE_OFF


async def test_second_turn_off_stops_drying(
    hass: HomeAssistant,
    mock_device: None,
    device_entry: MockConfigEntry,
    sent_requests: list[str],
    freezer: FrozenDateTimeFactory,
) -> None:
    await setup_integration(hass, device_entry)
    await call(hass, "switch", SERVICE_TURN_ON, ENABLED)
    await call(hass, CLIMATE_DOMAIN, SERVICE_TURN_OFF, CLIMATE)

    await advance(hass, freezer, 0.1)
    await call(hass, CLIMATE_DOMAIN, SERVICE_TURN_OFF, CLIMATE)

    assert sent_value(sent_requests, OPERATING) == "0"
    assert hass.states.get(DRYING).state == STATE_OFF


async def test_other_command_cancels_drying(
    hass: HomeAssistant,
    mock_device: None,
    device_entry: MockConfigEntry,
) -> None:
    await setup_integration(hass, device_entry)
    await call(hass, "switch", SERVICE_TURN_ON, ENABLED)
    await call(hass, CLIMATE_DOMAIN, SERVICE_TURN_OFF, CLIMATE)

    await call(
        hass, CLIMATE_DOMAIN, SERVICE_SET_TEMPERATURE, CLIMATE, **{ATTR_TEMPERATURE: 21}
    )

    assert hass.states.get(DRYING).state == STATE_OFF


@pytest.mark.parametrize("device_state", [{MODE: 4}])
async def test_no_drying_after_fan_mode(
    hass: HomeAssistant,
    mock_device: None,
    device_entry: MockConfigEntry,
    sent_requests: list[str],
) -> None:
    await setup_integration(hass, device_entry)
    await call(hass, "switch", SERVICE_TURN_ON, ENABLED)

    await call(hass, CLIMATE_DOMAIN, SERVICE_TURN_OFF, CLIMATE)

    assert sent_value(sent_requests, OPERATING) == "0"
    assert hass.states.get(DRYING).state == STATE_OFF


@pytest.mark.parametrize(
    ("after_remote_off", "drying"), [(True, STATE_ON), (False, STATE_OFF)]
)
async def test_turned_off_with_remote(
    hass: HomeAssistant,
    mock_device: None,
    device_entry: MockConfigEntry,
    device_state: dict[int, int],
    freezer: FrozenDateTimeFactory,
    after_remote_off: bool,
    drying: str,
) -> None:
    await setup_integration(hass, device_entry)
    await call(hass, "switch", SERVICE_TURN_ON, ENABLED)
    if after_remote_off:
        await call(hass, "switch", SERVICE_TURN_ON, AFTER_REMOTE_OFF)

    device_state[OPERATING] = 0
    await advance(hass, freezer, 0.5)

    assert hass.states.get(DRYING).state == drying


@pytest.mark.parametrize("device_state", [{MODE: 4}])
async def test_settings_and_drying_survive_restart(
    hass: HomeAssistant,
    mock_device: None,
    device_entry: MockConfigEntry,
    sent_requests: list[str],
    freezer: FrozenDateTimeFactory,
) -> None:
    until = dt_util.utcnow() + timedelta(minutes=5)
    mock_restore_cache(
        hass,
        [
            State(ENABLED, STATE_ON),
            State(DRYING, STATE_ON, {"until": until.isoformat()}),
        ],
    )
    await setup_integration(hass, device_entry)

    assert hass.states.get(ENABLED).state == STATE_ON
    assert hass.states.get(DRYING).state == STATE_ON

    await advance(hass, freezer, 5.1)
    assert sent_value(sent_requests, OPERATING) == "0"
    assert hass.states.get(DRYING).state == STATE_OFF


async def test_modes_are_enabled_by_default(
    hass: HomeAssistant, mock_device: None, device_entry: MockConfigEntry
) -> None:
    await setup_integration(hass, device_entry)

    for mode in ("cooling", "dehumidifying", "auto"):
        assert hass.states.get(f"switch.living_room_anti_mold_after_{mode}").state == (
            STATE_ON
        )


async def test_no_drying_after_disabled_mode(
    hass: HomeAssistant,
    mock_device: None,
    device_entry: MockConfigEntry,
    sent_requests: list[str],
) -> None:
    await setup_integration(hass, device_entry)
    await call(hass, "switch", SERVICE_TURN_ON, ENABLED)
    await call(hass, "switch", SERVICE_TURN_OFF, AFTER_COOLING)

    await call(hass, CLIMATE_DOMAIN, SERVICE_TURN_OFF, CLIMATE)

    assert sent_value(sent_requests, OPERATING) == "0"
    assert hass.states.get(DRYING).state == STATE_OFF


async def test_disabled_mode_survives_restart(
    hass: HomeAssistant, mock_device: None, device_entry: MockConfigEntry
) -> None:
    mock_restore_cache(hass, [State(AFTER_AUTO, STATE_OFF)])
    await setup_integration(hass, device_entry)

    assert hass.states.get(AFTER_AUTO).state == STATE_OFF
    assert hass.states.get(AFTER_COOLING).state == STATE_ON


@pytest.mark.parametrize(("operating", "mode"), [(1, 1), (0, 4)])
async def test_change_on_device_while_drying_cancels_drying(
    hass: HomeAssistant,
    mock_device: None,
    device_entry: MockConfigEntry,
    device_state: dict[int, int],
    sent_requests: list[str],
    freezer: FrozenDateTimeFactory,
    operating: int,
    mode: int,
) -> None:
    await setup_integration(hass, device_entry)
    await call(hass, "switch", SERVICE_TURN_ON, ENABLED)
    await call(hass, CLIMATE_DOMAIN, SERVICE_TURN_OFF, CLIMATE)
    await advance(hass, freezer, 0.5)
    assert hass.states.get(DRYING).state == STATE_ON

    # Changed with the remote: back to cooling, or turned off.
    device_state[OPERATING] = operating
    device_state[MODE] = mode
    await advance(hass, freezer, 0.5)
    assert hass.states.get(DRYING).state == STATE_OFF

    requests_before = len(sent_requests)
    await advance(hass, freezer, 15)
    assert all(
        request.split(",")[OPERATING] == "N"
        for request in sent_requests[requests_before:]
    )


async def test_drying_stops_if_device_changed_during_restart(
    hass: HomeAssistant, mock_device: None, device_entry: MockConfigEntry
) -> None:
    until = dt_util.utcnow() + timedelta(minutes=5)
    mock_restore_cache(
        hass,
        [
            State(ENABLED, STATE_ON),
            State(DRYING, STATE_ON, {"until": until.isoformat()}),
        ],
    )
    await setup_integration(hass, device_entry)

    assert hass.states.get(DRYING).state == STATE_OFF
