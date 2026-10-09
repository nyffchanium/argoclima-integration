from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_CPU_ID
from .const import CONF_DEVICE_TYPE
from .const import CONF_DEVICES
from .const import CONF_HOST
from .const import CONF_HUB_ID
from .const import CONF_ROLE
from .const import DOMAIN
from .const import DUMMY_SERVER_DEVICE_IDENTIFIER_PREFIX
from .const import DUMMY_SERVER_UNIQUE_ID_PREFIX
from .const import ENTRY_ROLE_DEVICE
from .const import ENTRY_ROLE_HUB
from .device_type import ArgoDeviceType
from .update_coordinator import ArgoDataUpdateCoordinator


@dataclass
class ArgoRuntimeDevice:
    """Runtime data for one actual Argoclima appliance."""

    entry_id: str
    device_id: str
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
                device_id=entry.entry_id,
                title=entry.title,
                data=entry.data,
                type=device_type,
                coordinator=runtime,
            )
        ]
    return []


def async_entry_role(entry: ConfigEntry) -> str:
    """Return the configured entry role, defaulting entries to device."""
    return entry.data.get(CONF_ROLE, ENTRY_ROLE_DEVICE)


def dummy_server_unique_id(port: int) -> str:
    """Return the unique id for a dummy server listening on port."""
    return f"{DUMMY_SERVER_UNIQUE_ID_PREFIX}:{port}"


def dummy_server_hub_id(entry: ConfigEntry) -> str:
    """Return the stable hub device identifier for a dummy server entry."""
    return entry.data.get(
        CONF_HUB_ID,
        f"{DUMMY_SERVER_DEVICE_IDENTIFIER_PREFIX}:{entry.entry_id}",
    )


def hub_entry_for_id(hass: HomeAssistant, hub_id: str) -> ConfigEntry | None:
    """Return the hub config entry for a stable hub id, if it's set up."""
    for entry in hass.config_entries.async_entries(DOMAIN):
        if (
            async_entry_role(entry) == ENTRY_ROLE_HUB
            and dummy_server_hub_id(entry) == hub_id
        ):
            return entry
    return None


def match_hub_device_id(
    devices: Mapping[str, Mapping[str, Any]],
    cpu_id: str | None,
    host: str | None,
) -> str | None:
    """Return the key of the stored hub device matching a CPU_ID or host.

    A host only matches devices whose CPU_ID is still unknown, so a manually
    added device keeps its key once it reports its CPU_ID.
    """
    if cpu_id is not None:
        for existing_id, existing in devices.items():
            if existing.get(CONF_CPU_ID) == cpu_id:
                return existing_id
    if host is not None:
        for existing_id, existing in devices.items():
            if existing.get(CONF_HOST) == host and existing.get(CONF_CPU_ID) in (
                None,
                cpu_id,
            ):
                return existing_id
    return None


def async_update_hub_device(
    hass: HomeAssistant, hub_entry: ConfigEntry, device_data: Mapping[str, Any]
) -> str:
    """Create or update a hub device record and return its key.

    The key is the device's permanent identity and never changes once assigned.
    """
    devices = dict(hub_entry.data.get(CONF_DEVICES, {}))
    device_id = (
        match_hub_device_id(
            devices, device_data.get(CONF_CPU_ID), device_data.get(CONF_HOST)
        )
        or uuid.uuid4().hex
    )
    _remove_duplicate_hosts(devices, device_id, device_data.get(CONF_HOST))
    devices[device_id] = {**devices.get(device_id, {}), **device_data}
    hass.config_entries.async_update_entry(
        hub_entry,
        data={**hub_entry.data, CONF_DEVICES: devices},
    )
    return device_id


def _remove_duplicate_hosts(
    devices: dict[str, dict[str, Any]], device_id: str, host: str | None
) -> None:
    if host is None:
        return
    for existing_id, existing_data in list(devices.items()):
        if existing_id != device_id and existing_data.get(CONF_HOST) == host:
            devices.pop(existing_id)
