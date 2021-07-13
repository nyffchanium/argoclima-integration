from datetime import datetime
from enum import IntEnum
from enum import IntFlag

from homeassistant.components.climate.const import FAN_AUTO
from homeassistant.components.climate.const import FAN_HIGH
from homeassistant.components.climate.const import FAN_LOW
from homeassistant.components.climate.const import FAN_MEDIUM
from homeassistant.components.climate.const import HVAC_MODE_AUTO
from homeassistant.components.climate.const import HVAC_MODE_COOL
from homeassistant.components.climate.const import HVAC_MODE_DRY
from homeassistant.components.climate.const import HVAC_MODE_FAN_ONLY
from homeassistant.components.climate.const import HVAC_MODE_HEAT
from homeassistant.const import TEMP_CELSIUS
from homeassistant.const import TEMP_FAHRENHEIT

FAN_LOWEST = "lowest"
FAN_HIGHER = "higher"
FAN_HIGHEST = "highest"


class UnknownConversionError(Exception):
    """"Unknown type conversion"""


class ValueType(IntEnum):
    READ_ONLY = 0
    WRITE_ONLY = 1
    READ_WRITE = 2


class ArgoUnit(IntEnum):
    CELCIUS = 0
    FARENHEIT = 1

    def to_ha_unit(self) -> str:
        if self.value == ArgoUnit.CELCIUS:
            return TEMP_CELSIUS
        if self.value == ArgoUnit.FARENHEIT:
            return TEMP_FAHRENHEIT
        raise UnknownConversionError

    @staticmethod
    def from_ha_unit(mode: str) -> "ArgoOperationMode":
        if mode == TEMP_CELSIUS:
            return ArgoUnit.CELCIUS
        if mode == TEMP_FAHRENHEIT:
            return ArgoUnit.FARENHEIT
        raise UnknownConversionError


class ArgoOperationMode(IntEnum):
    COOL = 1
    DRY = 2
    HEAT = 3
    FAN = 4
    AUTO = 5

    def to_hvac_mode(self) -> str:
        if self.value == ArgoOperationMode.COOL:
            return HVAC_MODE_COOL
        if self.value == ArgoOperationMode.DRY:
            return HVAC_MODE_DRY
        if self.value == ArgoOperationMode.HEAT:
            return HVAC_MODE_HEAT
        if self.value == ArgoOperationMode.FAN:
            return HVAC_MODE_FAN_ONLY
        if self.value == ArgoOperationMode.AUTO:
            return HVAC_MODE_AUTO
        raise UnknownConversionError

    @staticmethod
    def from_hvac_mode(mode: str) -> "ArgoOperationMode":
        if mode == HVAC_MODE_COOL:
            return ArgoOperationMode.COOL
        if mode == HVAC_MODE_DRY:
            return ArgoOperationMode.DRY
        if mode == HVAC_MODE_HEAT:
            return ArgoOperationMode.HEAT
        if mode == HVAC_MODE_FAN_ONLY:
            return ArgoOperationMode.FAN
        if mode == HVAC_MODE_AUTO:
            return ArgoOperationMode.AUTO
        raise UnknownConversionError


class ArgoFanSpeed(IntEnum):
    AUTO = 0
    LOWEST = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    HIGHER = 5
    HIGHEST = 6

    def to_ha_string(self) -> str:
        if self.value == ArgoFanSpeed.AUTO:
            return FAN_AUTO
        if self.value == ArgoFanSpeed.LOWEST:
            return FAN_LOWEST
        if self.value == ArgoFanSpeed.LOW:
            return FAN_LOW
        if self.value == ArgoFanSpeed.MEDIUM:
            return FAN_MEDIUM
        if self.value == ArgoFanSpeed.HIGH:
            return FAN_HIGH
        if self.value == ArgoFanSpeed.HIGHER:
            return FAN_HIGHER
        if self.value == ArgoFanSpeed.HIGHEST:
            return FAN_HIGHEST
        raise UnknownConversionError

    @staticmethod
    def from_ha_string(string: str) -> "ArgoOperationMode":
        if string == FAN_AUTO:
            return ArgoFanSpeed.AUTO
        if string == FAN_LOWEST:
            return ArgoFanSpeed.LOWEST
        if string == FAN_LOW:
            return ArgoFanSpeed.LOW
        if string == FAN_MEDIUM:
            return ArgoFanSpeed.MEDIUM
        if string == FAN_HIGH:
            return ArgoFanSpeed.HIGH
        if string == FAN_HIGHER:
            return ArgoFanSpeed.HIGHER
        if string == FAN_HIGHEST:
            return ArgoFanSpeed.HIGHEST
        raise UnknownConversionError


class ArgoFlapMode(IntEnum):
    pass


class ArgoTimerType(IntEnum):
    NO_TIMER = 0
    DELAY_ON_OFF = 1
    PROFILE_1 = 2
    PROFILE_2 = 3
    PROFILE_3 = 4

    def __str__(self) -> str:
        return self.name.lower()


class ArgoWeekday(IntEnum):
    SUNDAY = 0
    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSAY = 4
    FRIDAY = 5
    SATURDAY = 6

    def __str__(self) -> str:
        return self.name.lower()

    @classmethod
    def from_datetime(cls, date: datetime) -> "ArgoWeekday":
        val = date.weekday() + 1
        if val == 7:
            val = 0
        return cls(val)


class ArgoTimerWeekday(IntFlag):
    SUNDAY = 1
    MONDAY = 2
    TUESDAY = 4
    WEDNESDAY = 8
    THURSAY = 16
    FRIDAY = 32
    SATURDAY = 64

    def __str__(self) -> str:
        return self.name.lower()
