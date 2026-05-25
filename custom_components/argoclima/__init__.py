import asyncio
import logging

from custom_components.argoclima.api import ArgoApiClient
from custom_components.argoclima.const import CONF_DEVICE_TYPE
from custom_components.argoclima.const import CONF_HOST
from custom_components.argoclima.const import CONF_PORT
from custom_components.argoclima.const import DOMAIN
from custom_components.argoclima.const import DUMMY_SERVER_DEFAULT_PORT
from custom_components.argoclima.const import ENTRY_ROLE_DEVICE
from custom_components.argoclima.const import ENTRY_ROLE_SERVER
from custom_components.argoclima.const import STARTUP_MESSAGE
from custom_components.argoclima.device_type import ArgoDeviceType
from custom_components.argoclima.dummy_server import ArgoDummyServer
from custom_components.argoclima.dummy_server import async_dummy_server_running
from custom_components.argoclima.dummy_server import async_entry_role
from custom_components.argoclima.service import setup_service
from custom_components.argoclima.update_coordinator import ArgoDataUpdateCoordinator
from homeassistant.config_entries import ConfigEntry
from homeassistant.core_config import Config
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession


_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup(hass: HomeAssistant, config: Config):
    await setup_service(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up this integration using UI."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})
        _LOGGER.info(STARTUP_MESSAGE)

    role = async_entry_role(entry)
    if role == ENTRY_ROLE_SERVER:
        return await _async_setup_server_entry(hass, entry)

    if role != ENTRY_ROLE_DEVICE:
        raise ConfigEntryNotReady(f"Unsupported Argoclima entry role: {role}")

    type = ArgoDeviceType.from_name(entry.data.get(CONF_DEVICE_TYPE))
    if type is None:
        raise ConfigEntryNotReady("Unsupported Argoclima device type")

    host: str = entry.data.get(CONF_HOST)

    session = async_get_clientsession(hass)
    client = ArgoApiClient(type, host, session)

    coordinator = ArgoDataUpdateCoordinator(
        hass,
        client,
        type,
        use_polling=not async_dummy_server_running(hass),
    )
    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    hass.data[DOMAIN][entry.entry_id] = coordinator

    coordinator.platforms.extend(type.platforms)
    await hass.config_entries.async_forward_entry_setups(entry, type.platforms)

    entry.add_update_listener(async_reload_entry)

    return True


async def _async_setup_server_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    port = entry.data.get(CONF_PORT, DUMMY_SERVER_DEFAULT_PORT)
    server = ArgoDummyServer(hass, port)
    try:
        await server.async_start()
    except OSError as err:
        _LOGGER.error(
            "Failed to start Argoclima dummy server on port %s: %s", port, err
        )
        raise ConfigEntryNotReady(str(err)) from err

    hass.data[DOMAIN][entry.entry_id] = server
    _async_set_push_updates_enabled(hass, True)
    entry.add_update_listener(async_reload_entry)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    role = async_entry_role(entry)
    if role == ENTRY_ROLE_SERVER:
        server = hass.data[DOMAIN].pop(entry.entry_id, None)
        if isinstance(server, ArgoDummyServer):
            await server.async_stop()
        _async_set_push_updates_enabled(hass, async_dummy_server_running(hass))
        return True

    coordinator = hass.data[DOMAIN][entry.entry_id]
    type: ArgoDeviceType = ArgoDeviceType.from_name(entry.data.get(CONF_DEVICE_TYPE))
    unloaded = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in type.platforms
                if platform in coordinator.platforms
            ]
        )
    )
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unloaded


def _async_set_push_updates_enabled(hass: HomeAssistant, enabled: bool) -> None:
    for value in hass.data.get(DOMAIN, {}).values():
        if isinstance(value, ArgoDataUpdateCoordinator):
            value.async_set_push_updates_enabled(enabled)


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
