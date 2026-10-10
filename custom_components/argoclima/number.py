from homeassistant.components.number import NumberEntity
from homeassistant.components.number import NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import ArgoEntity
from .runtime import ArgoRuntimeDevice
from .runtime import runtime_devices_for_entry


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities(
        ArgoEcoLimitNumber(device)
        for device in runtime_devices_for_entry(hass, entry)
        if device.type.eco_limit
    )


class ArgoEcoLimitNumber(ArgoEntity, NumberEntity):
    _attr_icon = "mdi:leaf"
    _attr_mode = NumberMode.BOX
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, device: ArgoRuntimeDevice) -> None:
        super().__init__("Eco Mode Power Limit", device, None, EntityCategory.CONFIG)
        self._attr_native_min_value = device.type.eco_limit_min
        self._attr_native_max_value = device.type.eco_limit_max

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.eco_limit

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.data.eco_limit = int(value)
        await self._async_send_changes()
