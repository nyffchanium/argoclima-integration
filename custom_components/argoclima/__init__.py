import asyncio
import logging

import homeassistant.helpers.device_registry as dr
from custom_components.argoclima.api import ArgoApiClient
from custom_components.argoclima.const import CONF_CPU_ID
from custom_components.argoclima.const import CONF_DEVICE_TYPE
from custom_components.argoclima.const import CONF_HUB_ID
from custom_components.argoclima.const import CONF_HOST
from custom_components.argoclima.const import CONF_PORT
from custom_components.argoclima.const import CONF_ROLE
from custom_components.argoclima.const import DOMAIN
from custom_components.argoclima.const import DUMMY_SERVER_DEFAULT_PORT
from custom_components.argoclima.const import DUMMY_SERVER_TITLE
from custom_components.argoclima.const import ENTRY_ROLE_DEVICE
from custom_components.argoclima.const import ENTRY_ROLE_HUB
from custom_components.argoclima.const import NAME
from custom_components.argoclima.const import STARTUP_MESSAGE
from custom_components.argoclima.device_type import ArgoDeviceType
from custom_components.argoclima.dummy_server import ArgoDummyServer
from custom_components.argoclima.dummy_server import async_dummy_server_running
from custom_components.argoclima.dummy_server import async_entry_role
from custom_components.argoclima.dummy_server import dummy_server_hub_id
from custom_components.argoclima.service import setup_service
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

    coordinator = ArgoDataUpdateCoordinator(
        hass,
        client,
        type,
        use_polling=not _async_entry_has_running_hub(hass, entry),
    )
    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    hass.data[DOMAIN][entry.entry_id] = coordinator

    coordinator.platforms.extend(type.platforms)
    await hass.config_entries.async_forward_entry_setups(entry, type.platforms)

    if hub_id := entry.data.get(CONF_HUB_ID):
        _async_update_device_registry_hub(
            hass, hub_id, _async_hub_device_id(hass, hub_id)
        )

    entry.add_update_listener(async_reload_entry)

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

    hass.data[DOMAIN][entry.entry_id] = server
    hub_device = _async_register_hub_device(hass, entry, hub_id)
    _async_update_device_registry_hub(hass, hub_id, hub_device.id)
    _async_set_push_updates_enabled(hass, True)
    entry.add_update_listener(async_reload_entry)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    role = async_entry_role(entry)
    if role == ENTRY_ROLE_HUB:
        server = hass.data[DOMAIN].pop(entry.entry_id, None)
        if isinstance(server, ArgoDummyServer):
            await server.async_stop()
        _async_update_device_registry_hub(hass, dummy_server_hub_id(entry), None)
        _async_set_push_updates_enabled(hass, async_dummy_server_running(hass))
        return True

    coordinator = hass.data[DOMAIN][entry.entry_id]
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


def _async_set_push_updates_enabled(hass: HomeAssistant, enabled: bool) -> None:
    for entry_id, value in hass.data.get(DOMAIN, {}).items():
        if isinstance(value, ArgoDataUpdateCoordinator):
            entry = hass.config_entries.async_get_entry(entry_id)
            value.async_set_push_updates_enabled(
                enabled
                and entry is not None
                and _async_entry_has_running_hub(hass, entry)
            )


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
        return isinstance(
            hass.data.get(DOMAIN, {}).get(entry.entry_id), ArgoDummyServer
        )
    return False


def _async_register_hub_device(hass: HomeAssistant, entry: ConfigEntry, hub_id: str):
    """Register the dummy server as the hub parent for pushed devices."""
    device_registry = dr.async_get(hass)
    return device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        entry_type=dr.DeviceEntryType.SERVICE,
        identifiers={(DOMAIN, hub_id)},
        manufacturer=NAME,
        name=entry.title or DUMMY_SERVER_TITLE,
        model="Dummy Server",
    )


def _async_update_device_registry_hub(
    hass: HomeAssistant, hub_id: str, hub_device_id: str | None
) -> None:
    """Link actual Argoclima devices through the dummy server hub."""
    device_registry = dr.async_get(hass)
    hub_entry = _async_hub_entry_for_id(hass, hub_id)
    for entry in hass.config_entries.async_entries(DOMAIN):
        if async_entry_role(entry) != ENTRY_ROLE_DEVICE:
            continue
        if entry.data.get(CONF_HUB_ID) != hub_id:
            continue

        device_identifier = entry.data.get(CONF_CPU_ID) or entry.entry_id
        device = device_registry.async_get_device(
            identifiers={(DOMAIN, device_identifier)}
        ) or device_registry.async_get_device(identifiers={(DOMAIN, entry.entry_id)})
        if device is None:
            continue

        if hub_entry is None or hub_device_id is None:
            _async_restore_device_registry_parent(device_registry, device, entry)
        else:
            _async_move_device_registry_parent(
                device_registry, device, entry, hub_entry, hub_device_id
            )


def _async_hub_entry_for_id(hass: HomeAssistant, hub_id: str) -> ConfigEntry | None:
    for entry in hass.config_entries.async_entries(DOMAIN):
        if (
            async_entry_role(entry) == ENTRY_ROLE_HUB
            and dummy_server_hub_id(entry) == hub_id
        ):
            return entry
    return None


def _async_hub_device_id(hass: HomeAssistant, hub_id: str) -> str | None:
    device_registry = dr.async_get(hass)
    hub_device = device_registry.async_get_device(identifiers={(DOMAIN, hub_id)})
    return None if hub_device is None else hub_device.id


def _async_move_device_registry_parent(
    device_registry: dr.DeviceRegistry,
    device: dr.DeviceEntry,
    entry: ConfigEntry,
    hub_entry: ConfigEntry,
    hub_device_id: str,
) -> None:
    """Make the hub the primary registry owner for a child device."""
    if (
        device.primary_config_entry == hub_entry.entry_id
        and device.via_device_id == hub_device_id
    ):
        return

    device = device_registry.async_update_device(
        device.id,
        add_config_entry_id=hub_entry.entry_id,
        device_info_type="primary",
        via_device_id=hub_device_id,
    )
    if device is None:
        return

    if (
        device.primary_config_entry != hub_entry.entry_id
        and entry.entry_id in device.config_entries
        and len(device.config_entries) > 1
    ):
        device = device_registry.async_update_device(
            device.id,
            remove_config_entry_id=entry.entry_id,
        )
        if device is None:
            return

    device_registry.async_update_device(
        device.id,
        add_config_entry_id=hub_entry.entry_id,
        device_info_type="primary",
        via_device_id=hub_device_id,
    )


def _async_restore_device_registry_parent(
    device_registry: dr.DeviceRegistry, device: dr.DeviceEntry, entry: ConfigEntry
) -> None:
    """Move a child device back to its own entry when its hub is unloaded."""
    device = device_registry.async_update_device(
        device.id,
        add_config_entry_id=entry.entry_id,
        device_info_type="primary",
    )
    if device is None:
        return

    if (
        device.primary_config_entry is not None
        and entry.entry_id != device.primary_config_entry
        and len(device.config_entries) > 1
    ):
        device = device_registry.async_update_device(
            device.id,
            remove_config_entry_id=device.primary_config_entry,
            via_device_id=None,
        )
        if device is None:
            return

    device_registry.async_update_device(
        device.id,
        add_config_entry_id=entry.entry_id,
        device_info_type="primary",
        via_device_id=None,
    )


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
