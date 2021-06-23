from custom_components.argoclima.data import ArgoData
import logging
import asyncio
import socket
import aiohttp
import async_timeout

TIMEOUT = 10


_LOGGER: logging.Logger = logging.getLogger(__package__)

HEADERS = {"Content-type": "text/html"}


class ArgoApiClient:
    def __init__(self, host: str, port: int, session: aiohttp.ClientSession) -> None:
        self._host = host
        self._port = port
        self._session = session

    async def async_call_api(self, data: ArgoData = None) -> ArgoData:
        has_data = data is not None
        if data is None:
            data = ArgoData()

        url = f"http://{self._host}:{self._port}/?HMI={data.to_update_query()}&UPD={1 if has_data else 0}"

        try:
            async with async_timeout.timeout(TIMEOUT, loop=asyncio.get_event_loop()):
                response = await self._session.get(url, headers=HEADERS)
                return ArgoData.parse_response_query(await response.text())

        except asyncio.TimeoutError as exception:
            _LOGGER.error(
                "Timeout error fetching information from %s - %s",
                url,
                exception,
            )

        except (KeyError, TypeError) as exception:
            _LOGGER.error(
                "Error parsing information from %s - %s",
                url,
                exception,
            )
        except (aiohttp.ClientError, socket.gaierror) as exception:
            _LOGGER.error(
                "Error fetching information from %s - %s",
                url,
                exception,
            )
        except Exception as exception:  # pylint: disable=broad-except
            _LOGGER.error("Something really wrong happened! - %s", exception)
