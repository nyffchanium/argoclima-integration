from __future__ import annotations

import asyncio
import hashlib
import logging
import secrets
from datetime import timedelta

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.update_coordinator import UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__package__)

FIRMWARE_URL = "http://31.14.128.210/UI/UI.php"
FIRMWARE_UNIT = "OU_FW"
FIRMWARE_WIFI = "UI_FW"
FIRMWARE_CHECK_INTERVAL = timedelta(days=1)
FIRMWARE_TIMEOUT = 15
DATA_FIRMWARE_COORDINATOR = f"{DOMAIN}_firmware"


class ArgoFirmwareCoordinator(DataUpdateCoordinator[dict[str, str]]):
    """Fetch the latest firmware versions Argo publishes."""

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=None,
            name=f"{DOMAIN} firmware",
            update_interval=FIRMWARE_CHECK_INTERVAL,
        )

    async def _async_update_data(self) -> dict[str, str]:
        session = async_get_clientsession(self.hass)
        try:
            return {
                firmware: await async_fetch_latest_release(session, firmware)
                for firmware in (FIRMWARE_UNIT, FIRMWARE_WIFI)
            }
        except (aiohttp.ClientError, TimeoutError, KeyError, ValueError) as err:
            raise UpdateFailed(
                f"Could not fetch Argo firmware versions: {err!r}"
            ) from err


async def async_fetch_latest_release(
    session: aiohttp.ClientSession, firmware: str
) -> str:
    # Argo's server answers version queries for any account, so no real
    # credentials or device ids are sent.
    params = {
        "CM": firmware,
        "PK": "-1",
        "USN": secrets.token_hex(4),
        "PSW": hashlib.md5(secrets.token_bytes(8), usedforsecurity=False).hexdigest(),
        "CPU_ID": secrets.token_hex(8),
    }
    async with (
        asyncio.timeout(FIRMWARE_TIMEOUT),
        session.get(FIRMWARE_URL, params=params) as response,
    ):
        response.raise_for_status()
        text = await response.text()

    fields = dict(
        part.split("=", 1)
        for part in text.strip().removesuffix("|||").split("|")
        if "=" in part
    )
    return fields["RELEASE"]


@callback
def async_get_firmware_coordinator(hass: HomeAssistant) -> ArgoFirmwareCoordinator:
    if DATA_FIRMWARE_COORDINATOR not in hass.data:
        hass.data[DATA_FIRMWARE_COORDINATOR] = ArgoFirmwareCoordinator(hass)
    return hass.data[DATA_FIRMWARE_COORDINATOR]
