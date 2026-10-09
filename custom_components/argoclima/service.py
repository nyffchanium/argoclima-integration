from typing import Any

import homeassistant.helpers.config_validation as cv
import homeassistant.helpers.device_registry as dr
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.core import ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.service import verify_domain_control
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .runtime import ArgoHubRuntime
from .types import ArgoWeekday
from .update_coordinator import ArgoDataUpdateCoordinator

SERVICE_SET_TIME = "set_time"
ATTR_DEVICE = "device"
ATTR_TIME = "time"
ATTR_WEEKDAY = "weekday"


def _weekday(value: Any) -> ArgoWeekday:
    """Validate a weekday, given by number (0 = sunday) or name."""
    value = str(value).lower()
    for weekday in ArgoWeekday:
        if value in (str(weekday.value), str(weekday)):
            return weekday
    raise vol.Invalid("Invalid weekday")


def _coordinator_for_device(
    hass: HomeAssistant, device: dr.DeviceEntry
) -> ArgoDataUpdateCoordinator | None:
    identifiers = {
        identifier for domain, identifier in device.identifiers if domain == DOMAIN
    }
    for entry_id in device.config_entries:
        runtime = hass.data.get(DOMAIN, {}).get(entry_id)
        if isinstance(runtime, ArgoDataUpdateCoordinator):
            return runtime
        if isinstance(runtime, ArgoHubRuntime):
            for runtime_device in runtime.devices.values():
                if runtime_device.device_id in identifiers:
                    return runtime_device.coordinator
    return None


async def setup_service(hass: HomeAssistant) -> None:
    def device(value: Any) -> dr.DeviceEntry:
        device_entry = dr.async_get(hass).async_get(str(value))
        if device_entry is None:
            raise vol.Invalid(f"Could not find device with ID {value}")
        return device_entry

    async def set_time(call: ServiceCall) -> None:
        device_entry: dr.DeviceEntry = call.data[ATTR_DEVICE]
        device_name = device_entry.name_by_user or device_entry.name
        coordinator = _coordinator_for_device(hass, device_entry)
        if coordinator is None:
            raise ServiceValidationError(f"Device {device_name} is not loaded")
        if not coordinator.last_update_success:
            raise ServiceValidationError(f"Device {device_name} is not available")

        now = dt_util.now()
        time = call.data.get(ATTR_TIME, now.time())
        weekday = call.data.get(ATTR_WEEKDAY, ArgoWeekday.from_datetime(now))
        coordinator.data.set_current_weekday(weekday)
        coordinator.data.set_time(time.hour, time.minute)
        await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_TIME,
        verify_domain_control(DOMAIN)(set_time),
        schema=vol.Schema(
            {
                vol.Required(ATTR_DEVICE): device,
                vol.Optional(ATTR_TIME): cv.time,
                vol.Optional(ATTR_WEEKDAY): _weekday,
            }
        ),
    )
