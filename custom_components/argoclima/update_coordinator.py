import logging
from datetime import timedelta

from custom_components.argoclima.api import ArgoApiClient
from custom_components.argoclima.const import DOMAIN
from custom_components.argoclima.data import ArgoData
from custom_components.argoclima.device_type import ArgoDeviceType
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator


_LOGGER: logging.Logger = logging.getLogger(__package__)


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
        return await self._api.async_sync_data(self.data)
