import logging
from datetime import timedelta

from custom_components.argoclima.api import ArgoApiClient
from custom_components.argoclima.const import DOMAIN
from custom_components.argoclima.data import ArgoData
from custom_components.argoclima.device_type import ArgoDeviceType
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator


_LOGGER: logging.Logger = logging.getLogger(__package__)
MAX_CONSECUTIVE_UPDATE_FAILURES = 3


class ArgoDataUpdateCoordinator(DataUpdateCoordinator[ArgoData]):
    def __init__(
        self,
        hass: HomeAssistant,
        client: ArgoApiClient,
        type: ArgoDeviceType,
        *,
        use_polling: bool = True,
    ) -> None:
        """Initialize."""
        self._type = type
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=type.update_interval)
            if use_polling
            else None,
            update_method=self._async_update,
        )

        self._api = client
        self.platforms = []
        self.data = ArgoData(type)
        self._consecutive_update_failures = 0

    def async_update_host(self, host: str) -> None:
        """Update the direct device address used for explicit syncs."""
        self._api.host = host

    def async_set_push_updates_enabled(self, enabled: bool) -> None:
        """Enable or disable periodic polling while retaining manual refreshes."""
        was_polling = self.update_interval is not None
        self.update_interval = (
            None if enabled else timedelta(seconds=self._type.update_interval)
        )
        if enabled:
            self._async_unsub_refresh()
        elif not was_polling and self._listeners:
            self._schedule_refresh()

    async def _async_update(self) -> ArgoData:
        """Update data via library."""
        try:
            data = await self._api.async_sync_data(self.data)
        except Exception:
            self._consecutive_update_failures += 1

            if self._consecutive_update_failures < MAX_CONSECUTIVE_UPDATE_FAILURES:
                _LOGGER.warning(
                    "ArgoClimate update failed (%s/%s); keeping last known state",
                    self._consecutive_update_failures,
                    MAX_CONSECUTIVE_UPDATE_FAILURES,
                    exc_info=True,
                )
                return self.data

            _LOGGER.warning(
                "ArgoClimate update failed %s times in a row; marking unavailable",
                self._consecutive_update_failures,
                exc_info=True,
            )
            raise

        self._consecutive_update_failures = 0
        return data
