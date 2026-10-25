from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor import SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import ArgoEntity
from .runtime import ArgoRuntimeDevice
from .runtime import runtime_devices_for_entry


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    entities: list[SensorEntity] = []
    for device in runtime_devices_for_entry(hass, entry):
        if device.type.current_temperature:
            entities.append(ArgoTemperatureSensor(device))
        if device.type.remote_temperature:
            entities.append(ArgoTemperatureSourceSensor(device))
    async_add_entities(entities)


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


class ArgoTemperatureSourceSensor(ArgoEntity, SensorEntity):
    """Whether the room temperature is measured by the remote or the device."""

    _attr_options = ["remote", "device"]

    def __init__(self, device: ArgoRuntimeDevice) -> None:
        super().__init__(
            "Temperature Source",
            device,
            SensorDeviceClass.ENUM,
            EntityCategory.DIAGNOSTIC,
        )

    @property
    def native_value(self) -> str | None:
        active = self.coordinator.data.remote_temperature_active
        if active is None:
            return None
        return "remote" if active else "device"
