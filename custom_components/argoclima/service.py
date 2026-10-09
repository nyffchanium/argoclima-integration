import logging
from datetime import datetime
from datetime import time as dt_time
from typing import Any

import homeassistant.helpers.config_validation as cv
import homeassistant.helpers.device_registry as dr
import voluptuous as vol
from custom_components.argoclima.const import DOMAIN
from custom_components.argoclima.runtime import ArgoHubRuntime
from custom_components.argoclima.types import ArgoWeekday
from custom_components.argoclima.update_coordinator import ArgoDataUpdateCoordinator
from homeassistant.core import HomeAssistant
from homeassistant.helpers.service import verify_domain_control
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)
ATTR_DEVICE = "device"
ATTR_TIME = "time"
ATTR_WEEKDAY = "weekday"
WEEKDAY_NAMES = (
    "sunday",
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
)


def _weekday(value: Any) -> ArgoWeekday:
    """Validate a weekday, given by number (0 = sunday) or name."""
    value: str = str(value).lower()
    for number, name in enumerate(WEEKDAY_NAMES):
        if value in (str(number), name):
            return ArgoWeekday(number)
    raise vol.Invalid("Invalid weekday")


def _coordinator_from_hub_runtime(
    runtime: ArgoHubRuntime, device: dr.DeviceEntry
) -> ArgoDataUpdateCoordinator | None:
    identifiers = {
        identifier for domain, identifier in device.identifiers if domain == DOMAIN
    }
    for runtime_device in runtime.devices.values():
        if runtime_device.device_id in identifiers:
            return runtime_device.coordinator
    return None


async def setup_service(hass: HomeAssistant):
    async def _set_time(call, **kwargs) -> None:
        device: dr.DeviceEntry = call.data.get(ATTR_DEVICE)
        time: dt_time = call.data.get(ATTR_TIME)
        weekday: ArgoWeekday = call.data.get(ATTR_WEEKDAY)
        coordinator = _coordinator_for_device(device)
        if coordinator is None:
            _LOGGER.warning(
                "Device %s is not loaded.", device.name_by_user or device.name
            )
            return
        if not coordinator.last_update_success:
            _LOGGER.warning(
                "Device %s is not available.", device.name_by_user or device.name
            )
            return
        if time is None or weekday is None:
            date = _get_current_datetime()
            if time is None:
                time = date.time()
            if weekday is None:
                weekday = ArgoWeekday.from_datetime(date)
        coordinator.data.set_current_weekday(weekday)
        coordinator.data.set_time(time.hour, time.minute)
        await coordinator.async_request_refresh()

    def _get_current_datetime() -> datetime:
        return dt_util.utcnow().astimezone(dt_util.get_time_zone(hass.config.time_zone))

    def _coordinator_for_device(
        device: dr.DeviceEntry,
    ) -> ArgoDataUpdateCoordinator | None:
        for entry_id in device.config_entries:
            runtime = hass.data.get(DOMAIN, {}).get(entry_id)
            if isinstance(runtime, ArgoDataUpdateCoordinator):
                return runtime
            if isinstance(runtime, ArgoHubRuntime):
                coordinator = _coordinator_from_hub_runtime(runtime, device)
                if coordinator is not None:
                    return coordinator
        identifiers = {
            identifier for domain, identifier in device.identifiers if domain == DOMAIN
        }
        # A standalone device's device_info identifier is always its own
        # entry_id (see runtime.py/entity.py) - stable regardless of
        # whether/when its CPU_ID becomes known.
        for entry in hass.config_entries.async_entries(DOMAIN):
            if entry.entry_id in identifiers:
                coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
                if isinstance(coordinator, ArgoDataUpdateCoordinator):
                    return coordinator
        for runtime in hass.data.get(DOMAIN, {}).values():
            if isinstance(runtime, ArgoHubRuntime):
                coordinator = _coordinator_from_hub_runtime(runtime, device)
                if coordinator is not None:
                    return coordinator
        return None

    def device(value: Any) -> dr.DeviceEntry:
        """Validate that the device exists."""
        device_entry = dr.async_get(hass).async_get(str(value))
        if device_entry is None:
            raise vol.Invalid(f"Could not find device with ID {value}")
        return device_entry

    hass.services.async_register(
        DOMAIN,
        "set_time",
        verify_domain_control(DOMAIN)(_set_time),
        schema=vol.Schema(
            {
                vol.Required(ATTR_DEVICE): device,
                vol.Optional(ATTR_TIME): cv.time,
                vol.Optional(ATTR_WEEKDAY): _weekday,
            }
        ),
    )
