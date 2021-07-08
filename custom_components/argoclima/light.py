from typing import Callable
from typing import List

from custom_components.argoclima.device_type import InvalidOperationError
from homeassistant.components.light import LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .entity import ArgoEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_devices: Callable[[List[LightEntity]], None],
):
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_devices([ArgoDeviceLight(coordinator, entry)])


class ArgoDeviceLight(ArgoEntity, LightEntity):
    def __init__(self, coordinator, entry: ConfigEntry):
        ArgoEntity.__init__(self, "Device Light", coordinator, entry)
        LightEntity.__init__(self)

    @property
    def is_on(self) -> bool:
        if not self._type.device_lights:
            raise InvalidOperationError
        return self.coordinator.data.light

    @property
    def supported_features(self) -> int:
        if not self._type.device_lights:
            raise InvalidOperationError
        return 0

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
