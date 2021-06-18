from homeassistant.config_entries import ConfigEntry
from custom_components.argoclima.data import (
    DATA_TEMP_MAX,
    DATA_TEMP_MIN,
    FanSpeed,
    OperationMode,
    ArgoData,
    Unit,
)
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    HVAC_MODE_AUTO,
    HVAC_MODE_COOL,
    HVAC_MODE_DRY,
    HVAC_MODE_FAN_ONLY,
    HVAC_MODE_OFF,
    PRESET_BOOST,
    PRESET_ECO,
    PRESET_NONE,
    PRESET_SLEEP,
    SUPPORT_FAN_MODE,
    SUPPORT_PRESET_MODE,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.const import TEMP_CELSIUS, TEMP_FAHRENHEIT

from .const import (
    DOMAIN,
)
from .entity import ArgoEntity


async def async_setup_entry(hass, entry, async_add_devices):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_devices([UlisseEntityClimate(coordinator, entry)])


class UlisseEntityClimate(ArgoEntity, ClimateEntity):
    def __init__(self, coordinator, entry: ConfigEntry):
        ArgoEntity.__init__(self, "climate", coordinator, entry)
        ClimateEntity.__init__(self)

    @property
    def temperature_unit(self):
        return (
            TEMP_CELSIUS
            if self.coordinator.data.unit == Unit.CELCIUS
            else TEMP_FAHRENHEIT
        )

    @property
    def current_temperature(self):
        return self.coordinator.data.temp

    @property
    def target_temperature(self):
        return self.coordinator.data.target_temp

    @property
    def max_temp(self):
        return DATA_TEMP_MAX

    @property
    def min_temp(self):
        return DATA_TEMP_MIN

    @property
    def hvac_mode(self):
        if not self.coordinator.data.operating:
            return HVAC_MODE_OFF
        map = {
            OperationMode.COOL: HVAC_MODE_COOL,
            OperationMode.DRY: HVAC_MODE_DRY,
            OperationMode.FAN: HVAC_MODE_FAN_ONLY,
            OperationMode.AUTO: HVAC_MODE_AUTO,
        }
        return map[self.coordinator.data.mode]

    @property
    def hvac_modes(self):
        return [
            HVAC_MODE_OFF,
            HVAC_MODE_COOL,
            HVAC_MODE_DRY,
            HVAC_MODE_FAN_ONLY,
            HVAC_MODE_AUTO,
        ]

    @property
    def preset_mode(self):
        if self.coordinator.data.eco:
            return PRESET_ECO
        if self.coordinator.data.turbo:
            return PRESET_BOOST
        if self.coordinator.data.night:
            return PRESET_SLEEP
        return PRESET_NONE

    @property
    def preset_modes(self):
        return [PRESET_ECO, PRESET_BOOST, PRESET_SLEEP]

    @property
    def fan_mode(self):
        map = {
            None: None,
            FanSpeed.AUTO: FAN_AUTO,
            FanSpeed.LOWEST: "lowest",
            FanSpeed.LOW: FAN_LOW,
            FanSpeed.MEDIUM: FAN_MEDIUM,
            FanSpeed.HIGH: FAN_HIGH,
            FanSpeed.HIGHER: "higher",
            FanSpeed.HIGHEST: "highest",
        }
        return map[self.coordinator.data.fan]

    @property
    def fan_modes(self):
        return [FAN_AUTO, "lowest", FAN_LOW, FAN_MEDIUM, FAN_HIGH, "higher", "highest"]

    @property
    def supported_features(self):
        return SUPPORT_TARGET_TEMPERATURE | SUPPORT_FAN_MODE | SUPPORT_PRESET_MODE

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        data = ArgoData()
        if hvac_mode is HVAC_MODE_OFF:
            data.operating = False
        else:
            data.operating = True
            map = {
                HVAC_MODE_COOL: OperationMode.COOL,
                HVAC_MODE_DRY: OperationMode.DRY,
                HVAC_MODE_FAN_ONLY: OperationMode.FAN,
                HVAC_MODE_AUTO: OperationMode.AUTO,
            }
            data.mode = map[hvac_mode]
        await self.coordinator.api.async_call_api(data)

    async def async_set_preset_mode(self, preset_mode):
        """Set new target preset mode."""
        data = ArgoData()
        # TODO looks like all modes can be active simultaneously
        data.eco = preset_mode is PRESET_ECO
        data.turbo = preset_mode is PRESET_BOOST
        data.night = preset_mode is PRESET_SLEEP
        await self.coordinator.api.async_call_api(data)

    async def async_set_fan_mode(self, fan_mode):
        """Set new target fan mode."""
        data = ArgoData()
        map = {
            FAN_AUTO: FanSpeed.AUTO,
            "lowest": FanSpeed.LOWEST,
            FAN_LOW: FanSpeed.LOW,
            FAN_MEDIUM: FanSpeed.MEDIUM,
            FAN_HIGH: FanSpeed.HIGH,
            "higher": FanSpeed.HIGHER,
            "highest": FanSpeed.HIGHEST,
        }
        data.fan = map[fan_mode]
        await self.coordinator.api.async_call_api(data)

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        if "temperature" in kwargs:
            data = ArgoData()
            data.target_temp = kwargs["temperature"]
            await self.coordinator.api.async_call_api(data)
