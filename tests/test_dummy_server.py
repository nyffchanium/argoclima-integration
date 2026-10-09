import asyncio
import logging
import socket
import struct

import pytest
from homeassistant.config_entries import SOURCE_INTEGRATION_DISCOVERY
from homeassistant.core import HomeAssistant

from custom_components.argoclima import dummy_server
from custom_components.argoclima.const import DOMAIN
from custom_components.argoclima.dummy_server import MAX_CONNECTIONS
from custom_components.argoclima.dummy_server import ArgoDummyServer
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


async def test_one_discovery_per_host(hass: HomeAssistant) -> None:
    for cpu_id in ("ABC123", "DEF456"):
        await async_handle_push_data(
            hass, ArgoPushData(cpu_id=cpu_id, host=HOST, hmi=None, hub_id=None)
        )
    await hass.async_block_till_done()

    assert len(hass.config_entries.flow.async_progress_by_handler(DOMAIN)) == 1


async def test_connection_limit(hass: HomeAssistant, socket_enabled: None) -> None:
    server = ArgoDummyServer(hass, 0, HUB_ID)
    await server.async_start()
    port = server._server.sockets[0].getsockname()[1]
    connections = []
    try:
        for _ in range(MAX_CONNECTIONS):
            connections.append(await asyncio.open_connection("127.0.0.1", port))
        await asyncio.sleep(0.1)

        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        assert await asyncio.wait_for(reader.read(), timeout=2) == b""
        writer.close()
    finally:
        for _, writer in connections:
            writer.close()
        await server.async_stop()


MALFORMED_REQUESTS = [
    b"\r\n\r\n",
    b"GARBAGE\r\n\r\n",
    b"GET http://[ HTTP/1.1\r\n\r\n",
    b"GET /?CM=UI_FLG&IP=999.1.1.1 HTTP/1.1\r\n\r\n",
    b"GET /?CM=UI_FLG&HMI=1,2,3 HTTP/1.1\r\n\r\n",
    b"POST / HTTP/1.1\r\nContent-Length: abc\r\n\r\n",
    b"POST / HTTP/1.1\r\nContent-Length: 999999\r\n\r\n",
    b"GET /" + b"A" * 70_000 + b" HTTP/1.1\r\n\r\n",
    b"\xff\xfe\x00\x01 / HTTP/1.1\r\n\r\n",
    b"GET /?CM=UI_FLG",
]


async def test_survives_malformed_and_aborted_requests(
    hass: HomeAssistant,
    socket_enabled: None,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dummy_server, "REQUEST_FOLLOWUP_DELAY", 0)
    server = ArgoDummyServer(hass, 0, HUB_ID)
    await server.async_start()
    port = server._server.sockets[0].getsockname()[1]

    async def send(payload: bytes, reset: bool = False) -> bytes:
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        writer.write(payload)
        await writer.drain()
        if reset:
            sock = writer.get_extra_info("socket")
            sock.setsockopt(
                socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0)
            )
            writer.close()
            return b""
        writer.write_eof()
        response = await asyncio.wait_for(reader.read(), timeout=5)
        writer.close()
        return response

    try:
        for payload in MALFORMED_REQUESTS:
            await send(payload)
            await send(payload, reset=True)
        await asyncio.sleep(0.2)

        response = await send(b"GET /?CM=UI_NTP HTTP/1.1\r\n\r\n")
        assert response.startswith(b"HTTP/1.1 200 OK")
        assert b"NTP " in response
    finally:
        await server.async_stop()

    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]
