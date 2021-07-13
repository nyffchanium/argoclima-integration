from typing import Any
from typing import Dict

import voluptuous as vol
from custom_components.argoclima.api import ArgoApiClient
from custom_components.argoclima.const import ARGO_DEVICE_ULISSE_ECO
from custom_components.argoclima.const import ARGO_DEVICES
from custom_components.argoclima.const import CONF_DEVICE_TYPE
from custom_components.argoclima.const import CONF_HOST
from custom_components.argoclima.const import CONF_NAME
from custom_components.argoclima.const import DOMAIN
from custom_components.argoclima.data import ArgoData
from custom_components.argoclima.device_type import ArgoDeviceType
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_create_clientsession


async def async_test_host(hass: HomeAssistant, type: ArgoDeviceType, host: str):
    """Return true if host seems to be a supported device."""
    try:
        session = async_create_clientsession(hass)
        client = ArgoApiClient(type, host, session)
        result = await client.async_sync_data(ArgoData(type))
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

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> "ArgoOptionsFlowHandler":
        return ArgoOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input: Dict[str, Any] = None) -> FlowResult:
        """Handle a flow initialized by the user."""
        self._errors = {}

        if user_input is not None:
            type = ArgoDeviceType.from_name(user_input[CONF_DEVICE_TYPE])
            if type is not None:
                hostOk = await async_test_host(self.hass, type, user_input[CONF_HOST])
                if hostOk:
                    return self.async_create_entry(
                        title=user_input[CONF_NAME],
                        data={
                            CONF_DEVICE_TYPE: user_input[CONF_DEVICE_TYPE],
                            CONF_HOST: user_input[CONF_HOST],
                        },
                    )
                else:
                    self._errors["base"] = "host"
            else:
                self._errors["base"] = "invalid_device_type"

        return self._show_config_form(user_input)

    def _show_config_form(self, user_input: Dict[str, Any]) -> FlowResult:
        def default(key: str, default: str = None):
            if user_input is not None and user_input[key] is not None:
                return user_input[key]
            return default

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_DEVICE_TYPE,
                        default=default(CONF_DEVICE_TYPE, ARGO_DEVICE_ULISSE_ECO),
                    ): vol.In(ARGO_DEVICES),
                    vol.Required(CONF_NAME, default=default(CONF_NAME)): str,
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
        self.config_entry = config_entry
        self.data = dict(config_entry.data)

    async def async_step_init(self, user_input: Dict[str, Any] = None) -> FlowResult:
        """Manage the options."""
        return await self.async_step_user(user_input)

    async def async_step_user(self, user_input: Dict[str, Any] = None) -> FlowResult:
        """Handle a flow initialized by the user."""
        if user_input is not None:
            type = ArgoDeviceType.from_name(self.data.get(CONF_DEVICE_TYPE))
            hostOk = await async_test_host(self.hass, type, user_input[CONF_HOST])
            if hostOk:
                self.data.update({CONF_HOST: user_input[CONF_HOST]})
                return self.async_create_entry(title="", data=self.data)
            else:
                self._errors["base"] = "host"

        return self._async_show_option_form(user_input)

    def _async_show_option_form(self, user_input: Dict[str, Any]) -> FlowResult:
        def default(key: str):
            if user_input is not None and (
                user_input[key] is not None and len(user_input[key]) > 0
            ):
                return user_input[key]
            return self.data.get(key)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=default(CONF_HOST)): str,
                }
            ),
            errors=self._errors,
        )
