import asyncio
import logging
from datetime import timedelta

from custom_components.argoclima.data import ArgoData
from custom_components.argoclima.device_type import ArgoDeviceType
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Config
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.update_coordinator import UpdateFailed

from .api import ArgoApiClient
from .const import CONF_DEVICE_TYPE
from .const import CONF_HOST
from .const import DOMAIN
from .const import STARTUP_MESSAGE

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup(hass: HomeAssistant, config: Config):
    """Set up this integration using YAML is not supported."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up this integration using UI."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})
        _LOGGER.info(STARTUP_MESSAGE)

    type = ArgoDeviceType.from_name(entry.data.get(CONF_DEVICE_TYPE))
    host: str = entry.data.get(CONF_HOST)

    session = async_get_clientsession(hass)
    client = ArgoApiClient(type, host, session)

    coordinator = ArgoDataUpdateCoordinator(hass, client, type)
    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    hass.data[DOMAIN][entry.entry_id] = coordinator

    for platform in type.platforms:
        coordinator.platforms.append(platform)
        hass.async_add_job(
            hass.config_entries.async_forward_entry_setup(entry, platform)
        )

    entry.add_update_listener(async_reload_entry)
    return True


class ArgoDataUpdateCoordinator(DataUpdateCoordinator[ArgoData]):
    def __init__(
        self, hass: HomeAssistant, client: ArgoApiClient, type: ArgoDeviceType
    ) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=type.update_interval),
            update_method=self._async_update,
        )

        self._api = client
        self.platforms = []
        self.data = ArgoData(type)

    async def _async_update(self) -> ArgoData:
        """Update data via library."""
        try:
            return await self._api.async_sync_data(self.data)
        except Exception as exception:
            raise UpdateFailed() from exception


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
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


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
