from collections.abc import Callable

from custom_components.argoclima.device_type import InvalidOperationError
from custom_components.argoclima.entity import ArgoEntity
from custom_components.argoclima.runtime import ArgoRuntimeDevice
from custom_components.argoclima.runtime import runtime_devices_for_entry
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_devices: Callable[[list[SwitchEntity]], None],
):
    entities = []
    for device in runtime_devices_for_entry(hass, entry):
        if device.type.device_lights:
            entities.append(ArgoDeviceLightSwitch(device))
        if device.type.remote_temperature:
            entities.append(ArgoRemoteTemperatureSwitch(device))

    async_add_devices(entities)


class ArgoDeviceLightSwitch(ArgoEntity, SwitchEntity):
    def __init__(self, device: ArgoRuntimeDevice):
        ArgoEntity.__init__(
            self,
            "Device Light",
            device,
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
    def __init__(self, device: ArgoRuntimeDevice):
        ArgoEntity.__init__(
            self,
            "Use Remote Temperature",
            device,
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
