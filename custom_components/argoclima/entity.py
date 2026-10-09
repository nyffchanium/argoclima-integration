from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .const import MANUFACTURER
from .runtime import ArgoRuntimeDevice
from .unique_id import entity_unique_id
from .update_coordinator import ArgoDataUpdateCoordinator


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

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def device_info(self) -> DeviceInfo:
        firmware = (
            self.coordinator.data.firmware_version if self.coordinator.data else None
        )
        return DeviceInfo(
            identifiers={(DOMAIN, self._device.device_id)},
            name=self._device.title,
            model=self._type.name,
            manufacturer=MANUFACTURER,
            sw_version=str(firmware) if firmware is not None else None,
        )
