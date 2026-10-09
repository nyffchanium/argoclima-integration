import asyncio
import logging

import homeassistant.helpers.device_registry as dr
import homeassistant.helpers.entity_registry as er
from custom_components.argoclima.api import ArgoApiClient
from custom_components.argoclima.const import CONF_CPU_ID
from custom_components.argoclima.const import CONF_DEVICE_TYPE
from custom_components.argoclima.const import CONF_DEVICES
from custom_components.argoclima.const import CONF_HUB_ID
from custom_components.argoclima.const import CONF_HOST
from custom_components.argoclima.const import CONF_NAME
from custom_components.argoclima.const import CONF_PORT
from custom_components.argoclima.const import DOMAIN
from custom_components.argoclima.const import DUMMY_SERVER_DEFAULT_PORT
from custom_components.argoclima.const import ENTRY_ROLE_DEVICE
from custom_components.argoclima.const import ENTRY_ROLE_HUB
from custom_components.argoclima.const import STARTUP_MESSAGE
from custom_components.argoclima.device_type import ArgoDeviceType
from custom_components.argoclima.dummy_server import ArgoDummyServer
from custom_components.argoclima.dummy_server import async_dummy_server_running
from custom_components.argoclima.runtime import ArgoHubRuntime
from custom_components.argoclima.runtime import ArgoRuntimeDevice
from custom_components.argoclima.runtime import async_entry_role
from custom_components.argoclima.runtime import dummy_server_hub_id
from custom_components.argoclima.service import setup_service
from custom_components.argoclima.unique_id import legacy_unique_id_migrations
from custom_components.argoclima.update_coordinator import ArgoDataUpdateCoordinator
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.core_config import Config
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession


_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup(hass: HomeAssistant, config: Config):
    await setup_service(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up this integration using UI."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})
        _LOGGER.info(STARTUP_MESSAGE)

    role = async_entry_role(entry)
    if role == ENTRY_ROLE_HUB:
        return await _async_setup_hub_entry(hass, entry)

    if role != ENTRY_ROLE_DEVICE:
        raise ConfigEntryNotReady(f"Unsupported Argoclima entry role: {role}")

    type = ArgoDeviceType.from_name(entry.data.get(CONF_DEVICE_TYPE))
    if type is None:
        raise ConfigEntryNotReady("Unsupported Argoclima device type")

    host: str = entry.data.get(CONF_HOST)

    session = async_get_clientsession(hass)
    client = ArgoApiClient(type, host, session)

    has_hub = entry.data.get(CONF_HUB_ID) is not None
    coordinator = ArgoDataUpdateCoordinator(
        hass,
        client,
        type,
        use_polling=not _async_entry_has_running_hub(hass, entry),
    )

    if has_hub:
        coordinator.async_set_updated_data(coordinator.data)
    else:
        await coordinator.async_refresh()
        if not coordinator.last_update_success:
            raise ConfigEntryNotReady

    hass.data[DOMAIN][entry.entry_id] = coordinator

    _async_migrate_legacy_unique_ids(hass, entry)
    coordinator.platforms.extend(type.platforms)
    await hass.config_entries.async_forward_entry_setups(entry, type.platforms)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def _async_setup_hub_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hub_id = dummy_server_hub_id(entry)
    port = entry.data.get(CONF_PORT, DUMMY_SERVER_DEFAULT_PORT)
    server = ArgoDummyServer(hass, port, hub_id)
    try:
        await server.async_start()
    except OSError as err:
        _LOGGER.error(
            "Failed to start Argoclima dummy server on port %s: %s", port, err
        )
        raise ConfigEntryNotReady(str(err)) from err

    runtime = ArgoHubRuntime(server=server, devices={}, platforms=set())
    hass.data[DOMAIN][entry.entry_id] = runtime
    _async_setup_hub_devices(hass, entry, runtime)
    if runtime.platforms:
        await hass.config_entries.async_forward_entry_setups(entry, runtime.platforms)
    _async_set_push_updates_enabled(hass, True)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    role = async_entry_role(entry)
    if role == ENTRY_ROLE_HUB:
        runtime = hass.data[DOMAIN].pop(entry.entry_id, None)
        if isinstance(runtime, ArgoHubRuntime) and runtime.platforms:
            await hass.config_entries.async_unload_platforms(entry, runtime.platforms)
        if isinstance(runtime, ArgoHubRuntime):
            await runtime.server.async_stop()
        elif isinstance(runtime, ArgoDummyServer):
            await runtime.async_stop()
        _async_set_push_updates_enabled(hass, async_dummy_server_running(hass))
        return True

    coordinator = hass.data[DOMAIN].get(entry.entry_id)
    if coordinator is None:
        return True
    type: ArgoDeviceType = ArgoDeviceType.from_name(entry.data.get(CONF_DEVICE_TYPE))
    unloaded = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in type.platforms
                if platform in coordinator.platforms
            ]
        )
    )
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unloaded


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: ConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Allow a hub child device to be removed from the UI."""
    if async_entry_role(entry) != ENTRY_ROLE_HUB:
        return False

    device_id = _hub_child_device_id(entry, device_entry)
    if device_id is None:
        return False

    runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if isinstance(runtime, ArgoHubRuntime):
        runtime.devices.pop(device_id, None)

    devices = dict(entry.data.get(CONF_DEVICES, {}))
    devices.pop(device_id)
    # This alone reloads the hub entry via the update listener registered
    # in _async_setup_hub_entry - no separate explicit reload needed.
    hass.config_entries.async_update_entry(
        entry,
        data={**entry.data, CONF_DEVICES: devices},
    )

    return True


def _async_migrate_legacy_unique_ids(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Move entities of older versions onto the current unique_id format.

    Keeps entity ids, history, names and areas when switching over from
    nyffchanium/argoclima-integration or an earlier fork version. Only
    standalone device entries need this - hub entries didn't exist there.
    """
    registry = er.async_get(hass)
    registry_entries = er.async_entries_for_config_entry(registry, entry.entry_id)
    migrations = legacy_unique_id_migrations(
        entry.entry_id,
        entry.title,
        entry.data.get(CONF_CPU_ID),
        {registry_entry.unique_id for registry_entry in registry_entries},
    )
    for registry_entry in registry_entries:
        new_unique_id = migrations.get(registry_entry.unique_id)
        if new_unique_id is None:
            continue
        _LOGGER.info(
            "Migrating unique_id of %s from %s to %s",
            registry_entry.entity_id,
            registry_entry.unique_id,
            new_unique_id,
        )
        registry.async_update_entity(
            registry_entry.entity_id, new_unique_id=new_unique_id
        )


def _async_set_push_updates_enabled(hass: HomeAssistant, enabled: bool) -> None:
    for entry_id, value in hass.data.get(DOMAIN, {}).items():
        if isinstance(value, ArgoDataUpdateCoordinator):
            entry = hass.config_entries.async_get_entry(entry_id)
            value.async_set_push_updates_enabled(
                enabled
                and entry is not None
                and _async_entry_has_running_hub(hass, entry)
            )
        elif isinstance(value, ArgoHubRuntime):
            for device in value.devices.values():
                device.coordinator.async_set_push_updates_enabled(enabled)


def _async_entry_has_running_hub(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Return true if the device entry is associated with a loaded hub."""
    hub_id = entry.data.get(CONF_HUB_ID)
    return hub_id is not None and _async_hub_running(hass, hub_id)


def _async_hub_running(hass: HomeAssistant, hub_id: str) -> bool:
    for entry in hass.config_entries.async_entries(DOMAIN):
        if async_entry_role(entry) != ENTRY_ROLE_HUB:
            continue
        if dummy_server_hub_id(entry) != hub_id:
            continue
        runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id)
        return isinstance(runtime, ArgoHubRuntime) or isinstance(
            runtime, ArgoDummyServer
        )
    return False


def _hub_child_device_id(entry: ConfigEntry, device_entry: dr.DeviceEntry) -> str | None:
    devices = entry.data.get(CONF_DEVICES, {})
    for domain, identifier in device_entry.identifiers:
        if domain == DOMAIN and identifier in devices:
            return identifier
    return None


def _async_setup_hub_devices(
    hass: HomeAssistant, entry: ConfigEntry, runtime: ArgoHubRuntime
) -> None:
    session = async_get_clientsession(hass)
    for device_id, device_data in entry.data.get(CONF_DEVICES, {}).items():
        host = device_data.get(CONF_HOST)
        if host is None:
            continue
        device_type = ArgoDeviceType.from_name(device_data.get(CONF_DEVICE_TYPE))
        if device_type is None:
            continue
        client = ArgoApiClient(device_type, host, session)
        coordinator = ArgoDataUpdateCoordinator(
            hass,
            client,
            device_type,
            use_polling=False,
        )
        coordinator.async_set_updated_data(coordinator.data)
        runtime.devices[device_id] = ArgoRuntimeDevice(
            entry_id=entry.entry_id,
            device_id=device_id,
            title=device_data.get(CONF_NAME, entry.title),
            data=device_data,
            type=device_type,
            coordinator=coordinator,
        )
        runtime.platforms.update(device_type.platforms)


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
