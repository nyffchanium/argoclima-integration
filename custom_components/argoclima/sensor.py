from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor import SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import ArgoEntity
from .runtime import ArgoRuntimeDevice
from .runtime import runtime_devices_for_entry


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities(
        ArgoTemperatureSensor(device)
        for device in runtime_devices_for_entry(hass, entry)
        if device.type.current_temperature
    )


class ArgoTemperatureSensor(ArgoEntity, SensorEntity):
    """Room temperature measured by the device, or by the remote if enabled."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_suggested_display_precision = 1

    def __init__(self, device: ArgoRuntimeDevice) -> None:
        super().__init__("Temperature", device, SensorDeviceClass.TEMPERATURE)

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.temp
