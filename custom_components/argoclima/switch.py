from typing import Any

from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import ArgoEntity
from .runtime import ArgoRuntimeDevice
from .runtime import runtime_devices_for_entry


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    entities = []
    for device in runtime_devices_for_entry(hass, entry):
        if device.type.device_lights:
            entities.append(ArgoDeviceLightSwitch(device))
        if device.type.remote_temperature:
            entities.append(ArgoRemoteTemperatureSwitch(device))
    async_add_entities(entities)


class ArgoDeviceLightSwitch(ArgoEntity, SwitchEntity):
    _attr_icon = "mdi:lightbulb"

    def __init__(self, device: ArgoRuntimeDevice) -> None:
        super().__init__(
            "Device Light", device, SwitchDeviceClass.SWITCH, EntityCategory.CONFIG
        )

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.light

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.coordinator.data.light = True
        await self._async_send_changes()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.coordinator.data.light = False
        await self._async_send_changes()


class ArgoRemoteTemperatureSwitch(ArgoEntity, SwitchEntity):
    _attr_icon = "mdi:remote"

    def __init__(self, device: ArgoRuntimeDevice) -> None:
        super().__init__(
            "Use Remote Temperature",
            device,
            SwitchDeviceClass.SWITCH,
            EntityCategory.CONFIG,
        )

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.remote_temperature

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.coordinator.data.remote_temperature = True
        await self._async_send_changes()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.coordinator.data.remote_temperature = False
        await self._async_send_changes()
