from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .entity import ArgoAntiMoldEntity
from .entity import ArgoEntity
from .runtime import ArgoRuntimeDevice
from .runtime import runtime_devices_for_entry
from .types import ArgoFanSpeed
from .types import ArgoTimerType
from .types import ArgoUnit


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    entities = []
    for device in runtime_devices_for_entry(hass, entry):
        if device.type.unit:
            entities.append(ArgoUnitSelect(device))
        if device.type.timer:
            entities.append(ArgoTimerSelect(device))
        if device.type.anti_mold:
            entities.append(ArgoAntiMoldFanSpeedSelect(device))
    async_add_entities(entities)


class ArgoUnitSelect(ArgoEntity, SelectEntity):
    _attr_options = [unit.to_ha_unit() for unit in ArgoUnit]

    def __init__(self, device: ArgoRuntimeDevice) -> None:
        super().__init__("Display Unit", device, None, EntityCategory.CONFIG)

    @property
    def current_option(self) -> str | None:
        unit = self.coordinator.data.unit
        return unit.to_ha_unit() if unit is not None else None

    async def async_select_option(self, option: str) -> None:
        self.coordinator.data.unit = ArgoUnit.from_ha_unit(option)
        await self._async_send_changes()


class ArgoTimerSelect(ArgoEntity, SelectEntity):
    def __init__(self, device: ArgoRuntimeDevice) -> None:
        super().__init__("Active Timer", device, None, EntityCategory.CONFIG)
        self._attr_options = [str(timer) for timer in device.type.timers]

    @property
    def current_option(self) -> str | None:
        timer = self.coordinator.data.timer
        return str(timer) if timer is not None else None

    async def async_select_option(self, option: str) -> None:
        self.coordinator.data.timer = ArgoTimerType[option.upper()]
        await self._async_send_changes()


class ArgoAntiMoldFanSpeedSelect(ArgoAntiMoldEntity, SelectEntity, RestoreEntity):
    _attr_icon = "mdi:fan"

    def __init__(self, device: ArgoRuntimeDevice) -> None:
        super().__init__("Anti Mold Fan Speed", device)
        self._attr_options = [
            speed.to_ha_string()
            for speed in device.type.fan_speeds
            if speed is not ArgoFanSpeed.AUTO
        ]

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if state is not None and state.state in self.options:
            self._anti_mold.fan_speed = ArgoFanSpeed.from_ha_string(state.state)

    @property
    def current_option(self) -> str:
        return self._anti_mold.fan_speed.to_ha_string()

    async def async_select_option(self, option: str) -> None:
        self._anti_mold.fan_speed = ArgoFanSpeed.from_ha_string(option)
        self.async_write_ha_state()
