import logging
from datetime import timedelta

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.update_coordinator import UpdateFailed

from .api import ArgoApiClient
from .const import DOMAIN
from .data import ArgoData
from .data import InvalidResponseFormatError
from .device_type import ArgoDeviceType

_LOGGER = logging.getLogger(__package__)

MAX_CONSECUTIVE_UPDATE_FAILURES = 3


class ArgoDataUpdateCoordinator(DataUpdateCoordinator[ArgoData]):
    def __init__(
        self,
        hass: HomeAssistant,
        client: ArgoApiClient,
        device_type: ArgoDeviceType,
        *,
        use_polling: bool = True,
    ) -> None:
        self._type = device_type
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=self._polling_interval if use_polling else None,
            update_method=self._async_update,
        )
        self._api = client
        self.platforms = []
        self.data = ArgoData(device_type)
        self._consecutive_update_failures = 0

    @property
    def _polling_interval(self) -> timedelta:
        return timedelta(seconds=self._type.update_interval)

    def async_update_host(self, host: str) -> None:
        self._api.host = host

    def async_set_push_updates_enabled(self, enabled: bool) -> None:
        """Pause polling while the device pushes its state through the dummy server."""
        was_polling = self.update_interval is not None
        self.update_interval = None if enabled else self._polling_interval
        if enabled:
            self._async_unsub_refresh()
        elif not was_polling and self._listeners:
            self._schedule_refresh()

    async def _async_update(self) -> ArgoData:
        try:
            data = await self._api.async_sync_data(self.data)
        except (
            aiohttp.ClientError,
            TimeoutError,
            InvalidResponseFormatError,
            ValueError,
        ) as err:
            self._consecutive_update_failures += 1
            reason = str(err) or type(err).__name__
            if self._consecutive_update_failures < MAX_CONSECUTIVE_UPDATE_FAILURES:
                _LOGGER.debug(
                    "Argoclima device %s did not respond (%s/%s), keeping last state: %s",
                    self._api.host,
                    self._consecutive_update_failures,
                    MAX_CONSECUTIVE_UPDATE_FAILURES,
                    reason,
                )
                return self.data
            raise UpdateFailed(
                f"Argoclima device {self._api.host} did not respond "
                f"{self._consecutive_update_failures} times in a row: {reason}"
            ) from err

        self._consecutive_update_failures = 0
        return data
