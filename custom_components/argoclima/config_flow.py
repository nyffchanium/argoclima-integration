"""Adds config flow for Blueprint."""
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_create_clientsession
import voluptuous as vol

from .api import ArgoApiClient
from .const import (
    ARGO_DEVICES,
    ARGO_DEVICE_ULISSE_ECO,
    CONF_DEVICE_TYPE,
    CONF_HOST,
    CONF_NAME,
    DOMAIN,
)


class ArgoFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        """Initialize."""
        self._errors = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return ArgoOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        self._errors = {}

        if user_input is not None:
            result = await self._test_host(
                user_input[CONF_HOST],
            )
            if result:
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )
            else:
                self._errors["base"] = "host"

            return await self._show_config_form(user_input)

        return await self._show_config_form(user_input)

    async def _show_config_form(self, user_input):  # pylint: disable=unused-argument
        def default(key: str, default=None):
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

    async def _test_host(self, host):
        """Return true if credentials is valid."""
        try:
            session = async_create_clientsession(self.hass)
            client = ArgoApiClient(host, session)
            await client.async_call_api()
            return True
        except Exception:  # pylint: disable=broad-except
            pass
        return False


class ArgoOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        """Initialize HACS options flow."""
        self.config_entry = config_entry
        self.options = dict(config_entry.options)

    async def async_step_init(self, user_input=None):  # pylint: disable=unused-argument
        """Manage the options."""
        return await self.async_step_user(user_input)

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        # if user_input is not None:
        #     self.options.update(user_input)
        #     return await self._update_options()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),
        )

    # async def _update_options(self):
    #     """Update config entry options."""
    #     return self.async_create_entry(
    #         title=self.config_entry.data.get(CONF_USERNAME), data=self.options
    #     )
