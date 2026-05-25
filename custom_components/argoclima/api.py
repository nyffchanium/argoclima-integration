import asyncio

import aiohttp
import async_timeout
from custom_components.argoclima.data import ArgoData
from custom_components.argoclima.device_type import ArgoDeviceType

TIMEOUT = 8

HEADERS = {"Content-type": "text/html"}


class ArgoApiClient:
    def __init__(
        self, type: ArgoDeviceType, host: str, session: aiohttp.ClientSession
    ) -> None:
        self._host = host
        self._port = type.port
        self._type = type
        self._session = session
        self._request_lock = asyncio.Lock()

    @property
    def host(self) -> str:
        return self._host

    @host.setter
    def host(self, host: str) -> None:
        self._host = host

    async def async_sync_data(self, data: ArgoData) -> ArgoData:
        if data is None:
            data = ArgoData(self._type)

        url = f"http://{self._host}:{self._port}/?HMI={data.to_parameter_string()}&UPD={1 if data.is_update_pending() else 0}"

        async with (
            self._request_lock,
            async_timeout.timeout(TIMEOUT),
            self._session.get(url, headers=HEADERS) as response,
        ):
            response.raise_for_status()
            text = await response.text()

        data.parse_response_parameter_string(text)
        return data
