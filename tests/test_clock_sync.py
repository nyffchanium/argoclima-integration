from datetime import timedelta
from unittest.mock import patch

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.argoclima.api import ArgoApiClient
from custom_components.argoclima.const import ARGO_DEVICE_ULISSE_ECO
from custom_components.argoclima.const import CONF_CPU_ID
from custom_components.argoclima.const import CONF_DEVICE_TYPE
from custom_components.argoclima.const import CONF_DEVICES
from custom_components.argoclima.const import CONF_HOST
from custom_components.argoclima.const import CONF_PORT
from custom_components.argoclima.const import CONF_ROLE
from custom_components.argoclima.const import DOMAIN
from custom_components.argoclima.const import ENTRY_ROLE_HUB
from custom_components.argoclima.dummy_server import ArgoDummyServer
from custom_components.argoclima.dummy_server import ArgoPushData
from custom_components.argoclima.dummy_server import async_handle_push_data
from custom_components.argoclima.runtime import dummy_server_hub_id
from custom_components.argoclima.types import ArgoWeekday

from .conftest import HOST
from .conftest import device_response

WEEKDAY_INDEX, TIME_INDEX = 18, 20

pytestmark = pytest.mark.clock_sync


@pytest.fixture(autouse=True)
def fixed_start(freezer: FrozenDateTimeFactory) -> None:
    """Start on a full minute, so the minute can't change during a test."""
    freezer.move_to("2026-10-15T10:00:00+00:00")


async def advance(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, delta: timedelta
) -> None:
    freezer.tick(delta)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


def clock_requests(sent_requests: list[str]) -> list[tuple[str, str]]:
    values = [request.split(",") for request in sent_requests]
    return [(v[WEEKDAY_INDEX], v[TIME_INDEX]) for v in values if v[TIME_INDEX] != "N"]


def expected_clock() -> tuple[str, str]:
    now = dt_util.now()
    return str(int(ArgoWeekday.from_datetime(now))), str(now.hour * 60 + now.minute)


async def test_clock_is_set_after_setup_and_daily(
    hass: HomeAssistant,
    mock_device: None,
    device_entry: MockConfigEntry,
    sent_requests: list[str],
    freezer: FrozenDateTimeFactory,
) -> None:
    device_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(device_entry.entry_id)
    await hass.async_block_till_done()

    await advance(hass, freezer, timedelta(seconds=15))
    await advance(hass, freezer, timedelta(seconds=2))
    assert clock_requests(sent_requests) == [expected_clock()]

    await advance(hass, freezer, timedelta(hours=12))
    assert len(clock_requests(sent_requests)) == 1

    await advance(hass, freezer, timedelta(hours=12))
    await advance(hass, freezer, timedelta(seconds=2))
    assert clock_requests(sent_requests)[1:] == [expected_clock()]


async def test_clock_is_set_after_reconnect(
    hass: HomeAssistant,
    mock_device: None,
    device_entry: MockConfigEntry,
    sent_requests: list[str],
    freezer: FrozenDateTimeFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    device_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(device_entry.entry_id)
    await hass.async_block_till_done()
    await advance(hass, freezer, timedelta(seconds=17))
    online = ArgoApiClient.async_sync_data

    async def offline(self, data):
        raise TimeoutError

    monkeypatch.setattr(ArgoApiClient, "async_sync_data", offline)
    for _ in range(3):
        await advance(hass, freezer, timedelta(seconds=15))
    monkeypatch.setattr(ArgoApiClient, "async_sync_data", online)
    await advance(hass, freezer, timedelta(seconds=15))
    await advance(hass, freezer, timedelta(seconds=15))

    assert len(clock_requests(sent_requests)) == 2


async def test_clock_is_set_on_first_push_with_dummy_server(
    hass: HomeAssistant,
    mock_device: None,
    sent_requests: list[str],
    freezer: FrozenDateTimeFactory,
) -> None:
    hub = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_ROLE: ENTRY_ROLE_HUB,
            CONF_PORT: 8080,
            CONF_DEVICES: {
                "device-key": {
                    CONF_DEVICE_TYPE: ARGO_DEVICE_ULISSE_ECO,
                    CONF_HOST: HOST,
                    CONF_CPU_ID: "A1B2C3",
                }
            },
        },
    )
    hub.add_to_hass(hass)
    with (
        patch.object(ArgoDummyServer, "async_start"),
        patch.object(ArgoDummyServer, "async_stop"),
    ):
        assert await hass.config_entries.async_setup(hub.entry_id)
        await hass.async_block_till_done()
        assert clock_requests(sent_requests) == []

        await async_handle_push_data(
            hass,
            ArgoPushData(
                cpu_id="A1B2C3",
                host=HOST,
                hmi=device_response(),
                hub_id=dummy_server_hub_id(hub),
            ),
        )
        await advance(hass, freezer, timedelta(seconds=2))

        assert clock_requests(sent_requests) == [expected_clock()]
        await hass.config_entries.async_unload(hub.entry_id)
