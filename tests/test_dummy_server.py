from homeassistant.config_entries import SOURCE_INTEGRATION_DISCOVERY
from homeassistant.core import HomeAssistant

from custom_components.argoclima.const import DOMAIN
from custom_components.argoclima.dummy_server import ArgoPushData
from custom_components.argoclima.dummy_server import _peer_host
from custom_components.argoclima.dummy_server import _push_data_from_params
from custom_components.argoclima.dummy_server import _redact_sensitive_text
from custom_components.argoclima.dummy_server import _valid_host
from custom_components.argoclima.dummy_server import async_handle_push_data

from .conftest import HOST

HUB_ID = "dummy_server_hub:test"
PARAMS = {"IP": HOST, "CPU_ID": "ABC123", "HMI": "N"}


class FakeWriter:
    def __init__(self, peername: tuple[str, int] | None) -> None:
        self._peername = peername

    def get_extra_info(self, name: str) -> tuple[str, int] | None:
        return self._peername


def test_accepts_push_from_claimed_ip() -> None:
    push_data = _push_data_from_params(PARAMS, HUB_ID, HOST)

    assert push_data.host == HOST
    assert push_data.cpu_id == "ABC123"
    assert push_data.hub_id == HUB_ID


def test_rejects_push_from_other_ip() -> None:
    assert _push_data_from_params(PARAMS, HUB_ID, "192.168.1.99") is None


def test_rejects_push_from_unknown_source() -> None:
    assert _push_data_from_params(PARAMS, HUB_ID, None) is None


def test_accepts_ipv4_mapped_peer_address() -> None:
    peer = _valid_host(f"::ffff:{HOST}")

    assert _push_data_from_params(PARAMS, HUB_ID, peer).host == HOST


def test_falls_back_to_host_based_id_without_cpu_id() -> None:
    push_data = _push_data_from_params({"IP": HOST}, HUB_ID, HOST)

    assert push_data.cpu_id == f"host:{HOST}"


def test_peer_host() -> None:
    assert _peer_host(FakeWriter((HOST, 54321))) == HOST
    assert _peer_host(FakeWriter(None)) is None


def test_redacts_credentials() -> None:
    redacted = _redact_sensitive_text("/?CM=UI_FLG&USN=user&PSW=secret&IP=1")

    assert "secret" not in redacted
    assert "user" not in redacted
    assert "IP=1" in redacted


async def test_unknown_device_starts_discovery(hass: HomeAssistant) -> None:
    await async_handle_push_data(
        hass, ArgoPushData(cpu_id="ABC123", host=HOST, hmi=None, hub_id=None)
    )
    await hass.async_block_till_done()

    [flow] = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert flow["context"]["source"] == SOURCE_INTEGRATION_DISCOVERY
    assert flow["context"]["unique_id"] == "ABC123"
    assert flow["step_id"] == "discovery_confirm"
