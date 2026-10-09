import hashlib
import uuid

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.argoclima.const import CONF_CPU_ID
from custom_components.argoclima.const import DOMAIN
from custom_components.argoclima.unique_id import entity_unique_id

from .conftest import TITLE


def upstream_unique_id(entry_id: str, title: str, entity_name: str) -> str:
    """Unique_id as built by nyffchanium/argoclima-integration up to 1.1.4."""
    name = f"{title} {entity_name}"
    return uuid.UUID(hashlib.md5((entry_id + name).encode("utf-8")).hexdigest()).hex


async def test_setup_creates_entities(
    hass: HomeAssistant, mock_device: None, device_entry: MockConfigEntry
) -> None:
    device_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(device_entry.entry_id)
    await hass.async_block_till_done()

    assert device_entry.state is ConfigEntryState.LOADED

    climate = hass.states.get("climate.living_room_climate")
    assert climate.state == "cool"
    assert climate.attributes["current_temperature"] == 23.5
    assert climate.attributes["temperature"] == 22.0
    assert climate.attributes["fan_mode"] == "auto"
    assert climate.attributes["preset_mode"] == "none"

    assert hass.states.get("switch.living_room_device_light").state == STATE_ON
    assert hass.states.get("number.living_room_eco_mode_power_limit").state == "75"
    assert hass.states.get("select.living_room_display_unit").state == "°C"
    assert hass.states.get("select.living_room_active_timer").state == "no_timer"

    [device] = dr.async_entries_for_config_entry(
        dr.async_get(hass), device_entry.entry_id
    )
    assert device.identifiers == {(DOMAIN, device_entry.entry_id)}
    assert device.sw_version == "41"


async def test_unload(
    hass: HomeAssistant, mock_device: None, device_entry: MockConfigEntry
) -> None:
    device_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(device_entry.entry_id)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_unload(device_entry.entry_id)
    assert device_entry.state is ConfigEntryState.NOT_LOADED


async def test_migrates_upstream_unique_ids(
    hass: HomeAssistant, mock_device: None, device_entry: MockConfigEntry
) -> None:
    device_entry.add_to_hass(hass)
    registry = er.async_get(hass)
    legacy = registry.async_get_or_create(
        "climate",
        DOMAIN,
        upstream_unique_id(device_entry.entry_id, TITLE, "Climate"),
        config_entry=device_entry,
        suggested_object_id="living_room_climate",
    )
    registry.async_update_entity(legacy.entity_id, name="Office AC")

    assert await hass.config_entries.async_setup(device_entry.entry_id)
    await hass.async_block_till_done()

    migrated = registry.async_get(legacy.entity_id)
    assert migrated.unique_id == entity_unique_id(device_entry.entry_id, "Climate")
    assert migrated.name == "Office AC"
    assert registry.async_get("climate.living_room_climate_2") is None
    assert hass.states.get(legacy.entity_id).state == "cool"


async def test_migrates_cpu_id_based_unique_ids(
    hass: HomeAssistant, mock_device: None, device_entry: MockConfigEntry
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=TITLE,
        data={**device_entry.data, CONF_CPU_ID: "A1B2C3D4E5F6"},
    )
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    legacy = registry.async_get_or_create(
        "switch",
        DOMAIN,
        entity_unique_id("A1B2C3D4E5F6", "Device Light"),
        config_entry=entry,
        suggested_object_id="living_room_device_light",
    )

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert registry.async_get(legacy.entity_id).unique_id == entity_unique_id(
        entry.entry_id, "Device Light"
    )


async def test_existing_current_entity_is_not_overwritten(
    hass: HomeAssistant, mock_device: None, device_entry: MockConfigEntry
) -> None:
    device_entry.add_to_hass(hass)
    registry = er.async_get(hass)
    current = registry.async_get_or_create(
        "climate",
        DOMAIN,
        entity_unique_id(device_entry.entry_id, "Climate"),
        config_entry=device_entry,
        suggested_object_id="living_room_climate",
    )
    legacy = registry.async_get_or_create(
        "climate",
        DOMAIN,
        upstream_unique_id(device_entry.entry_id, TITLE, "Climate"),
        config_entry=device_entry,
        suggested_object_id="old_climate",
    )

    assert await hass.config_entries.async_setup(device_entry.entry_id)
    await hass.async_block_till_done()

    assert registry.async_get(current.entity_id).unique_id == current.unique_id
    assert registry.async_get(legacy.entity_id).unique_id == legacy.unique_id
