import asyncio

from custom_components.argoclima.api import ArgoApiClient
from custom_components.argoclima.data import ArgoData
from custom_components.argoclima.device_type import ULISSE_ECO

from .conftest import HOST
from .conftest import device_response


class FakeResponse:
    def __init__(self, session: "FakeSession") -> None:
        self._session = session

    async def __aenter__(self) -> "FakeResponse":
        self._session.active += 1
        self._session.max_active = max(self._session.max_active, self._session.active)
        await asyncio.sleep(0.01)
        return self

    async def __aexit__(self, *args: object) -> None:
        self._session.active -= 1

    def raise_for_status(self) -> None:
        return

    async def text(self) -> str:
        return device_response()


class FakeSession:
    def __init__(self) -> None:
        self.urls: list[str] = []
        self.active = 0
        self.max_active = 0

    def get(self, url: str, headers: dict[str, str]) -> FakeResponse:
        self.urls.append(url)
        return FakeResponse(self)


async def test_request_url() -> None:
    session = FakeSession()
    client = ArgoApiClient(ULISSE_ECO, HOST, session)

    data = await client.async_sync_data(None)

    assert session.urls == [f"http://{HOST}:1001/?HMI={','.join(['N'] * 36)}&UPD=0"]
    assert data.temp == 23.5


async def test_requests_are_serialized() -> None:
    session = FakeSession()
    client = ArgoApiClient(ULISSE_ECO, HOST, session)

    await asyncio.gather(
        client.async_sync_data(ArgoData(ULISSE_ECO)),
        client.async_sync_data(ArgoData(ULISSE_ECO)),
    )

    assert session.max_active == 1
