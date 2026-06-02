from typing import Any

import voluptuous as vol
from custom_components.argoclima.api import ArgoApiClient
from custom_components.argoclima.const import ARGO_DEVICE_ULISSE_ECO
from custom_components.argoclima.const import ARGO_DEVICES
from custom_components.argoclima.const import CONF_DEVICE_TYPE
from custom_components.argoclima.const import CONF_CPU_ID
from custom_components.argoclima.const import CONF_HUB_ID
from custom_components.argoclima.const import CONF_HOST
from custom_components.argoclima.const import CONF_NAME
from custom_components.argoclima.const import CONF_PORT
from custom_components.argoclima.const import CONF_ROLE
from custom_components.argoclima.const import DOMAIN
from custom_components.argoclima.const import DUMMY_SERVER_DEFAULT_PORT
from custom_components.argoclima.const import DUMMY_SERVER_TITLE
from custom_components.argoclima.const import ENTRY_ROLE_DEVICE
from custom_components.argoclima.const import ENTRY_ROLE_HUB
from custom_components.argoclima.data import ArgoData
from custom_components.argoclima.device_type import ArgoDeviceType
from custom_components.argoclima.dummy_server import async_entry_role
from custom_components.argoclima.dummy_server import dummy_server_hub_id
from custom_components.argoclima.dummy_server import dummy_server_unique_id
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_create_clientsession

NO_HUB_ID = "__no_hub__"


async def async_test_host(
    hass: HomeAssistant, device_type: ArgoDeviceType, host: str
) -> bool:
    """Return true if host seems to be a supported device."""
    try:
        session = async_create_clientsession(hass)
        client = ArgoApiClient(device_type, host, session)
        result = await client.async_sync_data(ArgoData(device_type))
        return result is not None
    except Exception:  # pylint: disable=broad-except
        pass
    return False


class ArgoFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        """Initialize."""
        super().__init__()
        self._errors = {}
        self._discovery_info: dict[str, Any] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> "ArgoOptionsFlowHandler":
        return ArgoOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input: dict[str, Any] = None) -> FlowResult:
        """Handle a flow initialized by the user."""
        return self.async_show_menu(
            step_id="user",
            menu_options=["server", "device"],
        )

    async def async_step_server(self, user_input: dict[str, Any] = None) -> FlowResult:
        """Create the dummy server entry."""
        self._errors = {}

        if user_input is not None:
            port = user_input[CONF_PORT]
            if _server_port_exists(self.hass, port):
                self._errors["base"] = "port_in_use"
                return self._show_server_form(user_input)

            await self.async_set_unique_id(dummy_server_unique_id(port))
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=_server_title(port),
                data={
                    CONF_ROLE: ENTRY_ROLE_HUB,
                    CONF_PORT: port,
                },
            )

        return self._show_server_form(user_input)

    def _show_server_form(self, user_input: dict[str, Any]) -> FlowResult:
        return self.async_show_form(
            step_id="server",
            data_schema=_server_schema(user_input),
            errors=self._errors,
        )

    async def async_step_device(self, user_input: dict[str, Any] = None) -> FlowResult:
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
                        data[CONF_HUB_ID] = hub_id
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
    ) -> FlowResult:
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
        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] = None
    ) -> FlowResult:
        """Confirm a discovered device."""
        if user_input is not None:
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

    def _show_device_form(self, user_input: dict[str, Any]) -> FlowResult:
        def default(key: str, default: str = None):
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
        )

    def _show_discovery_form(self, user_input: dict[str, Any]) -> FlowResult:
        def default(key: str, default: str = None):
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


class ArgoOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize HACS options flow."""
        super().__init__()
        self._errors = {}
        self._config_entry = config_entry
        self.data = dict(config_entry.data)

    async def async_step_init(self, user_input: dict[str, Any] = None) -> FlowResult:
        """Manage the options."""
        return await self.async_step_user(user_input)

    async def async_step_user(self, user_input: dict[str, Any] = None) -> FlowResult:
        """Handle a flow initialized by the user."""
        if async_entry_role(self._config_entry) == ENTRY_ROLE_HUB:
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
                    self._config_entry,
                    data=self.data,
                )
                return self.async_create_entry(title="", data={})
            self._errors["base"] = "host"

        return self._async_show_option_form(user_input)

    def _async_show_option_form(self, user_input: dict[str, Any]) -> FlowResult:
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
        )

    async def async_step_server(self, user_input: dict[str, Any] = None) -> FlowResult:
        """Handle server options."""
        self._errors = {}

        if user_input is not None:
            port = user_input[CONF_PORT]
            if _server_port_exists(self.hass, port, self._config_entry.entry_id):
                self._errors["base"] = "port_in_use"
                return self._show_server_form()

            self.data.update(
                {
                    CONF_ROLE: ENTRY_ROLE_HUB,
                    CONF_PORT: port,
                }
            )
            self.hass.config_entries.async_update_entry(
                self._config_entry,
                data=self.data,
                title=_server_title(port),
                unique_id=dummy_server_unique_id(port),
            )
            return self.async_create_entry(title="", data={})

        return self._show_server_form()

    def _show_server_form(self) -> FlowResult:
        return self.async_show_form(
            step_id="server",
            data_schema=_server_schema(self.data),
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
    port = DUMMY_SERVER_DEFAULT_PORT
    if user_input is not None and user_input.get(CONF_PORT) is not None:
        port = user_input[CONF_PORT]

    return vol.Schema(
        {
            vol.Required(CONF_PORT, default=port): vol.All(
                vol.Coerce(int),
                vol.Range(min=1, max=65535),
            ),
        }
    )
