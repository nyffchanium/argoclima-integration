from __future__ import annotations

from .const import API_UPDATE_ATTEMPTS
from .device_type import ArgoDeviceType
from .types import ArgoFanSpeed
from .types import ArgoOperationMode
from .types import ArgoTimerType
from .types import ArgoTimerWeekday
from .types import ArgoUnit
from .types import ArgoWeekday
from .types import ValueType

RESPONSE_VALUE_COUNT = 39
UPDATE_VALUE_COUNT = 36


def _optional(enum, value):
    return enum(value) if value is not None else None


class InvalidResponseFormatError(Exception):
    """The response does not have a known Argoclima format."""


class ArgoDataValue:
    def __init__(
        self,
        update_index: int,
        response_index: int,
        type: ValueType = ValueType.READ_WRITE,
    ) -> None:
        self._type = type
        self._update_index = update_index
        self._response_index = response_index
        self._value: int = None
        self._pending_change = False
        self._requested_value: int = None
        self._change_try_counter_enabled = False
        self._change_try_count = 0

    @property
    def update_index(self) -> int:
        return self._update_index

    @property
    def response_index(self) -> int:
        return self._response_index

    @property
    def pending_change(self) -> bool:
        return self._pending_change

    @property
    def value(self) -> int:
        """Return the requested value while a change is pending, else the current one."""
        if self._type == ValueType.WRITE_ONLY:
            raise ValueError("Write-only value can't be read")
        return self._requested_value if self._pending_change else self._value

    def request_value(self, value: int) -> None:
        if self._type == ValueType.READ_ONLY:
            raise ValueError("Read-only value can't be written")
        current = self._requested_value if self._pending_change else self._value
        if value == current:
            return
        self._requested_value = value
        self._pending_change = True
        self._change_try_counter_enabled = False

    def requested_value_as_string(self) -> str:
        return str(int(self._requested_value))

    def update(self, value: str) -> None:
        self._value = int(value)
        if self._pending_change and self._requested_value == self._value:
            self._pending_change = False
            self._change_try_counter_enabled = False

    def enable_change_watcher(self) -> None:
        """Start counting failed update attempts if not started already."""
        if not self._change_try_counter_enabled:
            self._change_try_count = 0
            self._change_try_counter_enabled = True

    def assume_change_successful(self) -> None:
        if self._change_try_counter_enabled:
            self._pending_change = False
            self._change_try_counter_enabled = False

    def notify_unsuccessful_change(self) -> None:
        if self._change_try_counter_enabled:
            self._change_try_count += 1
            if self._change_try_count == API_UPDATE_ATTEMPTS:
                self._pending_change = False
                self._change_try_counter_enabled = False


class ArgoRangedDataValue(ArgoDataValue):
    def __init__(
        self,
        update_index: int,
        response_index: int,
        min: int,
        max: int,
        type: ValueType = ValueType.READ_WRITE,
    ) -> None:
        super().__init__(update_index, response_index, type)
        self._min = min
        self._max = max

    def request_value(self, value: int) -> None:
        if not self._min <= value <= self._max:
            raise ValueError(f"Value {value} outside of [{self._min}, {self._max}]")
        return super().request_value(value)


class ArgoConstrainedDataValue(ArgoDataValue):
    def __init__(
        self,
        update_index: int,
        response_index: int,
        allowed_values: list[int],
        type: ValueType = ValueType.READ_WRITE,
    ) -> None:
        super().__init__(update_index, response_index, type)
        self._allowed_values = allowed_values

    def request_value(self, value: int) -> None:
        if value not in self._allowed_values:
            raise ValueError(f"Value {value} not allowed")
        return super().request_value(value)


class ArgoBooleanDataValue(ArgoDataValue):
    def __init__(
        self,
        update_index: int,
        response_index: int,
        type: ValueType = ValueType.READ_WRITE,
    ) -> None:
        super().__init__(update_index, response_index, type=type)

    @property
    def value(self) -> bool:
        return super().value == 1

    def request_value(self, value: int) -> None:
        return super().request_value(1 if value else 0)


class ArgoData:
    def __init__(self, type: ArgoDeviceType) -> None:
        self._type = type
        self._target_temp = ArgoRangedDataValue(
            0, 0, type.target_temperature_min * 10, type.target_temperature_max * 10
        )
        self._temp = ArgoDataValue(None, 1, ValueType.READ_ONLY)
        self._operating = ArgoBooleanDataValue(2, 2)
        self._mode = ArgoConstrainedDataValue(3, 3, list(map(int, ArgoOperationMode)))
        self._fan = ArgoConstrainedDataValue(4, 4, list(map(int, ArgoFanSpeed)))
        self._remote_temperature = ArgoBooleanDataValue(6, 6)
        self._eco = ArgoBooleanDataValue(8, 8)
        self._turbo = ArgoBooleanDataValue(9, 9)
        self._night = ArgoBooleanDataValue(10, 10)
        self._light = ArgoBooleanDataValue(11, 11)
        self._timer = ArgoConstrainedDataValue(12, 12, list(map(int, ArgoTimerType)))
        self._current_weekday = ArgoConstrainedDataValue(
            18, None, list(map(int, ArgoWeekday)), ValueType.WRITE_ONLY
        )
        self._timer_weekdays = ArgoConstrainedDataValue(
            19, None, list(map(int, ArgoTimerWeekday)), ValueType.WRITE_ONLY
        )
        self._time = ArgoRangedDataValue(20, None, 0, 1439, ValueType.WRITE_ONLY)
        self._delaytimer_duration = ArgoRangedDataValue(
            21, None, 0, 1439, ValueType.WRITE_ONLY
        )
        self._timer_on = ArgoRangedDataValue(22, None, 0, 1439, ValueType.WRITE_ONLY)
        self._timer_off = ArgoRangedDataValue(23, None, 0, 1439, ValueType.WRITE_ONLY)
        self._eco_limit = ArgoRangedDataValue(
            25, 22, type.eco_limit_min, type.eco_limit_max
        )
        self._unit = ArgoDataValue(26, 24)
        self._firmware_version = ArgoDataValue(None, 23, ValueType.READ_ONLY)
        self.wifi_firmware_version: str | None = None
        self._values: list[ArgoDataValue] = [
            self._target_temp,
            self._temp,
            self._operating,
            self._mode,
            self._fan,
            self._remote_temperature,
            self._eco,
            self._turbo,
            self._night,
            self._light,
            self._timer,
            self._current_weekday,
            self._timer_weekdays,
            self._time,
            self._delaytimer_duration,
            self._timer_on,
            self._timer_off,
            self._eco_limit,
            self._unit,
            self._firmware_version,
        ]

    def to_parameter_string(self) -> str:
        values = []
        for i in range(UPDATE_VALUE_COUNT):
            out = "N"
            for val in self._values:
                if val.update_index == i and val.pending_change:
                    out = val.requested_value_as_string()
                    val.enable_change_watcher()
                    break
            values.append(str(out))
        return ",".join(values)

    def parse_response_parameter_string(
        self, query: str, *, is_response: bool = True
    ) -> None:
        """Apply a device state string.

        Only answers to our own requests count as attempts to apply pending
        changes; state the device reports on its own (is_response=False) just
        confirms them when they match.
        """
        values = query.split(",")

        if len(values) != RESPONSE_VALUE_COUNT:
            raise InvalidResponseFormatError()

        for val in self._values:
            if val.response_index is not None:
                value = values[val.response_index]

                if value == "N":
                    continue

                if not value.isdecimal():
                    raise InvalidResponseFormatError()

                val.update(value)

                if val.pending_change and is_response:
                    val.notify_unsuccessful_change()

            elif val.pending_change and is_response:
                val.assume_change_successful()

    def is_update_pending(self) -> bool:
        return any(val.pending_change for val in self._values)

    @property
    def target_temp(self) -> float:
        return (
            self._target_temp.value / 10
            if self._target_temp.value is not None
            else None
        )

    @target_temp.setter
    def target_temp(self, value: int):
        self._target_temp.request_value(int(value * 10))

    @property
    def temp(self) -> float:
        return self._temp.value / 10 if self._temp.value is not None else None

    @property
    def operating(self) -> bool:
        return self._operating.value

    @operating.setter
    def operating(self, value: bool):
        self._operating.request_value(value)

    @property
    def mode(self) -> ArgoOperationMode | None:
        return _optional(ArgoOperationMode, self._mode.value)

    @mode.setter
    def mode(self, value: ArgoOperationMode):
        self._mode.request_value(value)

    @property
    def fan(self) -> ArgoFanSpeed | None:
        return _optional(ArgoFanSpeed, self._fan.value)

    @fan.setter
    def fan(self, value: ArgoFanSpeed):
        self._fan.request_value(value)

    @property
    def remote_temperature(self) -> bool:
        return self._remote_temperature.value

    @remote_temperature.setter
    def remote_temperature(self, value: bool):
        self._remote_temperature.request_value(value)

    @property
    def eco(self) -> bool:
        return self._eco.value

    @eco.setter
    def eco(self, value: bool):
        self._eco.request_value(value)

    @property
    def turbo(self) -> bool:
        return self._turbo.value

    @turbo.setter
    def turbo(self, value: bool):
        self._turbo.request_value(value)

    @property
    def night(self) -> bool:
        return self._night.value

    @night.setter
    def night(self, value: bool):
        self._night.request_value(value)

    @property
    def light(self) -> bool:
        return self._light.value

    @light.setter
    def light(self, value: bool):
        self._light.request_value(value)

    @property
    def timer(self) -> ArgoTimerType | None:
        return _optional(ArgoTimerType, self._timer.value)

    @timer.setter
    def timer(self, value: ArgoTimerType):
        self._timer.request_value(value)

    def set_current_weekday(self, value: ArgoWeekday):
        self._current_weekday.request_value(value)

    def set_timer_weekdays(self, value: ArgoTimerWeekday):
        self._timer_weekdays.request_value(value)

    def set_time(self, hours: int, minutes: int):
        self._time.request_value(hours * 60 + minutes)

    def set_delaytimer_duration(self, hours: int, minutes: int):
        self._delaytimer_duration.request_value(hours * 60 + minutes)

    def set_timer_on(self, hours: int, minutes: int):
        self._timer_on.request_value(hours * 60 + minutes)

    def set_timer_off(self, hours: int, minutes: int):
        self._timer_off.request_value(hours * 60 + minutes)

    @property
    def eco_limit(self) -> int:
        return self._eco_limit.value

    @eco_limit.setter
    def eco_limit(self, value: int):
        self._eco_limit.request_value(value)

    @property
    def unit(self) -> ArgoUnit | None:
        return _optional(ArgoUnit, self._unit.value)

    @unit.setter
    def unit(self, value: ArgoUnit):
        self._unit.request_value(value)

    @property
    def firmware_version(self) -> int:
        return self._firmware_version.value
