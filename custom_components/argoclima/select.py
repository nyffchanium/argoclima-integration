from collections.abc import Callable

from custom_components.argoclima.device_type import InvalidOperationError
from custom_components.argoclima.entity import ArgoEntity
from custom_components.argoclima.runtime import ArgoRuntimeDevice
from custom_components.argoclima.runtime import runtime_devices_for_entry
from custom_components.argoclima.types import ArgoTimerType
from custom_components.argoclima.types import ArgoUnit
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_devices: Callable[[list[SelectEntity]], None],
):
    entities = []
    for device in runtime_devices_for_entry(hass, entry):
        if device.type.unit:
            entities.append(ArgoUnitSelect(device))
        if device.type.timer:
            entities.append(ArgoTimerSelect(device))

    async_add_devices(entities)


class ArgoUnitSelect(ArgoEntity, SelectEntity):
    def __init__(self, device: ArgoRuntimeDevice):
        ArgoEntity.__init__(
            self, "Display Unit", device, None, EntityCategory.CONFIG
        )
        SelectEntity.__init__(self)

    @property
    def current_option(self) -> str:
        if not self._type.unit:
            raise InvalidOperationError
        return self.coordinator.data.unit.to_ha_unit()

    @property
    def options(self) -> list[str]:
        if not self._type.unit:
            raise InvalidOperationError
        list = []
        for unit in ArgoUnit:
            list.append(unit.to_ha_unit())
        return list

    async def async_select_option(self, option: str) -> None:
        if not self._type.unit:
            raise InvalidOperationError
        self.coordinator.data.unit = ArgoUnit.from_ha_unit(option)
        await self.coordinator.async_request_refresh()


class ArgoTimerSelect(ArgoEntity, SelectEntity):
    def __init__(self, device: ArgoRuntimeDevice):
        ArgoEntity.__init__(
            self, "Active Timer", device, None, EntityCategory.CONFIG
        )
        SelectEntity.__init__(self)

    @property
    def current_option(self) -> str:
        if not self._type.timer:
            raise InvalidOperationError
        return self.coordinator.data.timer.__str__()

    @property
    def options(self) -> list[str]:
        if not self._type.timer:
            raise InvalidOperationError
        list = []
        for type in self._type.timers:
            list.append(type.__str__())
        return list

    async def async_select_option(self, option: str) -> None:
        if not self._type.timer:
            raise InvalidOperationError
        self.coordinator.data.timer = ArgoTimerType[option.upper()]
        await self.coordinator.async_request_refresh()
