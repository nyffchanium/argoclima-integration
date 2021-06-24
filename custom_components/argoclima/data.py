from enum import IntEnum
from enum import IntFlag
from typing import List

DATA_TEMP_MIN = 10
DATA_TEMP_MAX = 32


class ValueType(IntEnum):
    READ_ONLY = 0
    WRITE_ONLY = 1
    READ_WRITE = 2


class OperationMode(IntEnum):
    COOL = 1
    DRY = 2
    # HEAT = 3
    FAN = 4
    AUTO = 5


class FanSpeed(IntEnum):
    AUTO = 0
    LOWEST = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    HIGHER = 5
    HIGHEST = 6


class TimerType(IntEnum):
    NO_TIMER = 0
    DELAY_ON_OFF = 1
    PROFILE_1 = 2
    PROFILE_2 = 3
    PROFILE_3 = 4


class Weekday(IntEnum):
    SUNDAY = 0
    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSAY = 4
    FRIDAY = 5
    SATURDAY = 6


class TimerWeekday(IntFlag):
    SUNDAY = 1
    MONDAY = 2
    TUESDAY = 4
    WEDNESDAY = 8
    THURSAY = 16
    FRIDAY = 32
    SATURDAY = 64


class Unit(IntEnum):
    CELCIUS = 0
    FARENHEIT = 1


class DataValue:
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
        self._changed = False

    @property
    def update_index(self) -> int:
        return self._update_index

    @property
    def response_index(self) -> int:
        return self._response_index

    @property
    def changed(self) -> bool:
        return self._changed

    @property
    def value(self) -> int:
        if self._type == ValueType.WRITE_ONLY:
            raise "can't get writeonly value"
        return self._value

    @value.setter
    def value(self, value: int):
        if self._type == ValueType.READ_ONLY:
            raise "can't set readonly value"
        if self._value != value:
            self._changed = True
            self._value = value

    def reset_changed_flag(self):
        self._changed = False

    def as_string(self) -> str:
        return str(int(self._value))

    def update(self, value: str) -> None:
        self._value = int(value)


class RangedDataValue(DataValue):
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

    @DataValue.value.setter
    def value(self, value: int):
        if value < self._min:
            raise f"value can't be less than {self._min}"
        elif value > self._max:
            raise f"value can't be greater than {self._max}"
        super(RangedDataValue, type(self)).value.fset(self, value)


class ConstrainedDataValue(DataValue):
    def __init__(
        self,
        update_index: int,
        response_index: int,
        allowed_values: List[int],
        type: ValueType = ValueType.READ_WRITE,
    ) -> None:
        super().__init__(update_index, response_index, type)
        self._allowed_values = allowed_values

    @DataValue.value.setter
    def value(self, value: int):
        if value not in self._allowed_values:
            raise "value not allowed"
        super(ConstrainedDataValue, type(self)).value.fset(self, value)


class BooleanDataValue(DataValue):
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

    @value.setter
    def value(self, value: bool):
        super(BooleanDataValue, type(self)).value.fset(self, 1 if value else 0)


class ArgoData:
    def __init__(self) -> None:
        self._target_temp = RangedDataValue(
            0, 0, DATA_TEMP_MIN * 10, DATA_TEMP_MAX * 10
        )
        self._temp = DataValue(None, 1, ValueType.READ_ONLY)
        self._operating = BooleanDataValue(2, 2)
        self._mode = ConstrainedDataValue(3, 3, list(map(int, OperationMode)))
        self._fan = ConstrainedDataValue(4, 4, list(map(int, FanSpeed)))
        # self._flap = RangedDataValue(5, 5, 0, 7)
        self._target_remote = BooleanDataValue(6, 6)
        # self._filter = BooleanDataValue(8, 8)
        self._eco = BooleanDataValue(8, 8)
        self._turbo = BooleanDataValue(9, 9)
        self._night = BooleanDataValue(10, 10)
        self._light = BooleanDataValue(11, 11)
        self._timer = ConstrainedDataValue(12, 12, list(map(int, TimerType)))
        self._current_weekday = ConstrainedDataValue(
            18, None, list(map(int, Weekday)), ValueType.WRITE_ONLY
        )
        self._timer_weekdays = ConstrainedDataValue(
            19, None, list(map(int, TimerWeekday)), ValueType.WRITE_ONLY
        )
        self._time = RangedDataValue(20, None, 0, 1439, ValueType.WRITE_ONLY)
        self._delaytimer_duration = RangedDataValue(
            21, None, 0, 1439, ValueType.WRITE_ONLY
        )
        self._timer_on = RangedDataValue(22, None, 0, 1439, ValueType.WRITE_ONLY)
        self._timer_off = RangedDataValue(23, None, 0, 1439, ValueType.WRITE_ONLY)
        # self._reset = RangedDataValue(24, None, 0, 3, ValueType.WRITE_ONLY)
        self._eco_limit = RangedDataValue(25, 22, 30, 99)
        self._unit = DataValue(26, 24)
        self._firmware_version = DataValue(None, 23, ValueType.READ_ONLY)
        self._values: List[DataValue] = [
            self._target_temp,
            self._temp,
            self._operating,
            self._mode,
            self._fan,
            self._target_remote,
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

    def to_update_query(self) -> str:
        values = []
        for i in range(36):
            out = "N"
            for val in self._values:
                if val.update_index == i and val.changed:
                    out = val.as_string()
                    val.reset_changed_flag()
                    break
            values.append(str(out))
        return ",".join(values)

    @classmethod
    def parse_response_query(cls, query: str):
        instance = cls()
        values = query.split(",")

        if len(values) != 39:
            raise InvalidResponseFormatError

        for val in instance._values:
            if val.response_index is not None:
                value = values[val.response_index]

                if value == "N":
                    continue

                if not value.isdecimal():
                    raise InvalidResponseFormatError

                val.update(value)
                val.reset_changed_flag()

        return instance

    @property
    def target_temp(self) -> float:
        return (
            self._target_temp.value / 10
            if self._target_temp.value is not None
            else None
        )

    @target_temp.setter
    def target_temp(self, value: int):
        self._target_temp.value = (int)(value * 10)

    @property
    def temp(self) -> float:
        return self._temp.value / 10 if self._temp.value is not None else None

    @property
    def operating(self) -> bool:
        return self._operating.value

    @operating.setter
    def operating(self, value: bool):
        self._operating.value = value

    @property
    def mode(self) -> OperationMode:
        return self._mode.value

    @mode.setter
    def mode(self, value: OperationMode):
        self._mode.value = value

    @property
    def fan(self) -> FanSpeed:
        return self._fan.value

    @fan.setter
    def fan(self, value: FanSpeed):
        self._fan.value = value

    @property
    def target_remote(self) -> bool:
        return self._target_remote.value

    @target_remote.setter
    def target_remote(self, value: bool):
        self._target_remote.value = value

    @property
    def eco(self) -> bool:
        return self._eco.value

    @eco.setter
    def eco(self, value: bool):
        self._eco.value = value

    @property
    def turbo(self) -> bool:
        return self._turbo.value

    @turbo.setter
    def turbo(self, value: bool):
        self._turbo.value = value

    @property
    def night(self) -> bool:
        return self._night.value

    @night.setter
    def night(self, value: bool):
        self._night.value = value

    @property
    def light(self) -> bool:
        return self._light.value

    @light.setter
    def light(self, value: bool):
        self._light.value = value

    @property
    def timer(self) -> TimerType:
        return self._timer.value

    @timer.setter
    def timer(self, value: TimerType):
        self._timer.value = value

    def set_current_weekday(self, value: Weekday):
        self._current_weekday.value = value

    def set_timer_weekdays(self, value: TimerWeekday):
        self._timer_weekdays.value = value

    def set_time(self, hours: int, minutes: int):
        self._time.value = hours * 60 + minutes

    def set_delaytimer_duration(self, hours: int, minutes: int):
        self._delaytimer_duration.value = hours * 60 + minutes

    def set_timer_on(self, hours: int, minutes: int):
        self._timer_on.value = hours * 60 + minutes

    def set_timer_off(self, hours: int, minutes: int):
        self._timer_off.value = hours * 60 + minutes

    @property
    def eco_limit(self) -> int:
        return self._eco_limit.value

    @eco_limit.setter
    def eco_limit(self, value: int):
        self._eco_limit.value = value

    @property
    def unit(self) -> Unit:
        return self._unit.value

    @unit.setter
    def unit(self, value: Unit):
        self._unit.value = value

    @property
    def firmware_version(self) -> int:
        self._firmware_version.value


class InvalidResponseFormatError(Exception):
    """The response does not have a known Argoclima format."""
