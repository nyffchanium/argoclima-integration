from __future__ import annotations

import asyncio
from ipaddress import ip_address
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.config_entries import ConfigFlow
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.config_entries import OptionsFlow
from homeassistant.core import HomeAssistant
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ArgoApiClient
from .const import ARGO_DEVICE_ULISSE_ECO
from .const import ARGO_DEVICES
from .const import CONF_CPU_ID
from .const import CONF_DEVICE_TYPE
from .const import CONF_HOST
from .const import CONF_HUB_ID
from .const import CONF_NAME
from .const import CONF_NAT_GATEWAY
from .const import CONF_PORT
from .const import CONF_ROLE
from .const import DOCUMENTATION_URL
from .const import DOMAIN
from .const import DUMMY_SERVER_BIND_HOST
from .const import DUMMY_SERVER_DEFAULT_PORT
from .const import DUMMY_SERVER_TITLE
from .const import ENTRY_ROLE_DEVICE
from .const import ENTRY_ROLE_HUB
from .data import ArgoData
from .data import InvalidResponseFormatError
from .device_type import ArgoDeviceType
from .runtime import async_entry_role
from .runtime import async_update_hub_device
from .runtime import dummy_server_hub_id
from .runtime import dummy_server_unique_id
from .runtime import hub_entry_for_id

NO_HUB_ID = "__no_hub__"


async def async_test_host(
    hass: HomeAssistant, device_type: ArgoDeviceType, host: str
) -> bool:
    """Return true if host responds like a supported device."""
    client = ArgoApiClient(device_type, host, async_get_clientsession(hass))
    try:
        await client.async_sync_data(ArgoData(device_type))
    except (aiohttp.ClientError, TimeoutError, InvalidResponseFormatError, ValueError):
        return False
    return True


class ArgoFlowHandler(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._errors: dict[str, str] = {}
        self._discovery_info: dict[str, Any] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> ArgoOptionsFlowHandler:
        return ArgoOptionsFlowHandler()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        return self.async_show_menu(
            step_id="user",
            menu_options=["server", "device"],
        )

    async def async_step_server(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create the dummy server entry."""
        self._errors = {}

        if user_input is not None:
            port = user_input[CONF_PORT]
            self._errors = await _async_validate_server_input(self.hass, user_input)
            if self._errors:
                return self._show_server_form(user_input)

            await self.async_set_unique_id(dummy_server_unique_id(port))
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=_server_title(port),
                data=_server_data({CONF_ROLE: ENTRY_ROLE_HUB}, user_input),
            )

        return self._show_server_form(user_input)

    def _show_server_form(self, user_input: dict[str, Any]) -> ConfigFlowResult:
        return self.async_show_form(
            step_id="server",
            data_schema=_server_schema(user_input),
            errors=self._errors,
        )

    async def async_step_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a manually configured device."""
        self._errors = {}

        if user_input is not None:
            device_type = ArgoDeviceType.from_name(user_input[CONF_DEVICE_TYPE])
            if device_type is not None:
                host_ok = await async_test_host(
                    self.hass, device_type, user_input[CONF_HOST]
                )
                if host_ok:
                    data = {
                        CONF_ROLE: ENTRY_ROLE_DEVICE,
                        CONF_DEVICE_TYPE: user_input[CONF_DEVICE_TYPE],
                        CONF_HOST: user_input[CONF_HOST],
                    }
                    if hub_id := _selected_hub_id(user_input):
                        return self._async_add_device_to_hub(
                            hub_id,
                            {
                                **data,
                                CONF_HUB_ID: hub_id,
                                CONF_NAME: user_input[CONF_NAME],
                            },
                        )
                    return self.async_create_entry(
                        title=user_input[CONF_NAME],
                        data=data,
                    )
                self._errors["base"] = "host"
            else:
                self._errors["base"] = "invalid_device_type"

        return self._show_device_form(user_input)

    async def async_step_integration_discovery(
        self, discovery_info: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle a device discovered from dummy server push traffic."""
        cpu_id = discovery_info.get(CONF_CPU_ID)
        if cpu_id is None:
            return self.async_abort(reason="missing_cpu_id")

        self._discovery_info = discovery_info
        await self.async_set_unique_id(cpu_id)
        self._abort_if_unique_id_configured(
            updates={
                CONF_ROLE: ENTRY_ROLE_DEVICE,
                CONF_CPU_ID: cpu_id,
                CONF_HOST: discovery_info[CONF_HOST],
                CONF_HUB_ID: discovery_info.get(CONF_HUB_ID),
                CONF_DEVICE_TYPE: discovery_info[CONF_DEVICE_TYPE],
            }
        )
        host = discovery_info[CONF_HOST]
        if self._async_in_progress(match_context={CONF_HOST: host}):
            return self.async_abort(reason="already_in_progress")
        self.context[CONF_HOST] = host
        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm a discovered device."""
        if user_input is not None:
            if self._discovery_info.get(CONF_HUB_ID) is not None:
                return self._async_add_discovered_device_to_hub(user_input)

            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data={
                    CONF_ROLE: ENTRY_ROLE_DEVICE,
                    CONF_CPU_ID: self._discovery_info[CONF_CPU_ID],
                    CONF_HOST: user_input[CONF_HOST],
                    CONF_HUB_ID: self._discovery_info.get(CONF_HUB_ID),
                    CONF_DEVICE_TYPE: user_input[CONF_DEVICE_TYPE],
                },
            )

        return self._show_discovery_form(user_input)

    def _async_add_device_to_hub(
        self, hub_id: str, device_data: dict[str, Any]
    ) -> ConfigFlowResult:
        hub_entry = hub_entry_for_id(self.hass, hub_id)
        if hub_entry is None:
            return self.async_abort(reason="hub_not_found")

        async_update_hub_device(self.hass, hub_entry, device_data)
        return self.async_abort(reason="device_added")

    def _async_add_discovered_device_to_hub(
        self, user_input: dict[str, Any]
    ) -> ConfigFlowResult:
        return self._async_add_device_to_hub(
            self._discovery_info[CONF_HUB_ID],
            {
                CONF_ROLE: ENTRY_ROLE_DEVICE,
                CONF_CPU_ID: self._discovery_info[CONF_CPU_ID],
                CONF_HOST: user_input[CONF_HOST],
                CONF_HUB_ID: self._discovery_info[CONF_HUB_ID],
                CONF_DEVICE_TYPE: user_input[CONF_DEVICE_TYPE],
                CONF_NAME: user_input[CONF_NAME],
            },
        )

    def _show_device_form(self, user_input: dict[str, Any]) -> ConfigFlowResult:
        def default(key: str, default: str | None = None):
            if user_input is not None and user_input.get(key) is not None:
                return user_input[key]
            return default

        schema = {
            vol.Required(
                CONF_DEVICE_TYPE,
                default=default(CONF_DEVICE_TYPE, ARGO_DEVICE_ULISSE_ECO),
            ): vol.In(ARGO_DEVICES),
            vol.Required(CONF_NAME, default=default(CONF_NAME)): str,
            vol.Required(CONF_HOST, default=default(CONF_HOST)): str,
        }
        hub_options = _hub_options(self.hass)
        if hub_options:
            schema[
                vol.Optional(
                    CONF_HUB_ID,
                    default=default(CONF_HUB_ID, NO_HUB_ID),
                )
            ] = vol.In(hub_options)

        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema(schema),
            errors=self._errors,
            description_placeholders={"docs_url": DOCUMENTATION_URL},
        )

    def _show_discovery_form(self, user_input: dict[str, Any]) -> ConfigFlowResult:
        def default(key: str, default: str | None = None):
            if user_input is not None and user_input.get(key) is not None:
                return user_input[key]
            if self._discovery_info.get(key) is not None:
                return self._discovery_info[key]
            return default

        cpu_id = self._discovery_info[CONF_CPU_ID]
        return self.async_show_form(
            step_id="discovery_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_DEVICE_TYPE,
                        default=default(CONF_DEVICE_TYPE, ARGO_DEVICE_ULISSE_ECO),
                    ): vol.In(ARGO_DEVICES),
                    vol.Required(
                        CONF_NAME,
                        default=default(CONF_NAME, f"Argoclima {cpu_id[-6:]}"),
                    ): str,
                    vol.Required(CONF_HOST, default=default(CONF_HOST)): str,
                }
            ),
            errors=self._errors,
        )


class ArgoOptionsFlowHandler(OptionsFlow):
    def __init__(self) -> None:
        self._errors: dict[str, str] = {}
        self.data: dict[str, Any] = {}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        self.data = dict(self.config_entry.data)
        return await self.async_step_user(user_input)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        if async_entry_role(self.config_entry) == ENTRY_ROLE_HUB:
            return await self.async_step_server(user_input)

        if user_input is not None:
            device_type = ArgoDeviceType.from_name(self.data.get(CONF_DEVICE_TYPE))
            host_ok = await async_test_host(
                self.hass, device_type, user_input[CONF_HOST]
            )
            if host_ok:
                self.data.update({CONF_HOST: user_input[CONF_HOST]})
                if hub_id := _selected_hub_id(user_input):
                    self.data[CONF_HUB_ID] = hub_id
                else:
                    self.data.pop(CONF_HUB_ID, None)
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data=self.data,
                )
                return self.async_create_entry(title="", data={})
            self._errors["base"] = "host"

        return self._async_show_option_form(user_input)

    def _async_show_option_form(self, user_input: dict[str, Any]) -> ConfigFlowResult:
        def default(key: str):
            if user_input is not None and (
                user_input.get(key) is not None and len(user_input[key]) > 0
            ):
                return user_input[key]
            return self.data.get(key)

        schema = {
            vol.Required(CONF_HOST, default=default(CONF_HOST)): str,
        }
        hub_options = _hub_options(self.hass)
        if hub_options:
            schema[
                vol.Optional(
                    CONF_HUB_ID,
                    default=default(CONF_HUB_ID) or NO_HUB_ID,
                )
            ] = vol.In(hub_options)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(schema),
            errors=self._errors,
            description_placeholders={"docs_url": DOCUMENTATION_URL},
        )

    async def async_step_server(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle server options."""
        self._errors = {}

        if user_input is not None:
            port = user_input[CONF_PORT]
            self._errors = await _async_validate_server_input(
                self.hass, user_input, self.config_entry
            )
            if self._errors:
                return self._show_server_form(user_input)

            self.data = _server_data(
                {**self.data, CONF_ROLE: ENTRY_ROLE_HUB}, user_input
            )
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data=self.data,
                title=_server_title(port),
                unique_id=dummy_server_unique_id(port),
            )
            return self.async_create_entry(title="", data={})

        return self._show_server_form(self.data)

    def _show_server_form(self, user_input: dict[str, Any]) -> ConfigFlowResult:
        return self.async_show_form(
            step_id="server",
            data_schema=_server_schema(user_input),
            errors=self._errors,
        )


def _server_port_exists(
    hass: HomeAssistant, port: int, exclude_entry_id: str | None = None
) -> bool:
    return any(
        async_entry_role(entry) == ENTRY_ROLE_HUB
        and entry.entry_id != exclude_entry_id
        and entry.data.get(CONF_PORT, DUMMY_SERVER_DEFAULT_PORT) == port
        for entry in hass.config_entries.async_entries(DOMAIN)
    )


def _server_title(port: int) -> str:
    return f"{DUMMY_SERVER_TITLE} ({port})"


def _hub_options(hass: HomeAssistant) -> dict[str, str]:
    options = {
        dummy_server_hub_id(entry): entry.title
        for entry in hass.config_entries.async_entries(DOMAIN)
        if async_entry_role(entry) == ENTRY_ROLE_HUB
    }
    if not options:
        return {}
    return {NO_HUB_ID: "No dummy server hub", **options}


def _selected_hub_id(user_input: dict[str, Any]) -> str | None:
    hub_id = user_input.get(CONF_HUB_ID)
    if hub_id in (None, NO_HUB_ID):
        return None
    return hub_id


def _server_schema(user_input: dict[str, Any] | None) -> vol.Schema:
    user_input = user_input or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_PORT, default=user_input.get(CONF_PORT, DUMMY_SERVER_DEFAULT_PORT)
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
            vol.Optional(
                CONF_NAT_GATEWAY,
                description={"suggested_value": user_input.get(CONF_NAT_GATEWAY)},
            ): str,
        }
    )


async def _async_validate_server_input(
    hass: HomeAssistant, user_input: dict[str, Any], entry: ConfigEntry | None = None
) -> dict[str, str]:
    port = user_input[CONF_PORT]
    if _server_port_exists(hass, port, entry.entry_id if entry else None):
        return {"base": "port_in_use"}
    port_changed = entry is None or entry.data.get(CONF_PORT) != port
    if port_changed and not await _async_port_available(port):
        return {"base": "port_unavailable"}
    if nat_gateway := user_input.get(CONF_NAT_GATEWAY, "").strip():
        try:
            ip_address(nat_gateway)
        except ValueError:
            return {CONF_NAT_GATEWAY: "invalid_ip"}
    return {}


async def _async_port_available(port: int) -> bool:
    try:
        server = await asyncio.start_server(
            lambda reader, writer: writer.close(), DUMMY_SERVER_BIND_HOST, port
        )
    except OSError:
        return False
    server.close()
    await server.wait_closed()
    return True


def _server_data(data: dict[str, Any], user_input: dict[str, Any]) -> dict[str, Any]:
    data = {**data, CONF_PORT: user_input[CONF_PORT]}
    if nat_gateway := user_input.get(CONF_NAT_GATEWAY, "").strip():
        data[CONF_NAT_GATEWAY] = nat_gateway
    else:
        data.pop(CONF_NAT_GATEWAY, None)
    return data
