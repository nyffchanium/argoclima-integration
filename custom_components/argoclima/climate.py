from typing import Callable
from typing import List

from custom_components.argoclima.const import DOMAIN
from custom_components.argoclima.data import ArgoFanSpeed
from custom_components.argoclima.data import ArgoOperationMode
from custom_components.argoclima.device_type import InvalidOperationError
from custom_components.argoclima.entity import ArgoEntity
from custom_components.argoclima.types import ArgoUnit
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import ClimateEntityFeature
from homeassistant.components.climate.const import HVACMode
from homeassistant.components.climate.const import PRESET_BOOST
from homeassistant.components.climate.const import PRESET_ECO
from homeassistant.components.climate.const import PRESET_NONE
from homeassistant.components.climate.const import PRESET_SLEEP
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_devices: Callable[[List[ClimateEntity]], None],
):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_devices([ArgoEntityClimate(coordinator, entry)])


class ArgoEntityClimate(ArgoEntity, ClimateEntity):
    def __init__(self, coordinator, entry: ConfigEntry):
        ArgoEntity.__init__(self, "Climate", coordinator, entry)
        ClimateEntity.__init__(self)

    @property
    def temperature_unit(self):
        if not self._type.current_temperature:
            raise InvalidOperationError
        return ArgoUnit.CELSIUS.to_ha_unit()

    @property
    def current_temperature(self):
        if not self._type.current_temperature:
            raise InvalidOperationError
        return self.coordinator.data.temp

    @property
    def target_temperature(self):
        if not self._type.target_temperature:
            raise InvalidOperationError
        return self.coordinator.data.target_temp

    @property
    def max_temp(self):
        if not self._type.target_temperature:
            raise InvalidOperationError
        return self._type.target_temperature_max

    @property
    def min_temp(self):
        if not self._type.target_temperature:
            raise InvalidOperationError
        return self._type.target_temperature_min

    @property
    def hvac_mode(self):
        if not self._type.operation_mode:
            raise InvalidOperationError
        if not self.coordinator.data.operating:
            return HVACMode.OFF
        return self.coordinator.data.mode.to_hvac_mode()

    @property
    def hvac_modes(self):
        if not self._type.operation_mode:
            raise InvalidOperationError
        modes = [HVACMode.OFF]
        for mode in self._type.operation_modes:
            modes.append(mode.to_hvac_mode())
        return modes

    @property
    def preset_mode(self):
        if not self._type.preset:
            raise InvalidOperationError
        if self.coordinator.data.eco:
            return PRESET_ECO
        if self.coordinator.data.turbo:
            return PRESET_BOOST
        if self.coordinator.data.night:
            return PRESET_SLEEP
        return PRESET_NONE

    @property
    def preset_modes(self):
        if not self._type.preset:
            raise InvalidOperationError
        modes = [PRESET_NONE]
        if self._type.eco_mode:
            modes.append(PRESET_ECO)
        if self._type.turbo_mode:
            modes.append(PRESET_BOOST)
        if self._type.night_mode:
            modes.append(PRESET_SLEEP)
        return modes

    @property
    def fan_mode(self):
        if not self._type.fan_speed:
            raise InvalidOperationError
        return self.coordinator.data.fan.to_ha_string()

    @property
    def fan_modes(self):
        if not self._type.fan_speed:
            raise InvalidOperationError
        modes = []
        for speed in self._type.fan_speeds:
            modes.append(speed.to_ha_string())
        return modes

    @property
    def supported_features(self):
        features = 0
        if self._type.target_temperature:
            features |= ClimateEntityFeature.TARGET_TEMPERATURE
        if self._type.fan_speed:
            features |= ClimateEntityFeature.FAN_MODE
        if self._type.preset:
            features |= ClimateEntityFeature.PRESET_MODE
        return features

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        if not self._type.operation_mode:
            raise InvalidOperationError
        data = self.coordinator.data
        if hvac_mode == HVACMode.OFF:
            data.operating = False
        else:
            data.operating = True
            data.mode = ArgoOperationMode.from_hvac_mode(hvac_mode)
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode):
        """Set new target preset mode."""
        if not self._type.preset:
            raise InvalidOperationError
        data = self.coordinator.data
        # TODO looks like all modes can be active simultaneously
        data.eco = preset_mode == PRESET_ECO
        data.turbo = preset_mode == PRESET_BOOST
        data.night = preset_mode == PRESET_SLEEP
        await self.coordinator.async_request_refresh()

    async def async_set_fan_mode(self, fan_mode):
        """Set new target fan mode."""
        if not self._type.fan_speed:
            raise InvalidOperationError
        self.coordinator.data.fan = ArgoFanSpeed.from_ha_string(fan_mode)
        await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        if not self._type.target_temperature:
            raise InvalidOperationError
        if "temperature" in kwargs:
            self.coordinator.data.target_temp = kwargs["temperature"]
            await self.coordinator.async_request_refresh()
