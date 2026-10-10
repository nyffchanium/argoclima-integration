from homeassistant.components.update import UpdateEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_HUB_ID
from .const import DOCUMENTATION_URL
from .entity import ArgoEntity
from .firmware import FIRMWARE_UNIT
from .firmware import FIRMWARE_WIFI
from .firmware import async_get_firmware_coordinator
from .runtime import ArgoRuntimeDevice
from .runtime import runtime_devices_for_entry


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    entities: list[ArgoFirmwareUpdate] = []
    for device in runtime_devices_for_entry(hass, entry):
        entities.append(ArgoUnitFirmwareUpdate(device))
        # Only reports through the dummy server include the WiFi firmware.
        if device.data.get(CONF_HUB_ID) is not None:
            entities.append(ArgoWifiFirmwareUpdate(device))
    async_add_entities(entities)


class ArgoFirmwareUpdate(ArgoEntity, UpdateEntity):
    """Compare a device's firmware with the latest version Argo publishes."""

    _attr_entity_registry_enabled_default = False
    _attr_release_summary = (
        "Install updates with the official Argo web app. If you use the dummy "
        "server, disable its DNAT rule while updating."
    )
    _attr_release_url = (
        f"{DOCUMENTATION_URL}/blob/master/docs/features.md#firmware-updates"
    )
    _firmware: str

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        coordinator = async_get_firmware_coordinator(self.hass)
        self.async_on_remove(coordinator.async_add_listener(self.async_write_ha_state))
        if coordinator.data is None:
            self.hass.async_create_background_task(
                coordinator.async_request_refresh(), "argoclima firmware check"
            )

    @property
    def latest_version(self) -> str | None:
        data = async_get_firmware_coordinator(self.hass).data
        return data.get(self._firmware) if data else None


class ArgoUnitFirmwareUpdate(ArgoFirmwareUpdate):
    _firmware = FIRMWARE_UNIT

    def __init__(self, device: ArgoRuntimeDevice) -> None:
        super().__init__("Firmware", device, None, EntityCategory.DIAGNOSTIC)

    @property
    def installed_version(self) -> str | None:
        version = self.coordinator.data.firmware_version
        return f"{version:05d}" if version is not None else None


class ArgoWifiFirmwareUpdate(ArgoFirmwareUpdate):
    _firmware = FIRMWARE_WIFI

    def __init__(self, device: ArgoRuntimeDevice) -> None:
        super().__init__("WiFi Firmware", device, None, EntityCategory.DIAGNOSTIC)

    @property
    def installed_version(self) -> str | None:
        return self.coordinator.data.wifi_firmware_version
