from homeassistant.components.number import ATTR_VALUE
from homeassistant.components.number import SERVICE_SET_VALUE
from homeassistant.components.select import ATTR_OPTION
from homeassistant.components.select import SERVICE_SELECT_OPTION
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.core import State
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.common import (
    mock_restore_cache_with_extra_data,
)

TIMER = "select.living_room_active_timer"
DURATION = "number.living_room_delay_timer_duration"
TIMER_INDEX, DURATION_INDEX = 12, 21


async def setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def call(
    hass: HomeAssistant, domain: str, service: str, entity_id: str, **data
) -> None:
    await hass.services.async_call(
        domain, service, {ATTR_ENTITY_ID: entity_id, **data}, blocking=True
    )
    await hass.async_block_till_done()


def sent(sent_requests: list[str], index: int) -> str:
    return sent_requests[-1].split(",")[index]


async def test_duration_is_sent_with_delay_timer(
    hass: HomeAssistant,
    mock_device: None,
    device_entry: MockConfigEntry,
    sent_requests: list[str],
) -> None:
    await setup(hass, device_entry)
    assert hass.states.get(DURATION).state == "60"

    await call(
        hass, "select", SERVICE_SELECT_OPTION, TIMER, **{ATTR_OPTION: "delay_on_off"}
    )

    assert sent(sent_requests, TIMER_INDEX) == "1"
    assert sent(sent_requests, DURATION_INDEX) == "60"


async def test_changing_duration_without_delay_timer_is_only_stored(
    hass: HomeAssistant,
    mock_device: None,
    device_entry: MockConfigEntry,
    sent_requests: list[str],
) -> None:
    await setup(hass, device_entry)
    requests_before = len(sent_requests)

    await call(hass, "number", SERVICE_SET_VALUE, DURATION, **{ATTR_VALUE: 90})

    assert hass.states.get(DURATION).state == "90"
    assert len(sent_requests) == requests_before


async def test_changing_duration_while_delay_timer_is_active(
    hass: HomeAssistant,
    mock_device: None,
    device_entry: MockConfigEntry,
    sent_requests: list[str],
    device_state: dict[int, int],
) -> None:
    device_state[TIMER_INDEX] = 1
    await setup(hass, device_entry)

    await call(hass, "number", SERVICE_SET_VALUE, DURATION, **{ATTR_VALUE: 120})

    assert sent(sent_requests, DURATION_INDEX) == "120"


async def test_duration_survives_restart(
    hass: HomeAssistant, mock_device: None, device_entry: MockConfigEntry
) -> None:
    mock_restore_cache_with_extra_data(
        hass,
        [
            (
                State(DURATION, "180"),
                {
                    "native_value": 180,
                    "native_min_value": 10,
                    "native_max_value": 1190,
                    "native_step": 10,
                    "native_unit_of_measurement": "min",
                },
            )
        ],
    )
    await setup(hass, device_entry)

    assert hass.states.get(DURATION).state == "180"
