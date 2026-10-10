from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .const import MANUFACTURER
from .data import ArgoData
from .runtime import ArgoRuntimeDevice
from .unique_id import entity_unique_id
from .update_coordinator import ArgoDataUpdateCoordinator


def firmware_label(data: ArgoData | None) -> str | None:
    """Return the firmware versions as shown in the device info."""
    if data is None or data.firmware_version is None:
        return None
    label = f"{data.firmware_version:05d}"
    if data.wifi_firmware_version:
        label += f" (WiFi {data.wifi_firmware_version})"
    return label


class ArgoEntity(CoordinatorEntity[ArgoDataUpdateCoordinator]):
    def __init__(
        self,
        entity_name: str,
        device: ArgoRuntimeDevice,
        device_class: str | None = None,
        entity_category: EntityCategory | None = None,
    ) -> None:
        super().__init__(device.coordinator)
        self._type = device.type
        self._device = device
        self._attr_unique_id = entity_unique_id(device.device_id, entity_name)
        self._attr_name = f"{device.title} {entity_name}"
        self._attr_device_class = device_class
        self._attr_entity_category = entity_category

    async def _async_send_changes(self) -> None:
        """Show requested changes right away and send them to the device."""
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._async_update_device_firmware()
        super()._handle_coordinator_update()

    @callback
    def _async_update_device_firmware(self) -> None:
        # Device info is only read when the entity is added, before devices
        # behind the dummy server have reported their firmware.
        sw_version = firmware_label(self.coordinator.data)
        if sw_version is None:
            return
        registry = dr.async_get(self.hass)
        for device in dr.async_entries_for_config_entry(
            registry, self._device.entry_id
        ):
            if (DOMAIN, self._device.device_id) in device.identifiers:
                if device.sw_version != sw_version:
                    registry.async_update_device(device.id, sw_version=sw_version)
                return

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._device.device_id)},
            name=self._device.title,
            model=self._type.name,
            manufacturer=MANUFACTURER,
            sw_version=firmware_label(self.coordinator.data),
        )
