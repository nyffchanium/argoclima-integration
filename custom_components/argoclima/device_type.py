from typing import List

from custom_components.argoclima.const import ARGO_DEVICE_ULISSE_ECO
from custom_components.argoclima.const import PLATFORM_CLIMATE
from custom_components.argoclima.types import ArgoFanSpeed
from custom_components.argoclima.types import ArgoFlapMode
from custom_components.argoclima.types import ArgoOperationMode
from custom_components.argoclima.types import ArgoTimerType


class InvalidOperationError(Exception):
    """"This operation is not available for this device type"""


class ArgoDeviceType:
    def __init__(self, name: str, port: int, update_interval: int) -> None:
        self._name = name
        self._port = port
        self._update_interval = update_interval
        self._on_off = False
        self._operation_modes: List[ArgoOperationMode] = []
        self._operation_mode = False
        self._eco_mode = False
        self._turbo_mode = False
        self._night_mode = False
        self._preset = False
        self._target_temperature = False
        self._target_temperature_min: float = None
        self._target_temperature_max: float = None
        self._current_temperature = False
        self._fan_speeds: List[ArgoFanSpeed] = []
        self._fan_speed = False
        self._flap_modes: List[ArgoFlapMode] = []
        self._flap_mode = False
        self._filter_mode = False
        self._timers: List[ArgoTimerType] = []
        self._timer = False
        self._set_time_and_weekday = False
        self._device_lights = False
        self._unit = False
        self._eco_limit = False
        self._firmware = False
        self._reset = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def port(self) -> int:
        return self._port

    @property
    def update_interval(self) -> int:
        return self._update_interval

    @property
    def on_off(self) -> bool:
        return self._on_off

    @property
    def operation_modes(self) -> List[ArgoOperationMode]:
        return self._operation_modes

    @property
    def operation_mode(self) -> bool:
        return self._operation_mode

    @property
    def eco_mode(self) -> bool:
        return self._eco_mode

    @property
    def turbo_mode(self) -> bool:
        return self._turbo_mode

    @property
    def night_mode(self) -> bool:
        return self._night_mode

    @property
    def preset(self) -> bool:
        return self._preset

    @property
    def target_temperature(self) -> bool:
        return self._target_temperature

    @property
    def target_temperature_min(self) -> float:
        return self._target_temperature_min

    @property
    def target_temperature_max(self) -> float:
        return self._target_temperature_max

    @property
    def current_temperature(self) -> bool:
        return self._current_temperature

    @property
    def fan_speeds(self) -> List[ArgoFanSpeed]:
        return self._fan_speeds

    @property
    def fan_speed(self) -> bool:
        return self._fan_speed

    @property
    def flap_modes(self) -> List[ArgoFlapMode]:
        return self._flap_modes

    @property
    def flap_mode(self) -> bool:
        return self._flap_mode

    @property
    def filter_mode(self) -> bool:
        return self._filter_mode

    @property
    def timers(self) -> List[ArgoTimerType]:
        return self._timers

    @property
    def timer(self) -> bool:
        return self._timer

    @property
    def set_time_and_weekday(self) -> bool:
        return self._set_time_and_weekday

    @property
    def device_lights(self) -> bool:
        return self._device_lights

    @property
    def unit(self) -> bool:
        return self._unit

    @property
    def eco_limit(self) -> bool:
        return self._eco_limit

    @property
    def firmware(self) -> bool:
        return self._firmware

    @property
    def reset(self) -> bool:
        return self._reset

    @property
    def platforms(self) -> List[str]:
        list = []
        if self._on_off:
            list.append(PLATFORM_CLIMATE)
        return list

    def __str__(self) -> str:
        return self.name

    @classmethod
    def from_name(cls, name: str) -> "ArgoDeviceType":
        map = {
            ARGO_DEVICE_ULISSE_ECO: ArgoDeviceTypeBuilder(
                ARGO_DEVICE_ULISSE_ECO, 1001, 10
            )
            .on_off()
            .operation_modes(
                [
                    ArgoOperationMode.COOL,
                    ArgoOperationMode.DRY,
                    ArgoOperationMode.FAN,
                    ArgoOperationMode.AUTO,
                ]
            )
            .eco_mode()
            .turbo_mode()
            .night_mode()
            .current_temperature()
            .target_temperature(10, 32)
            .fan_speeds(
                [
                    ArgoFanSpeed.AUTO,
                    ArgoFanSpeed.LOWEST,
                    ArgoFanSpeed.LOW,
                    ArgoFanSpeed.MEDIUM,
                    ArgoFanSpeed.HIGH,
                    ArgoFanSpeed.HIGHER,
                    ArgoFanSpeed.HIGHEST,
                ]
            )
            .build()
        }
        return map[name] if name in map else None


class ArgoDeviceTypeBuilder:
    def __init__(self, name: str, port: int, update_interval: int) -> None:
        self._deviceType = ArgoDeviceType(name, port, update_interval)

    def build(self) -> ArgoDeviceType:
        return self._deviceType

    def on_off(self) -> "ArgoDeviceTypeBuilder":
        self._deviceType._on_off = True
        return self

    def operation_modes(
        self, modes: List[ArgoOperationMode]
    ) -> "ArgoDeviceTypeBuilder":
        self._deviceType._operation_modes = modes
        self._deviceType._operation_mode = True
        return self

    def eco_mode(self) -> "ArgoDeviceTypeBuilder":
        self._deviceType._eco_mode = True
        self._deviceType._preset = True
        return self

    def turbo_mode(self) -> "ArgoDeviceTypeBuilder":
        self._deviceType._turbo_mode = True
        self._deviceType._preset = True
        return self

    def night_mode(self) -> "ArgoDeviceTypeBuilder":
        self._deviceType._night_mode = True
        self._deviceType._preset = True
        return self

    def target_temperature(self, min: float, max: float) -> "ArgoDeviceTypeBuilder":
        self._deviceType._target_temperature = True
        self._deviceType._target_temperature_min = min
        self._deviceType._target_temperature_max = max
        return self

    def current_temperature(self) -> "ArgoDeviceTypeBuilder":
        self._deviceType._current_temperature = True
        return self

    def fan_speeds(self, modes: List[ArgoFanSpeed]) -> "ArgoDeviceTypeBuilder":
        self._deviceType._fan_speeds = modes
        self._deviceType._fan_speed = True
        return self

    def flap_modes(self, modes: List[ArgoFlapMode]) -> "ArgoDeviceTypeBuilder":
        self._deviceType._flap_modes = modes
        self._deviceType._flap_mode = True
        return self

    def filter_mode(self) -> "ArgoDeviceTypeBuilder":
        self._deviceType._filter_mode = True
        return self

    def timers(self, modes: List[ArgoTimerType]) -> "ArgoDeviceTypeBuilder":
        self._deviceType._timers = modes
        self._deviceType._timer = True
        return self

    def set_time_and_weekday(self) -> "ArgoDeviceTypeBuilder":
        self._deviceType._set_time_and_weekday = True
        return self

    def device_lights(self) -> "ArgoDeviceTypeBuilder":
        self._deviceType._device_lights = True
        return self

    def unit(self) -> "ArgoDeviceTypeBuilder":
        self._deviceType._unit = True
        return self

    def eco_limit(self) -> "ArgoDeviceTypeBuilder":
        self._deviceType._eco_limit = True
        return self

    def firmware(self) -> "ArgoDeviceTypeBuilder":
        self._deviceType._firmware = True
        return self

    def reset(self) -> "ArgoDeviceTypeBuilder":
        self._deviceType._reset = True
        return self
