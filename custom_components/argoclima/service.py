import logging
from datetime import datetime
from datetime import time as dt_time
from typing import Any
from typing import cast

import homeassistant.helpers.config_validation as cv
import homeassistant.helpers.device_registry as dr
import voluptuous as vol
from custom_components.argoclima.const import DOMAIN
from custom_components.argoclima.types import ArgoWeekday
from custom_components.argoclima.update_coordinator import ArgoDataUpdateCoordinator
from homeassistant.core import HomeAssistant
from homeassistant.helpers.service import verify_domain_control
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)
ATTR_DEVICE = "device"
ATTR_TIME = "time"
ATTR_WEEKDAY = "weekday"


async def setup_service(hass: HomeAssistant):
    async def _set_time(call, **kwargs) -> None:
        device: dr.DeviceEntry = call.data.get(ATTR_DEVICE)
        time: dt_time = call.data.get(ATTR_TIME)
        weekday: ArgoWeekday = call.data.get(ATTR_WEEKDAY)
        entry_id = next(iter(device.config_entries))
        if entry_id not in hass.data[DOMAIN]:
            _LOGGER.warning(
                "Device %s is not loaded.", device.name_by_user or device.name
            )
            return
        coordinator: ArgoDataUpdateCoordinator = hass.data[DOMAIN][entry_id]
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

    def weekday(value: Any) -> ArgoWeekday:
        """Validate a weekday."""
        value: str = str(value).lower()
        if value in ["0", "sunday"]:
            return ArgoWeekday(0)
        elif value in ["1", "monday"]:
            return ArgoWeekday(1)
        elif value in ["2", "tuesday"]:
            return ArgoWeekday(2)
        elif value in ["3", "wednesday"]:
            return ArgoWeekday(3)
        elif value in ["4", "thursday"]:
            return ArgoWeekday(4)
        elif value in ["5", "friday"]:
            return ArgoWeekday(5)
        elif value in ["6", "saturday"]:
            return ArgoWeekday(6)
        else:
            raise vol.Invalid("Invalid weekday")

    def device(value: Any) -> dr.DeviceEntry:
        """Validate that the device exists."""
        device_registry = cast(dr.DeviceRegistry, hass.data[dr.DATA_REGISTRY])
        try:
            return device_registry.devices[str(value)]
        except:  # noqa: E722 pylint: disable=bare-except
            raise vol.Invalid(f"Could not find device with ID {value}")

    hass.services.async_register(
        DOMAIN,
        "set_time",
        verify_domain_control(hass, DOMAIN)(_set_time),
        schema=vol.Schema(
            {
                vol.Required(ATTR_DEVICE): device,
                vol.Optional(ATTR_TIME): cv.time,
                vol.Optional(ATTR_WEEKDAY): weekday,
            }
        ),
    )
