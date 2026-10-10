from homeassistant.const import STATE_OFF
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.argoclima.firmware import FIRMWARE_URL
from custom_components.argoclima.unique_id import entity_unique_id

ENTITY_ID = "update.living_room_firmware"


def mock_argo_firmware(
    aioclient_mock: AiohttpClientMocker, unit: str, wifi: str
) -> None:
    for command, release in (("OU_FW", unit), ("UI_FW", wifi)):
        aioclient_mock.get(
            FIRMWARE_URL,
            params={"CM": command},
            text=f"RELEASE={release}|OFFSET=036352|SIZE=025962|NUM_PACK=0103|CKS=1|||",
        )


async def setup_with_update_entity(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    er.async_get(hass).async_get_or_create(
        "update",
        "argoclima",
        entity_unique_id(entry.entry_id, "Firmware"),
        config_entry=entry,
        suggested_object_id="living_room_firmware",
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_disabled_by_default(
    hass: HomeAssistant,
    mock_device: None,
    device_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    device_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(device_entry.entry_id)
    await hass.async_block_till_done()

    entity = er.async_get(hass).async_get(ENTITY_ID)
    assert entity.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert aioclient_mock.call_count == 0


async def test_up_to_date(
    hass: HomeAssistant,
    mock_device: None,
    device_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    mock_argo_firmware(aioclient_mock, "01416", "00003")
    await setup_with_update_entity(hass, device_entry)

    state = hass.states.get(ENTITY_ID)
    assert state.state == STATE_OFF
    assert state.attributes["installed_version"] == "01416"
    assert state.attributes["latest_version"] == "01416"
    query = aioclient_mock.mock_calls[0][1].query
    assert query["CM"] == "OU_FW" and query["PK"] == "-1"


async def test_update_available(
    hass: HomeAssistant,
    mock_device: None,
    device_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    mock_argo_firmware(aioclient_mock, "01500", "00003")
    await setup_with_update_entity(hass, device_entry)

    state = hass.states.get(ENTITY_ID)
    assert state.state == STATE_ON
    assert state.attributes["latest_version"] == "01500"
