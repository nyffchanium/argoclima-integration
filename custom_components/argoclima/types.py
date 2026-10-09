from __future__ import annotations

from datetime import datetime
from enum import IntEnum
from enum import IntFlag

from homeassistant.components.climate.const import FAN_AUTO
from homeassistant.components.climate.const import FAN_HIGH
from homeassistant.components.climate.const import FAN_LOW
from homeassistant.components.climate.const import FAN_MEDIUM
from homeassistant.components.climate.const import HVACMode
from homeassistant.const import UnitOfTemperature

FAN_LOWEST = "lowest"
FAN_HIGHER = "higher"
FAN_HIGHEST = "highest"


class UnknownConversionError(Exception):
    """A value has no counterpart in the target representation."""


class ValueType(IntEnum):
    READ_ONLY = 0
    WRITE_ONLY = 1
    READ_WRITE = 2


def _convert(mapping: dict, value):
    try:
        return mapping[value]
    except KeyError as err:
        raise UnknownConversionError(value) from err


class ArgoUnit(IntEnum):
    CELSIUS = 0
    FAHRENHEIT = 1

    def to_ha_unit(self) -> str:
        return _convert(_UNIT_TO_HA, self)

    @staticmethod
    def from_ha_unit(unit: str) -> ArgoUnit:
        return _convert({v: k for k, v in _UNIT_TO_HA.items()}, unit)


_UNIT_TO_HA = {
    ArgoUnit.CELSIUS: UnitOfTemperature.CELSIUS,
    ArgoUnit.FAHRENHEIT: UnitOfTemperature.FAHRENHEIT,
}


class ArgoOperationMode(IntEnum):
    COOL = 1
    DRY = 2
    HEAT = 3
    FAN = 4
    AUTO = 5

    def to_hvac_mode(self) -> HVACMode:
        return _convert(_OPERATION_MODE_TO_HVAC, self)

    @staticmethod
    def from_hvac_mode(mode: str) -> ArgoOperationMode:
        return _convert({v: k for k, v in _OPERATION_MODE_TO_HVAC.items()}, mode)


_OPERATION_MODE_TO_HVAC = {
    ArgoOperationMode.COOL: HVACMode.COOL,
    ArgoOperationMode.DRY: HVACMode.DRY,
    ArgoOperationMode.HEAT: HVACMode.HEAT,
    ArgoOperationMode.FAN: HVACMode.FAN_ONLY,
    ArgoOperationMode.AUTO: HVACMode.AUTO,
}


class ArgoFanSpeed(IntEnum):
    AUTO = 0
    LOWEST = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    HIGHER = 5
    HIGHEST = 6

    def to_ha_string(self) -> str:
        return _convert(_FAN_SPEED_TO_HA, self)

    @staticmethod
    def from_ha_string(value: str) -> ArgoFanSpeed:
        return _convert({v: k for k, v in _FAN_SPEED_TO_HA.items()}, value)


_FAN_SPEED_TO_HA = {
    ArgoFanSpeed.AUTO: FAN_AUTO,
    ArgoFanSpeed.LOWEST: FAN_LOWEST,
    ArgoFanSpeed.LOW: FAN_LOW,
    ArgoFanSpeed.MEDIUM: FAN_MEDIUM,
    ArgoFanSpeed.HIGH: FAN_HIGH,
    ArgoFanSpeed.HIGHER: FAN_HIGHER,
    ArgoFanSpeed.HIGHEST: FAN_HIGHEST,
}


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
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6

    def __str__(self) -> str:
        return self.name.lower()

    @classmethod
    def from_datetime(cls, date: datetime) -> ArgoWeekday:
        return cls((date.weekday() + 1) % 7)


class ArgoTimerWeekday(IntFlag):
    SUNDAY = 1
    MONDAY = 2
    TUESDAY = 4
    WEDNESDAY = 8
    THURSDAY = 16
    FRIDAY = 32
    SATURDAY = 64

    def __str__(self) -> str:
        return self.name.lower()
