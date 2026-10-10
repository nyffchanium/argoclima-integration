from datetime import datetime
from datetime import timedelta
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.core import callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .entity import ArgoEntity
from .runtime import ArgoRuntimeDevice
from .runtime import runtime_devices_for_entry

CONNECTION_TIMEOUT = timedelta(seconds=60)
CONNECTION_CHECK_INTERVAL = timedelta(seconds=15)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities(
        ArgoConnectionSensor(device)
        for device in runtime_devices_for_entry(hass, entry)
    )


class ArgoConnectionSensor(ArgoEntity, BinarySensorEntity):
    """Whether the device communicated recently."""

    # Changes with every report; keep it out of the database.
    _unrecorded_attributes = frozenset({"last_seen"})

    def __init__(self, device: ArgoRuntimeDevice) -> None:
        super().__init__(
            "Connection",
            device,
            BinarySensorDeviceClass.CONNECTIVITY,
            EntityCategory.DIAGNOSTIC,
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        # Without reports, nothing else would update the state.
        self.async_on_remove(
            async_track_time_interval(
                self.hass, self._async_check_connection, CONNECTION_CHECK_INTERVAL
            )
        )

    @callback
    def _async_check_connection(self, _now: datetime) -> None:
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        return True

    @property
    def is_on(self) -> bool:
        last_seen = self.coordinator.last_seen
        return (
            last_seen is not None and dt_util.utcnow() - last_seen < CONNECTION_TIMEOUT
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        last_seen = self.coordinator.last_seen
        return {"last_seen": last_seen.isoformat() if last_seen else None}
