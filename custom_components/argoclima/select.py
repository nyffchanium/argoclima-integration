from typing import Callable
from typing import List

from custom_components.argoclima.data import ArgoData
from custom_components.argoclima.device_type import ArgoDeviceType
from custom_components.argoclima.device_type import InvalidOperationError
from custom_components.argoclima.types import ArgoUnit
from homeassistant.components.select import (
    SelectEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_DEVICE_TYPE
from .const import DOMAIN
from .entity import ArgoEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_devices: Callable[[List[SelectEntity]], None],
):
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    type = ArgoDeviceType.from_name(entry.data[CONF_DEVICE_TYPE])
    if type.unit:
        entities.append(ArgoUnitSelect(coordinator, entry))

    async_add_devices(entities)


class ArgoUnitSelect(ArgoEntity, SelectEntity):
    def __init__(self, coordinator, entry: ConfigEntry):
        ArgoEntity.__init__(self, "Display Unit", coordinator, entry)
        SelectEntity.__init__(self)

    @property
    def current_option(self) -> str:
        if not self._type.unit:
            raise InvalidOperationError
        return self.coordinator.data.unit.to_ha_unit()

    @property
    def options(self) -> List[str]:
        if not self._type.unit:
            raise InvalidOperationError
        list = []
        for unit in ArgoUnit:
            list.append(unit.to_ha_unit())
        return list

    async def async_select_option(self, option: str) -> None:
        if not self._type.unit:
            raise InvalidOperationError
        data = ArgoData(self._type)
        data.unit = ArgoUnit.from_ha_unit(option)
        await self.coordinator.api.async_call_api(data)
        await self.coordinator.async_request_refresh()
