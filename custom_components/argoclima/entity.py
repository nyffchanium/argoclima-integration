import hashlib
import uuid

from custom_components.argoclima import ArgoDataUpdateCoordinator
from custom_components.argoclima.const import CONF_DEVICE_TYPE
from custom_components.argoclima.const import DOMAIN
from custom_components.argoclima.const import MANUFACTURER
from custom_components.argoclima.device_type import ArgoDeviceType
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity


class ArgoEntity(CoordinatorEntity):
    coordinator: ArgoDataUpdateCoordinator

    def __init__(
        self,
        entity_name: str,
        coordinator: ArgoDataUpdateCoordinator,
        entry: ConfigEntry,
        device_class: str = None,
        entity_category: EntityCategory = None,
    ):
        super().__init__(coordinator)
        self._type = ArgoDeviceType.from_name(entry.data[CONF_DEVICE_TYPE])
        self._entity_name = entity_name
        self._entry = entry
        self._device_class = device_class
        self._entity_category = entity_category

    @property
    def unique_id(self) -> str:
        return uuid.UUID(
            hashlib.md5((self._entry.entry_id + self.name).encode("utf-8")).hexdigest()
        ).hex

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def name(self):
        return f"{self._entry.title} {self._entity_name}"

    @property
    def device_class(self) -> str:
        return self._device_class

    @property
    def entity_category(self) -> str:
        return self._entity_category

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._entry.title,
            "model": self._type.name,
            "sw_version": self.coordinator.data.firmware_version
            if self.coordinator.data is not None
            else None,
            "manufacturer": MANUFACTURER,
        }
