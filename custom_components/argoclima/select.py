from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import ArgoEntity
from .runtime import ArgoRuntimeDevice
from .runtime import runtime_devices_for_entry
from .types import ArgoTimerType
from .types import ArgoUnit


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    entities = []
    for device in runtime_devices_for_entry(hass, entry):
        if device.type.unit:
            entities.append(ArgoUnitSelect(device))
        if device.type.timer:
            entities.append(ArgoTimerSelect(device))
    async_add_entities(entities)


class ArgoUnitSelect(ArgoEntity, SelectEntity):
    _attr_options = [unit.to_ha_unit() for unit in ArgoUnit]

    def __init__(self, device: ArgoRuntimeDevice) -> None:
        super().__init__("Display Unit", device, None, EntityCategory.CONFIG)

    @property
    def current_option(self) -> str | None:
        unit = self.coordinator.data.unit
        return unit.to_ha_unit() if unit is not None else None

    async def async_select_option(self, option: str) -> None:
        self.coordinator.data.unit = ArgoUnit.from_ha_unit(option)
        await self.coordinator.async_request_refresh()


class ArgoTimerSelect(ArgoEntity, SelectEntity):
    def __init__(self, device: ArgoRuntimeDevice) -> None:
        super().__init__("Active Timer", device, None, EntityCategory.CONFIG)
        self._attr_options = [str(timer) for timer in device.type.timers]

    @property
    def current_option(self) -> str | None:
        timer = self.coordinator.data.timer
        return str(timer) if timer is not None else None

    async def async_select_option(self, option: str) -> None:
        self.coordinator.data.timer = ArgoTimerType[option.upper()]
        await self.coordinator.async_request_refresh()
