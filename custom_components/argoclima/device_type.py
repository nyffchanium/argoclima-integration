from typing import List
from custom_components.argoclima.const import ARGO_DEVICE_ULISSE_ECO, PLATFORM_CLIMATE


class DeviceType:
    def __init__(
        self, name: str, port: int, update_interval: int, platforms: List[str]
    ) -> None:
        self._name = name
        self._port = port
        self._update_interval = update_interval
        self._platforms = platforms

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
    def platforms(self) -> List[str]:
        return self._platforms

    def __str__(self) -> str:
        return self.name

    @classmethod
    def from_name(cls, name: str):
        map = {
            ARGO_DEVICE_ULISSE_ECO: DeviceType(
                ARGO_DEVICE_ULISSE_ECO, 1001, 10, [PLATFORM_CLIMATE]
            )
        }
        return map[name] if name in map else None
