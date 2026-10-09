from __future__ import annotations

from dataclasses import dataclass

from homeassistant.const import Platform

from .const import ARGO_DEVICE_ULISSE_ECO
from .types import ArgoFanSpeed
from .types import ArgoOperationMode
from .types import ArgoTimerType


@dataclass(frozen=True)
class ArgoDeviceType:
    name: str
    port: int
    update_interval: int
    on_off: bool = False
    operation_modes: tuple[ArgoOperationMode, ...] = ()
    fan_speeds: tuple[ArgoFanSpeed, ...] = ()
    timers: tuple[ArgoTimerType, ...] = ()
    eco_mode: bool = False
    turbo_mode: bool = False
    night_mode: bool = False
    current_temperature: bool = False
    target_temperature_range: tuple[int, int] | None = None
    remote_temperature: bool = False
    device_lights: bool = False
    unit: bool = False
    eco_limit_range: tuple[int, int] | None = None

    @property
    def operation_mode(self) -> bool:
        return bool(self.operation_modes)

    @property
    def fan_speed(self) -> bool:
        return bool(self.fan_speeds)

    @property
    def timer(self) -> bool:
        return bool(self.timers)

    @property
    def preset(self) -> bool:
        return self.eco_mode or self.turbo_mode or self.night_mode

    @property
    def target_temperature(self) -> bool:
        return self.target_temperature_range is not None

    @property
    def target_temperature_min(self) -> int:
        return self.target_temperature_range[0]

    @property
    def target_temperature_max(self) -> int:
        return self.target_temperature_range[1]

    @property
    def eco_limit(self) -> bool:
        return self.eco_limit_range is not None

    @property
    def eco_limit_min(self) -> int:
        return self.eco_limit_range[0]

    @property
    def eco_limit_max(self) -> int:
        return self.eco_limit_range[1]

    @property
    def platforms(self) -> list[Platform]:
        platforms = []
        if self.on_off:
            platforms.append(Platform.CLIMATE)
        if self.eco_limit:
            platforms.append(Platform.NUMBER)
        if self.unit or self.timer:
            platforms.append(Platform.SELECT)
        if self.device_lights or self.remote_temperature:
            platforms.append(Platform.SWITCH)
        return platforms

    def __str__(self) -> str:
        return self.name

    @staticmethod
    def from_name(name: str | None) -> ArgoDeviceType | None:
        return DEVICE_TYPES.get(name)


ULISSE_ECO = ArgoDeviceType(
    name=ARGO_DEVICE_ULISSE_ECO,
    port=1001,
    update_interval=60,
    on_off=True,
    operation_modes=(
        ArgoOperationMode.COOL,
        ArgoOperationMode.DRY,
        ArgoOperationMode.FAN,
        ArgoOperationMode.AUTO,
    ),
    fan_speeds=tuple(ArgoFanSpeed),
    timers=tuple(ArgoTimerType),
    eco_mode=True,
    turbo_mode=True,
    night_mode=True,
    current_temperature=True,
    target_temperature_range=(10, 32),
    remote_temperature=True,
    device_lights=True,
    unit=True,
    eco_limit_range=(30, 99),
)

DEVICE_TYPES = {device_type.name: device_type for device_type in (ULISSE_ECO,)}
