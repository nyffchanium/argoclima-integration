from typing import Callable
from typing import List

from custom_components.argoclima.const import CONF_DEVICE_TYPE
from custom_components.argoclima.const import DOMAIN
from custom_components.argoclima.device_type import ArgoDeviceType
from custom_components.argoclima.device_type import InvalidOperationError
from custom_components.argoclima.entity import ArgoEntity
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_devices: Callable[[List[SwitchEntity]], None],
):
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    type = ArgoDeviceType.from_name(entry.data[CONF_DEVICE_TYPE])

    if type.device_lights:
        entities.append(ArgoDeviceLightSwitch(coordinator, entry))
    if type.remote_temperature:
        entities.append(ArgoRemoteTemperatureSwitch(coordinator, entry))

    async_add_devices(entities)


class ArgoDeviceLightSwitch(ArgoEntity, SwitchEntity):
    def __init__(self, coordinator, entry: ConfigEntry):
        ArgoEntity.__init__(
            self,
            "Device Light",
            coordinator,
            entry,
            SwitchDeviceClass.SWITCH,
            EntityCategory.CONFIG,
        )
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


class ArgoRemoteTemperatureSwitch(ArgoEntity, SwitchEntity):
    def __init__(self, coordinator, entry: ConfigEntry):
        ArgoEntity.__init__(
            self,
            "Use Remote Temperature",
            coordinator,
            entry,
            SwitchDeviceClass.SWITCH,
            EntityCategory.CONFIG,
        )
        SwitchEntity.__init__(self)

    @property
    def icon(self) -> str:
        return "mdi:remote"

    @property
    def is_on(self) -> bool:
        if not self._type.remote_temperature:
            raise InvalidOperationError
        return self.coordinator.data.remote_temperature

    async def async_turn_on(self, **kwargs) -> None:
        if not self._type.remote_temperature:
            raise InvalidOperationError
        self.coordinator.data.remote_temperature = True
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        if not self._type.remote_temperature:
            raise InvalidOperationError
        self.coordinator.data.remote_temperature = False
        await self.coordinator.async_request_refresh()
