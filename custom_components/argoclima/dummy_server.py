from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from email.utils import format_datetime
from ipaddress import ip_address
from urllib.parse import parse_qsl
from urllib.parse import urlsplit

from custom_components.argoclima.const import ARGO_DEVICE_ULISSE_ECO
from custom_components.argoclima.const import CONF_CPU_ID
from custom_components.argoclima.const import CONF_DEVICE_TYPE
from custom_components.argoclima.const import CONF_HUB_ID
from custom_components.argoclima.const import CONF_HOST
from custom_components.argoclima.const import CONF_ROLE
from custom_components.argoclima.const import DOMAIN
from custom_components.argoclima.const import DUMMY_SERVER_BIND_HOST
from custom_components.argoclima.const import DUMMY_SERVER_DEVICE_IDENTIFIER_PREFIX
from custom_components.argoclima.const import DUMMY_SERVER_UNIQUE_ID_PREFIX
from custom_components.argoclima.const import ENTRY_ROLE_DEVICE
from custom_components.argoclima.const import ENTRY_ROLE_HUB
from custom_components.argoclima.data import ArgoData
from custom_components.argoclima.data import InvalidResponseFormatError
from custom_components.argoclima.device_type import ArgoDeviceType
from custom_components.argoclima.update_coordinator import ArgoDataUpdateCoordinator
from homeassistant.config_entries import SOURCE_INTEGRATION_DISCOVERY
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
import homeassistant.helpers.device_registry as dr

_LOGGER = logging.getLogger(__name__)

DATA_DISCOVERY_IN_FLIGHT_CPU_IDS = "discovery_in_flight_cpu_ids"
HOST_ONLY_CPU_ID_PREFIX = "host:"
REQUEST_HEADER_LIMIT = 16 * 1024
REQUEST_BODY_LIMIT = 16 * 1024
REQUEST_IDLE_TIMEOUT = 15
REQUEST_FOLLOWUP_DELAY = 1
CPU_ID_KEYS = ("CPU_ID", "SERIAL")
SENSITIVE_KEYS = {"SETUP", "USN", "PSW"}

UI_FLG_RESPONSE = "{|1|0|1|0|0|0|N,N,N,N,1,N,N,N,N,N,N,N,N,N,N,N,N,N,N,N,N,N,N,N,N,N,N,N,N,N,N,N,N,N,N,N,N,N|}[|0|||]ACN_FREE <br>\t\t"
FALLBACK_RESPONSE = "ERROR: Command unknow.. {command}<br>"


class InvalidDummyServerRequest(Exception):
    """The client sent an invalid or oversized request."""

    def __init__(self, reason: str, preview: str | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.preview = preview


@dataclass(frozen=True)
class ArgoPushData:
    """Device data pushed through a UI_FLG cloud request."""

    cpu_id: str
    host: str
    hmi: str | None
    hub_id: str | None
    device_type: str = ARGO_DEVICE_ULISSE_ECO


class ArgoDummyServer:
    """Minimal TCP listener that mimics the Argoclima cloud endpoint."""

    def __init__(self, hass: HomeAssistant, port: int, hub_id: str) -> None:
        self._hass = hass
        self._port = port
        self._hub_id = hub_id
        self._server: asyncio.Server | None = None
        self._connections: set[asyncio.StreamWriter] = set()

    async def async_start(self) -> None:
        """Start the listener."""
        self._server = await asyncio.start_server(
            self._handle_client,
            host=DUMMY_SERVER_BIND_HOST,
            port=self._port,
        )
        _LOGGER.info(
            "Argoclima dummy server listening on %s:%s",
            DUMMY_SERVER_BIND_HOST,
            self._port,
        )

    async def async_stop(self) -> None:
        """Stop the listener and close active connections."""
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

        connections = list(self._connections)
        for writer in connections:
            writer.close()
        await asyncio.gather(
            *(writer.wait_closed() for writer in connections),
            return_exceptions=True,
        )
        self._connections.clear()
        _LOGGER.info("Argoclima dummy server stopped")

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        self._connections.add(writer)
        try:
            while True:
                try:
                    request = await _read_http_request(reader)
                except TimeoutError:
                    _LOGGER.debug("Argoclima dummy server connection timed out")
                    break
                except InvalidDummyServerRequest as err:
                    if err.preview:
                        _LOGGER.warning(
                            "Argoclima dummy server received an invalid request: %s; preview=%s",
                            err.reason,
                            err.preview,
                        )
                    else:
                        _LOGGER.warning(
                            "Argoclima dummy server received an invalid request: %s",
                            err.reason,
                        )
                    break

                if request is None:
                    break

                method, target = request
                _LOGGER.debug(
                    "Argoclima dummy server request: %s %s",
                    method,
                    _redact_sensitive_text(target),
                )
                body = await self._async_response_body(method, target)
                writer.write(_build_http_response(body))
                await writer.drain()
                await asyncio.sleep(REQUEST_FOLLOWUP_DELAY)
        finally:
            self._connections.discard(writer)
            writer.close()
            await writer.wait_closed()

    async def _async_response_body(self, method: str, target: str) -> str:
        if method not in {"GET", "POST"}:
            return _fallback_response(method)

        query = urlsplit(target).query
        params = _parse_query(query)
        command = params.get("CM", "").upper()

        if command == "UI_NTP":
            return _ntp_response()

        if command == "UI_FLG":
            push_data = _push_data_from_params(params, self._hub_id)
            if push_data is not None:
                _LOGGER.info(
                    "Argoclima UI_FLG push received for CPU_ID %s from %s via hub %s",
                    push_data.cpu_id,
                    push_data.host,
                    push_data.hub_id,
                )
                await async_handle_push_data(self._hass, push_data)
            else:
                _LOGGER.warning(
                    "Argoclima UI_FLG push ignored; required fields missing or invalid. Present fields: %s",
                    sorted(params),
                )
            return UI_FLG_RESPONSE

        return _fallback_response(params.get("CM", ""))


def async_dummy_server_running(hass: HomeAssistant) -> bool:
    """Return true if a dummy server entry is currently loaded."""
    domain_data = hass.data.get(DOMAIN, {})
    return any(isinstance(value, ArgoDummyServer) for value in domain_data.values())


def async_entry_role(entry: ConfigEntry) -> str:
    """Return the configured entry role, defaulting entries to device."""
    return entry.data.get(CONF_ROLE, ENTRY_ROLE_DEVICE)


def dummy_server_unique_id(port: int) -> str:
    """Return the unique id for a dummy server listening on port."""
    return f"{DUMMY_SERVER_UNIQUE_ID_PREFIX}:{port}"


def dummy_server_hub_id(entry: ConfigEntry) -> str:
    """Return the stable hub device identifier for a dummy server entry."""
    return entry.data.get(
        CONF_HUB_ID,
        f"{DUMMY_SERVER_DEVICE_IDENTIFIER_PREFIX}:{entry.entry_id}",
    )


async def async_handle_push_data(hass: HomeAssistant, push_data: ArgoPushData) -> None:
    """Dispatch push data to an existing entry or start a discovery flow."""
    entry = _find_device_entry(hass, push_data)
    if entry is None:
        _LOGGER.info(
            "Argoclima device CPU_ID %s is unknown; starting discovery flow",
            push_data.cpu_id,
        )
        await _async_start_discovery_flow(hass, push_data)
        return

    _async_update_entry_identity(hass, entry, push_data)
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if isinstance(coordinator, ArgoDataUpdateCoordinator):
        _LOGGER.debug(
            "Argoclima push matched loaded entry %s; updating host to %s",
            entry.entry_id,
            push_data.host,
        )
        coordinator.async_update_host(push_data.host)
        coordinator.async_set_push_updates_enabled(True)
        data = _data_from_hmi(push_data, coordinator.data)
        if data is not None:
            coordinator.async_set_updated_data(data)
            _LOGGER.debug(
                "Argoclima push data applied to coordinator for entry %s",
                entry.entry_id,
            )
        else:
            _LOGGER.debug(
                "Argoclima push for entry %s did not include valid HMI state",
                entry.entry_id,
            )
    else:
        _LOGGER.debug(
            "Argoclima push matched entry %s, but entry is not loaded",
            entry.entry_id,
        )
    _async_update_device_registry_hub(hass, entry, push_data)


def _find_device_entry(
    hass: HomeAssistant, push_data: ArgoPushData
) -> ConfigEntry | None:
    ip_only_match: ConfigEntry | None = None
    for entry in hass.config_entries.async_entries(DOMAIN):
        if async_entry_role(entry) != ENTRY_ROLE_DEVICE:
            continue

        if entry.data.get(CONF_CPU_ID) == push_data.cpu_id:
            return entry
        if entry.unique_id == push_data.cpu_id:
            return entry

        if (
            (
                entry.data.get(CONF_CPU_ID) is None
                or str(entry.data.get(CONF_CPU_ID)).startswith(HOST_ONLY_CPU_ID_PREFIX)
            )
            and entry.data.get(CONF_HOST) == push_data.host
        ):
            ip_only_match = entry

    return ip_only_match


def _async_update_entry_identity(
    hass: HomeAssistant, entry: ConfigEntry, push_data: ArgoPushData
) -> None:
    data = dict(entry.data)
    changed = False

    if data.get(CONF_ROLE) != ENTRY_ROLE_DEVICE:
        data[CONF_ROLE] = ENTRY_ROLE_DEVICE
        changed = True
    if data.get(CONF_CPU_ID) != push_data.cpu_id:
        data[CONF_CPU_ID] = push_data.cpu_id
        changed = True
    if data.get(CONF_HOST) != push_data.host:
        data[CONF_HOST] = push_data.host
        changed = True
    if push_data.hub_id is not None and data.get(CONF_HUB_ID) != push_data.hub_id:
        data[CONF_HUB_ID] = push_data.hub_id
        changed = True
    if data.get(CONF_DEVICE_TYPE) is None:
        data[CONF_DEVICE_TYPE] = push_data.device_type
        changed = True

    if changed or entry.unique_id != push_data.cpu_id:
        _LOGGER.info(
            "Updating Argoclima entry %s identity/host from push CPU_ID %s host %s",
            entry.entry_id,
            push_data.cpu_id,
            push_data.host,
        )
        hass.config_entries.async_update_entry(
            entry,
            data=data,
            unique_id=push_data.cpu_id,
        )


async def _async_start_discovery_flow(
    hass: HomeAssistant, push_data: ArgoPushData
) -> None:
    in_flight = hass.data.setdefault(DOMAIN, {}).setdefault(
        DATA_DISCOVERY_IN_FLIGHT_CPU_IDS, set()
    )
    if push_data.cpu_id in in_flight:
        _LOGGER.debug(
            "Argoclima discovery flow for CPU_ID %s is already starting",
            push_data.cpu_id,
        )
        return

    flow_manager = hass.config_entries.flow
    if hasattr(flow_manager, "async_progress_by_handler"):
        for flow in flow_manager.async_progress_by_handler(DOMAIN):
            if flow.get("context", {}).get("unique_id") == push_data.cpu_id:
                _LOGGER.debug(
                    "Argoclima discovery flow for CPU_ID %s already in progress",
                    push_data.cpu_id,
                )
                return

    _LOGGER.info(
        "Starting Argoclima discovery flow for CPU_ID %s host %s",
        push_data.cpu_id,
        push_data.host,
    )
    in_flight.add(push_data.cpu_id)
    try:
        await flow_manager.async_init(
            DOMAIN,
            context={
                "source": SOURCE_INTEGRATION_DISCOVERY,
                "unique_id": push_data.cpu_id,
            },
            data={
                CONF_CPU_ID: push_data.cpu_id,
                CONF_HOST: push_data.host,
                CONF_HUB_ID: push_data.hub_id,
                CONF_DEVICE_TYPE: push_data.device_type,
            },
        )
    finally:
        in_flight.discard(push_data.cpu_id)


def _data_from_hmi(
    push_data: ArgoPushData, current_data: ArgoData | None = None
) -> ArgoData | None:
    if push_data.hmi is None:
        return None

    device_type = ArgoDeviceType.from_name(push_data.device_type)
    if device_type is None:
        return None

    data = ArgoData(device_type)
    try:
        data.parse_response_parameter_string(push_data.hmi)
    except (InvalidResponseFormatError, ValueError):
        _LOGGER.warning(
            "Argoclima push for CPU_ID %s included invalid HMI payload",
            push_data.cpu_id,
        )
        return None

    if current_data is not None and current_data.is_update_pending():
        current_data.parse_response_parameter_string(push_data.hmi)
        return current_data

    return data


def _async_update_device_registry_hub(
    hass: HomeAssistant, entry: ConfigEntry, push_data: ArgoPushData
) -> None:
    if push_data.hub_id is None:
        return

    device_registry = dr.async_get(hass)
    hub_device = device_registry.async_get_device(
        identifiers={(DOMAIN, push_data.hub_id)}
    )
    if hub_device is None:
        return

    hub_entry = _hub_entry_for_id(hass, push_data.hub_id)
    if hub_entry is None:
        return

    device = device_registry.async_get_device(
        identifiers={(DOMAIN, push_data.cpu_id)}
    ) or device_registry.async_get_device(identifiers={(DOMAIN, entry.entry_id)})
    if device is None:
        return

    _move_device_registry_parent(
        device_registry, device, entry, hub_entry, hub_device.id
    )


def _hub_entry_for_id(hass: HomeAssistant, hub_id: str) -> ConfigEntry | None:
    for entry in hass.config_entries.async_entries(DOMAIN):
        if (
            async_entry_role(entry) == ENTRY_ROLE_HUB
            and dummy_server_hub_id(entry) == hub_id
        ):
            return entry
    return None


def _move_device_registry_parent(
    device_registry: dr.DeviceRegistry,
    device: dr.DeviceEntry,
    entry: ConfigEntry,
    hub_entry: ConfigEntry,
    hub_device_id: str,
) -> None:
    if (
        device.primary_config_entry == hub_entry.entry_id
        and device.via_device_id == hub_device_id
    ):
        return

    device = device_registry.async_update_device(
        device.id,
        add_config_entry_id=hub_entry.entry_id,
        device_info_type="primary",
        via_device_id=hub_device_id,
    )
    if device is None:
        return

    if (
        device.primary_config_entry != hub_entry.entry_id
        and entry.entry_id in device.config_entries
        and len(device.config_entries) > 1
    ):
        device = device_registry.async_update_device(
            device.id,
            remove_config_entry_id=entry.entry_id,
        )
        if device is None:
            return

    device_registry.async_update_device(
        device.id,
        add_config_entry_id=hub_entry.entry_id,
        device_info_type="primary",
        via_device_id=hub_device_id,
    )


async def _read_http_request(
    reader: asyncio.StreamReader,
) -> tuple[str, str] | None:
    while True:
        try:
            header = await asyncio.wait_for(
                reader.readuntil(b"\r\n\r\n"), timeout=REQUEST_IDLE_TIMEOUT
            )
        except asyncio.IncompleteReadError as err:
            if err.partial:
                if not err.partial.strip():
                    _LOGGER.debug(
                        "Argoclima dummy server connection closed after blank data"
                    )
                    return None
                raise InvalidDummyServerRequest(
                    "connection closed before request headers completed",
                    _preview_bytes(err.partial),
                ) from err
            return None
        except asyncio.LimitOverrunError as err:
            raise InvalidDummyServerRequest("request headers exceeded stream limit") from err

        if len(header) > REQUEST_HEADER_LIMIT:
            raise InvalidDummyServerRequest(
                "request headers exceeded configured limit",
                _preview_bytes(header),
            )

        head = header.removesuffix(b"\r\n\r\n")
        lines = head.decode("iso-8859-1").split("\r\n")
        while lines and not lines[0].strip():
            lines.pop(0)
        if lines:
            break
        _LOGGER.debug("Argoclima dummy server ignored blank keep-alive data")

    request_line = lines[0].split()
    if len(request_line) < 3:
        raise InvalidDummyServerRequest(
            "request line did not include method, target, and HTTP version",
            _preview_text(lines[0]),
        )

    headers = {}
    for line in lines[1:]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        headers[key.lower()] = value.strip()

    content_length = _content_length(headers.get("content-length"))
    if content_length > REQUEST_BODY_LIMIT:
        raise InvalidDummyServerRequest("request body exceeded configured limit")

    if content_length > 0:
        try:
            await asyncio.wait_for(
                reader.readexactly(content_length), timeout=REQUEST_IDLE_TIMEOUT
            )
        except asyncio.IncompleteReadError as err:
            raise InvalidDummyServerRequest(
                "connection closed before request body completed",
                _preview_bytes(err.partial),
            ) from err

    return request_line[0].upper(), request_line[1]


def _content_length(value: str | None) -> int:
    if value is None:
        return 0
    try:
        return int(value)
    except ValueError as err:
        raise InvalidDummyServerRequest("content-length header was not an integer") from err


def _preview_bytes(value: bytes) -> str:
    return _preview_text(value.decode("iso-8859-1", errors="replace"))


def _preview_text(value: str) -> str:
    return repr(_redact_sensitive_text(value)[:300])


def _redact_sensitive_text(value: str) -> str:
    redacted = value
    for key in SENSITIVE_KEYS:
        redacted = re.sub(
            rf"({re.escape(key)}=)[^&\s]*",
            rf"\1<redacted>",
            redacted,
            flags=re.IGNORECASE,
        )
    return redacted


def _parse_query(query: str) -> dict[str, str]:
    return {
        key.upper(): value
        for key, value in parse_qsl(query, keep_blank_values=True)
        if key.upper() not in SENSITIVE_KEYS
    }


def _push_data_from_params(params: dict[str, str], hub_id: str) -> ArgoPushData | None:
    cpu_id = next(
        (
            params[key].strip()
            for key in CPU_ID_KEYS
            if params.get(key) is not None and params[key].strip()
        ),
        None,
    )
    host = _valid_host(params.get("IP"))
    if host is None:
        return None
    if cpu_id is None:
        cpu_id = f"{HOST_ONLY_CPU_ID_PREFIX}{host}"

    hmi = params.get("HMI")
    return ArgoPushData(
        cpu_id=cpu_id,
        host=host,
        hmi=hmi if hmi else None,
        hub_id=hub_id,
    )


def _valid_host(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        return str(ip_address(value.strip()))
    except ValueError:
        return None


def _ntp_response() -> str:
    return datetime.now(timezone.utc).strftime(
        "NTP %Y-%m-%dT%H:%M:%S+00:00 UI SERVER (M.A.V. srl)"
    )


def _fallback_response(command: str) -> str:
    return FALLBACK_RESPONSE.format(command=command)


def _build_http_response(body: str) -> bytes:
    encoded_body = body.encode("utf-8")
    now = datetime.now(timezone.utc)
    headers = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: text/html; charset=UTF-8\r\n"
        "Server: Microsoft-IIS/8.5\r\n"
        "X-Powered-By: PHP/7.0.30\r\n"
        "Access-Control-Allow-Origin: *\r\n"
        "Access-Control-Allow-Methods: *\r\n"
        "Access-Control-Allow-Headers: *\r\n"
        f"Date: {format_datetime(now, usegmt=True)}\r\n"
        f"Content-Length: {len(encoded_body)}\r\n"
        "\r\n"
    )
    return headers.encode() + encoded_body
