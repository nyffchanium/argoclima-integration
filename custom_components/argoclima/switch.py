from typing import Any

from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .anti_mold import DRYING_MODES
from .entity import ArgoAntiMoldEntity
from .entity import ArgoEntity
from .runtime import ArgoRuntimeDevice
from .runtime import runtime_devices_for_entry
from .types import ArgoOperationMode

ANTI_MOLD_MODE_NAMES = {
    ArgoOperationMode.COOL: "Anti Mold After Cooling",
    ArgoOperationMode.DRY: "Anti Mold After Dehumidifying",
    ArgoOperationMode.AUTO: "Anti Mold After Auto",
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    entities = []
    for device in runtime_devices_for_entry(hass, entry):
        if device.type.device_lights:
            entities.append(ArgoDeviceLightSwitch(device))
        if device.type.remote_temperature:
            entities.append(ArgoRemoteTemperatureSwitch(device))
        if device.type.anti_mold:
            entities.append(ArgoAntiMoldSwitch(device))
            entities.append(ArgoAntiMoldAfterRemoteOffSwitch(device))
            entities.extend(
                ArgoAntiMoldModeSwitch(device, mode)
                for mode in DRYING_MODES
                if mode in device.type.operation_modes
            )
    async_add_entities(entities)


class ArgoDeviceLightSwitch(ArgoEntity, SwitchEntity):
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


class ArgoAntiMoldSwitch(ArgoAntiMoldEntity, SwitchEntity, RestoreEntity):
    def __init__(self, device: ArgoRuntimeDevice) -> None:
        super().__init__("Anti Mold", device)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (state := await self.async_get_last_state()) is not None:
            self._anti_mold.enabled = state.state == "on"

    @property
    def is_on(self) -> bool:
        return self._anti_mold.enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        self._anti_mold.enabled = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._anti_mold.enabled = False
        self._anti_mold.async_cancel()
        self.async_write_ha_state()


class ArgoAntiMoldAfterRemoteOffSwitch(ArgoAntiMoldEntity, SwitchEntity, RestoreEntity):
    def __init__(self, device: ArgoRuntimeDevice) -> None:
        super().__init__("Anti Mold After Remote Off", device)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (state := await self.async_get_last_state()) is not None:
            self._anti_mold.after_remote_off = state.state == "on"

    @property
    def is_on(self) -> bool:
        return self._anti_mold.after_remote_off

    async def async_turn_on(self, **kwargs: Any) -> None:
        self._anti_mold.after_remote_off = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._anti_mold.after_remote_off = False
        self.async_write_ha_state()


class ArgoAntiMoldModeSwitch(ArgoAntiMoldEntity, SwitchEntity, RestoreEntity):
    """Whether to dry after the device ran in a mode."""

    def __init__(self, device: ArgoRuntimeDevice, mode: ArgoOperationMode) -> None:
        super().__init__(ANTI_MOLD_MODE_NAMES[mode], device)
        self._mode = mode

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (state := await self.async_get_last_state()) is not None:
            self._set(state.state == "on")

    @property
    def is_on(self) -> bool:
        return self._mode in self._anti_mold.modes

    async def async_turn_on(self, **kwargs: Any) -> None:
        self._set(True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._set(False)
        self.async_write_ha_state()

    def _set(self, on: bool) -> None:
        if on:
            self._anti_mold.modes.add(self._mode)
        else:
            self._anti_mold.modes.discard(self._mode)
