import hashlib
import uuid

from custom_components.argoclima import ArgoDataUpdateCoordinator
from custom_components.argoclima.const import CONF_DEVICE_TYPE
from custom_components.argoclima.device_type import DeviceType
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_NAME
from .const import DOMAIN
from .const import MANUFACTURER


class ArgoEntity(CoordinatorEntity):
    coordinator: ArgoDataUpdateCoordinator

    def __init__(
        self,
        entity_name: str,
        coordinator: ArgoDataUpdateCoordinator,
        entry: ConfigEntry,
    ):
        super().__init__(coordinator)
        self._type = DeviceType.from_name(entry.data[CONF_DEVICE_TYPE])
        self._entity_name = entity_name
        self._entry = entry

    @property
    def unique_id(self) -> str:
        """Return a unique ID to use for this entity."""
        return uuid.UUID(
            hashlib.md5((self._entry.entry_id + self.name).encode("utf-8")).hexdigest()
        ).hex

    @property
    def name(self):
        return f"{self._entry.data[CONF_NAME]} {self._entity_name}"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self._entry.data[CONF_NAME],
            "model": self._type.name,
            "sw_version": self.coordinator.data.firmware_version,
            "manufacturer": MANUFACTURER,
        }
