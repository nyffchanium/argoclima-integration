from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from custom_components.argoclima.const import CONF_CPU_ID
from custom_components.argoclima.const import CONF_DEVICE_TYPE
from custom_components.argoclima.const import CONF_DEVICES
from custom_components.argoclima.const import CONF_HOST
from custom_components.argoclima.const import CONF_HUB_ID
from custom_components.argoclima.const import CONF_ROLE
from custom_components.argoclima.const import DOMAIN
from custom_components.argoclima.const import DUMMY_SERVER_DEVICE_IDENTIFIER_PREFIX
from custom_components.argoclima.const import DUMMY_SERVER_UNIQUE_ID_PREFIX
from custom_components.argoclima.const import ENTRY_ROLE_DEVICE
from custom_components.argoclima.const import ENTRY_ROLE_HUB
from custom_components.argoclima.device_type import ArgoDeviceType
from custom_components.argoclima.update_coordinator import ArgoDataUpdateCoordinator
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


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
                # A standalone device's own config entry never gets
                # recreated, so its entry_id is already a permanent,
                # unique identity - no need for anything derived from
                # data that can change later (like the CPU_ID, which
                # may only become known after this device has already
                # been set up).
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
    """Find the permanent device key of an existing hub-child device.

    Each hub-child device keeps one permanent key for its whole
    lifetime (assigned once, the first time it's added) - that key is
    what unique_id/device identifiers are built from, so it must never
    be swapped out later. This only looks the key up; it never
    allocates a new one (see `async_update_hub_device` for that).

    Matches by CPU_ID first, since that's the device's real identity
    once it's known. Falls back to matching by host, but only against
    a device that hasn't been identified by a CPU_ID yet - that's what
    lets a manually-added device (known only by its IP at first) keep
    its original key once it starts pushing its real CPU_ID, instead
    of being treated as a brand new device.
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
    """Create or update a hub-child device record.

    Reuses the device's existing permanent key if one is found (see
    `match_hub_device_id`), otherwise allocates a new one. Returns the
    key the device is stored under.
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
    """Drop any other device record pointing at the same host.

    Two different permanent keys should never end up representing the
    same physical device/host at once; this cleans up the rare case
    that could otherwise happen (e.g. a stale record left behind).
    """
    if host is None:
        return
    for existing_id, existing_data in list(devices.items()):
        if existing_id != device_id and existing_data.get(CONF_HOST) == host:
            devices.pop(existing_id)
