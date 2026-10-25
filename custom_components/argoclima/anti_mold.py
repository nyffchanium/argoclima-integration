from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.core import CALLBACK_TYPE
from homeassistant.core import HomeAssistant
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.util import dt as dt_util

from .types import ArgoFanSpeed
from .types import ArgoOperationMode

if TYPE_CHECKING:
    from .update_coordinator import ArgoDataUpdateCoordinator

DRYING_MODES = (ArgoOperationMode.COOL, ArgoOperationMode.DRY, ArgoOperationMode.AUTO)
DEFAULT_DURATION = timedelta(minutes=15)
DEFAULT_FAN_SPEED = ArgoFanSpeed.MEDIUM


class AntiMoldController:
    """Keep the fan running for a while after cooling to dry the device."""

    def __init__(
        self, hass: HomeAssistant, coordinator: ArgoDataUpdateCoordinator
    ) -> None:
        self._hass = hass
        self._coordinator = coordinator
        self.enabled = False
        self.after_remote_off = False
        self.duration = DEFAULT_DURATION
        self.fan_speed = DEFAULT_FAN_SPEED
        self.modes = set(DRYING_MODES)
        self.until: datetime | None = None
        self._cancel_timer: CALLBACK_TYPE | None = None
        self._last_state: tuple[bool | None, ArgoOperationMode | None] | None = None
        self._listeners: list[Callable[[], None]] = []

    @property
    def active(self) -> bool:
        return self.until is not None

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> CALLBACK_TYPE:
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    def should_dry(self) -> bool:
        data = self._coordinator.data
        return (
            self.enabled
            and not self.active
            and bool(data.operating)
            and data.mode in self.modes
        )

    async def async_start(self) -> None:
        data = self._coordinator.data
        data.operating = True
        data.mode = ArgoOperationMode.FAN
        data.fan = self.fan_speed
        self._schedule(dt_util.utcnow() + self.duration)
        await self._coordinator.async_request_refresh()

    @callback
    def async_resume(self, until: datetime) -> None:
        """Continue drying that was running before a restart."""
        self._schedule(max(until, dt_util.utcnow()))
        self.async_handle_device_update()

    @callback
    def async_shutdown(self) -> None:
        """Stop the timer without changing the state, e.g. on unload."""
        if self._cancel_timer is not None:
            self._cancel_timer()
            self._cancel_timer = None

    @callback
    def async_cancel(self) -> None:
        if self._cancel_timer is not None:
            self._cancel_timer()
            self._cancel_timer = None
        if self.until is not None:
            self.until = None
            self._notify()

    @callback
    def async_handle_device_update(self) -> None:
        """Follow changes made on the device, e.g. with the remote.

        Drying starts when the device was turned off outside Home Assistant
        and stops when it was turned off or switched to another mode.
        """
        data = self._coordinator.data
        if data.operating is None:
            return
        previous, self._last_state = self._last_state, (data.operating, data.mode)
        if data.is_update_pending():
            return
        if self.active:
            if not data.operating or data.mode is not ArgoOperationMode.FAN:
                self.async_cancel()
            return
        if (
            self.enabled
            and self.after_remote_off
            and previous is not None
            and previous[0]
            and previous[1] in self.modes
            and data.operating is False
        ):
            self._hass.async_create_task(self.async_start())

    def _schedule(self, until: datetime) -> None:
        self.async_cancel()
        self.until = until
        self._cancel_timer = async_track_point_in_utc_time(
            self._hass, self._async_finish, until
        )
        self._notify()

    async def _async_finish(self, _now: datetime) -> None:
        self._cancel_timer = None
        self.until = None
        self._notify()
        self._coordinator.data.operating = False
        await self._coordinator.async_request_refresh()

    def _notify(self) -> None:
        for listener in list(self._listeners):
            listener()
