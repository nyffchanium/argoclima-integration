from typing import Any

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate import ClimateEntityFeature
from homeassistant.components.climate import HVACMode
from homeassistant.components.climate.const import PRESET_BOOST
from homeassistant.components.climate.const import PRESET_ECO
from homeassistant.components.climate.const import PRESET_NONE
from homeassistant.components.climate.const import PRESET_SLEEP
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import ArgoEntity
from .runtime import ArgoRuntimeDevice
from .runtime import runtime_devices_for_entry
from .types import ArgoFanSpeed
from .types import ArgoOperationMode
from .types import ArgoUnit


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities(
        ArgoClimate(device)
        for device in runtime_devices_for_entry(hass, entry)
        if device.type.on_off
    )


class ArgoClimate(ArgoEntity, ClimateEntity):
    _attr_temperature_unit = ArgoUnit.CELSIUS.to_ha_unit()

    def __init__(self, device: ArgoRuntimeDevice) -> None:
        super().__init__("Climate", device)
        self._attr_name = None
        device_type = device.type

        features = ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF
        if device_type.target_temperature:
            features |= ClimateEntityFeature.TARGET_TEMPERATURE
            self._attr_min_temp = device_type.target_temperature_min
            self._attr_max_temp = device_type.target_temperature_max
        if device_type.fan_speed:
            features |= ClimateEntityFeature.FAN_MODE
            self._attr_fan_modes = [
                speed.to_ha_string() for speed in device_type.fan_speeds
            ]
        if device_type.preset:
            features |= ClimateEntityFeature.PRESET_MODE
            self._attr_preset_modes = [PRESET_NONE]
            if device_type.eco_mode:
                self._attr_preset_modes.append(PRESET_ECO)
            if device_type.turbo_mode:
                self._attr_preset_modes.append(PRESET_BOOST)
            if device_type.night_mode:
                self._attr_preset_modes.append(PRESET_SLEEP)
        self._attr_supported_features = features
        self._attr_hvac_modes = [HVACMode.OFF] + [
            mode.to_hvac_mode() for mode in device_type.operation_modes
        ]

    @property
    def current_temperature(self) -> float | None:
        if not self._type.current_temperature:
            return None
        return self.coordinator.data.temp

    @property
    def target_temperature(self) -> float | None:
        if not self._type.target_temperature:
            return None
        return self.coordinator.data.target_temp

    @property
    def hvac_mode(self) -> HVACMode | None:
        data = self.coordinator.data
        if not data.operating:
            return HVACMode.OFF
        return data.mode.to_hvac_mode() if data.mode is not None else None

    @property
    def preset_mode(self) -> str | None:
        if not self._type.preset:
            return None
        data = self.coordinator.data
        if data.eco:
            return PRESET_ECO
        if data.turbo:
            return PRESET_BOOST
        if data.night:
            return PRESET_SLEEP
        return PRESET_NONE

    @property
    def fan_mode(self) -> str | None:
        fan = self.coordinator.data.fan
        if not self._type.fan_speed or fan is None:
            return None
        return fan.to_ha_string()

    async def async_turn_on(self) -> None:
        self.coordinator.data.operating = True
        await self._async_send_changes()

    async def async_turn_off(self) -> None:
        self.coordinator.data.operating = False
        await self._async_send_changes()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        data = self.coordinator.data
        if hvac_mode == HVACMode.OFF:
            data.operating = False
        else:
            data.operating = True
            data.mode = ArgoOperationMode.from_hvac_mode(hvac_mode)
        await self._async_send_changes()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        data = self.coordinator.data
        data.eco = preset_mode == PRESET_ECO
        data.turbo = preset_mode == PRESET_BOOST
        data.night = preset_mode == PRESET_SLEEP
        await self._async_send_changes()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        self.coordinator.data.fan = ArgoFanSpeed.from_ha_string(fan_mode)
        await self._async_send_changes()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is not None:
            self.coordinator.data.target_temp = temperature
            await self._async_send_changes()
