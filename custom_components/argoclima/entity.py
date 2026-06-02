import hashlib
import uuid

import homeassistant.helpers.device_registry as dr
from custom_components.argoclima.const import CONF_CPU_ID
from custom_components.argoclima.const import CONF_DEVICE_TYPE
from custom_components.argoclima.const import CONF_HUB_ID
from custom_components.argoclima.const import DOMAIN
from custom_components.argoclima.const import MANUFACTURER
from custom_components.argoclima.device_type import ArgoDeviceType
from custom_components.argoclima.update_coordinator import ArgoDataUpdateCoordinator
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
        device_identifier = self._entry.data.get(CONF_CPU_ID) or self._entry.entry_id
        device_info = {
            "identifiers": {(DOMAIN, device_identifier)},
            "name": self._entry.title,
            "model": self._type.name,
            "sw_version": self.coordinator.data.firmware_version
            if self.coordinator.data is not None
            else None,
            "manufacturer": MANUFACTURER,
        }
        if (hub_id := self._entry.data.get(CONF_HUB_ID)) and _hub_device_exists(
            self.coordinator.hass, hub_id
        ):
            device_info["via_device"] = (DOMAIN, hub_id)
        return device_info


def _hub_device_exists(hass, hub_id: str) -> bool:
    device_registry = dr.async_get(hass)
    return (
        device_registry.async_get_device(identifiers={(DOMAIN, hub_id)})
        is not None
    )
