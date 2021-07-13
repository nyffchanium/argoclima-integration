from typing import Callable
from typing import List

from custom_components.argoclima.const import DOMAIN
from custom_components.argoclima.device_type import InvalidOperationError
from custom_components.argoclima.entity import ArgoEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_devices: Callable[[List[SwitchEntity]], None],
):
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_devices([ArgoDeviceLightSwitch(coordinator, entry)])


class ArgoDeviceLightSwitch(ArgoEntity, SwitchEntity):
    def __init__(self, coordinator, entry: ConfigEntry):
        ArgoEntity.__init__(self, "Device Light", coordinator, entry, "switch")
        SwitchEntity.__init__(self)

    @property
    def icon(self) -> str:
        return "mdi:lightbulb"

    @property
    def is_on(self) -> bool:
        if not self._type.device_lights:
            raise InvalidOperationError
        return self.coordinator.data.light

    async def async_turn_on(self, **kwargs) -> None:
        if not self._type.device_lights:
            raise InvalidOperationError
        self.coordinator.data.light = True
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        if not self._type.device_lights:
            raise InvalidOperationError
        self.coordinator.data.light = False
        await self.coordinator.async_request_refresh()
