from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Mapping

from custom_components.argoclima.const import CONF_DEVICE_TYPE
from custom_components.argoclima.const import DOMAIN
from custom_components.argoclima.device_type import ArgoDeviceType
from custom_components.argoclima.update_coordinator import ArgoDataUpdateCoordinator
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


@dataclass
class ArgoRuntimeDevice:
    """Runtime data for one actual Argoclima appliance."""

    entry_id: str
    title: str
    data: Mapping[str, Any]
    type: ArgoDeviceType
    coordinator: ArgoDataUpdateCoordinator


@dataclass
class ArgoHubRuntime:
    """Runtime data for one dummy server hub and its child devices."""

    server: Any
    devices: dict[str, ArgoRuntimeDevice]
    platforms: set[str]


def runtime_devices_for_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> list[ArgoRuntimeDevice]:
    """Return actual appliance runtimes owned by a config entry."""
    runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if isinstance(runtime, ArgoHubRuntime):
        return list(runtime.devices.values())
    if isinstance(runtime, ArgoDataUpdateCoordinator):
        device_type = ArgoDeviceType.from_name(entry.data.get(CONF_DEVICE_TYPE))
        if device_type is None:
            return []
        return [
            ArgoRuntimeDevice(
                entry_id=entry.entry_id,
                title=entry.title,
                data=entry.data,
                type=device_type,
                coordinator=runtime,
            )
        ]
    return []
