from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant


async def setup_integration(hass: HomeAssistant, entry: ConfigEntry) -> None:
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


def sent_value(sent_requests: list[str], index: int) -> str:
    """Return a value of the last request sent to the device."""
    return sent_requests[-1].split(",")[index]
