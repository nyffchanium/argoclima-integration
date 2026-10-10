from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_CPU_ID
from .const import CONF_DEVICES
from .const import CONF_HOST
from .const import CONF_NAT_GATEWAY
from .const import DOMAIN
from .runtime import ArgoHubRuntime
from .runtime import runtime_devices_for_entry

TO_REDACT = {CONF_HOST, CONF_CPU_ID, CONF_NAT_GATEWAY, "unique_id"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    data = dict(entry.data)
    if CONF_DEVICES in data:
        data[CONF_DEVICES] = [
            async_redact_data(device, TO_REDACT)
            for device in data[CONF_DEVICES].values()
        ]

    runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    return {
        "entry": async_redact_data(
            {"title": entry.title, "version": entry.version, "data": data},
            TO_REDACT,
        ),
        "dummy_server": {
            "running": runtime.server.running,
            "connections": runtime.server.connection_count,
        }
        if isinstance(runtime, ArgoHubRuntime)
        else None,
        "devices": [
            {
                "type": device.type.name,
                "push_updates": device.coordinator.update_interval is None,
                "last_update_success": device.coordinator.last_update_success,
                "state": device.coordinator.data.as_dict()
                if device.coordinator.data
                else None,
            }
            for device in runtime_devices_for_entry(hass, entry)
        ],
    }
