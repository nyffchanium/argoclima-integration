import asyncio

import aiohttp

from .data import ArgoData
from .device_type import ArgoDeviceType

TIMEOUT = 8
HEADERS = {"Content-type": "text/html"}


class ArgoApiClient:
    def __init__(
        self, device_type: ArgoDeviceType, host: str, session: aiohttp.ClientSession
    ) -> None:
        self._host = host
        self._port = device_type.port
        self._type = device_type
        self._session = session
        self._request_lock = asyncio.Lock()

    @property
    def host(self) -> str:
        return self._host

    @host.setter
    def host(self, host: str) -> None:
        self._host = host

    async def async_sync_data(self, data: ArgoData | None) -> ArgoData:
        """Send pending changes to the device and return its current state."""
        if data is None:
            data = ArgoData(self._type)

        update = 1 if data.is_update_pending() else 0
        url = (
            f"http://{self._host}:{self._port}/"
            f"?HMI={data.to_parameter_string()}&UPD={update}"
        )

        # The device cancels a running request when a new one arrives.
        async with (
            self._request_lock,
            asyncio.timeout(TIMEOUT),
            self._session.get(url, headers=HEADERS) as response,
        ):
            response.raise_for_status()
            text = await response.text()

        data.parse_response_parameter_string(text)
        return data
