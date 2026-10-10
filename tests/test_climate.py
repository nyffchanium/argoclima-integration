from homeassistant.components.climate import ATTR_FAN_MODE
from homeassistant.components.climate import ATTR_HVAC_MODE
from homeassistant.components.climate import ATTR_PRESET_MODE
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.climate import SERVICE_SET_FAN_MODE
from homeassistant.components.climate import SERVICE_SET_HVAC_MODE
from homeassistant.components.climate import SERVICE_SET_PRESET_MODE
from homeassistant.components.climate import SERVICE_SET_TEMPERATURE
from homeassistant.components.climate import HVACMode
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.const import SERVICE_TURN_OFF
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

ENTITY_ID = "climate.living_room"


async def setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def call(hass: HomeAssistant, service: str, data: dict) -> None:
    await hass.services.async_call(
        CLIMATE_DOMAIN, service, {ATTR_ENTITY_ID: ENTITY_ID, **data}, blocking=True
    )
    await hass.async_block_till_done()


def sent_value(sent_requests: list[str], index: int) -> str:
    return sent_requests[-1].split(",")[index]


async def test_set_temperature(
    hass: HomeAssistant,
    mock_device: None,
    device_entry: MockConfigEntry,
    sent_requests: list[str],
) -> None:
    await setup(hass, device_entry)

    await call(hass, SERVICE_SET_TEMPERATURE, {ATTR_TEMPERATURE: 24.5})

    assert sent_value(sent_requests, 0) == "245"


async def test_set_hvac_mode(
    hass: HomeAssistant,
    mock_device: None,
    device_entry: MockConfigEntry,
    sent_requests: list[str],
) -> None:
    await setup(hass, device_entry)

    await call(hass, SERVICE_SET_HVAC_MODE, {ATTR_HVAC_MODE: HVACMode.DRY})

    assert sent_value(sent_requests, 3) == "2"


async def test_turn_off(
    hass: HomeAssistant,
    mock_device: None,
    device_entry: MockConfigEntry,
    sent_requests: list[str],
) -> None:
    await setup(hass, device_entry)

    await call(hass, SERVICE_TURN_OFF, {})

    assert sent_value(sent_requests, 2) == "0"


async def test_set_preset_mode(
    hass: HomeAssistant,
    mock_device: None,
    device_entry: MockConfigEntry,
    sent_requests: list[str],
) -> None:
    await setup(hass, device_entry)

    await call(hass, SERVICE_SET_PRESET_MODE, {ATTR_PRESET_MODE: "eco"})

    assert sent_value(sent_requests, 8) == "1"


async def test_set_fan_mode(
    hass: HomeAssistant,
    mock_device: None,
    device_entry: MockConfigEntry,
    sent_requests: list[str],
) -> None:
    await setup(hass, device_entry)

    await call(hass, SERVICE_SET_FAN_MODE, {ATTR_FAN_MODE: "highest"})

    assert sent_value(sent_requests, 4) == "6"
