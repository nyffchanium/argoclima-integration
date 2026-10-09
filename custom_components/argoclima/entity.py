from custom_components.argoclima.const import DOMAIN
from custom_components.argoclima.const import MANUFACTURER
from custom_components.argoclima.runtime import ArgoRuntimeDevice
from custom_components.argoclima.unique_id import entity_unique_id
from custom_components.argoclima.update_coordinator import ArgoDataUpdateCoordinator
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity


class ArgoEntity(CoordinatorEntity):
    coordinator: ArgoDataUpdateCoordinator

    def __init__(
        self,
        entity_name: str,
        device: ArgoRuntimeDevice,
        device_class: str = None,
        entity_category: EntityCategory = None,
    ):
        super().__init__(device.coordinator)
        self._type = device.type
        self._entity_name = entity_name
        self._device = device
        self._device_class = device_class
        self._entity_category = entity_category

    @property
    def unique_id(self) -> str:
        return entity_unique_id(self._device.device_id, self._entity_name)

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def name(self):
        return f"{self._device.title} {self._entity_name}"

    @property
    def device_class(self) -> str:
        return self._device_class

    @property
    def entity_category(self) -> str:
        return self._entity_category

    @property
    def device_info(self):
        device_info = {
            "identifiers": {(DOMAIN, self._device.device_id)},
            "name": self._device.title,
            "model": self._type.name,
            "sw_version": self.coordinator.data.firmware_version
            if self.coordinator.data is not None
            else None,
            "manufacturer": MANUFACTURER,
        }
        return device_info
