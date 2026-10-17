from datetime import timedelta

from homeassistant.components.number import NumberEntity
from homeassistant.components.number import NumberMode
from homeassistant.components.number import RestoreNumber
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DELAY_TIMER_MAX_MINUTES
from .const import DELAY_TIMER_MIN_MINUTES
from .const import DELAY_TIMER_STEP_MINUTES
from .entity import ArgoAntiMoldEntity
from .entity import ArgoEntity
from .entity import ArgoSettingEntity
from .runtime import ArgoRuntimeDevice
from .runtime import runtime_devices_for_entry
from .types import ArgoTimerType


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    entities: list[NumberEntity] = []
    for device in runtime_devices_for_entry(hass, entry):
        if device.type.eco_limit:
            entities.append(ArgoEcoLimitNumber(device))
        if device.type.anti_mold:
            entities.append(ArgoAntiMoldDurationNumber(device))
        if ArgoTimerType.DELAY_ON_OFF in device.type.timers:
            entities.append(ArgoDelayTimerNumber(device))
    async_add_entities(entities)


class ArgoEcoLimitNumber(ArgoEntity, NumberEntity):
    _attr_icon = "mdi:leaf"
    _attr_mode = NumberMode.BOX
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, device: ArgoRuntimeDevice) -> None:
        super().__init__("Eco Mode Power Limit", device, None, EntityCategory.CONFIG)
        self._attr_native_min_value = device.type.eco_limit_min
        self._attr_native_max_value = device.type.eco_limit_max

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.eco_limit

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.data.eco_limit = int(value)
        await self._async_send_changes()


class ArgoAntiMoldDurationNumber(ArgoAntiMoldEntity, RestoreNumber):
    _attr_icon = "mdi:timer-outline"
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 1
    _attr_native_max_value = 120
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES

    def __init__(self, device: ArgoRuntimeDevice) -> None:
        super().__init__("Anti Mold Duration", device)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (data := await self.async_get_last_number_data()) is not None and (
            data.native_value is not None
        ):
            self._anti_mold.duration = timedelta(minutes=data.native_value)

    @property
    def native_value(self) -> float:
        return self._anti_mold.duration.total_seconds() / 60

    async def async_set_native_value(self, value: float) -> None:
        self._anti_mold.duration = timedelta(minutes=value)
        self.async_write_ha_state()


class ArgoDelayTimerNumber(ArgoSettingEntity, RestoreNumber):
    """Duration of the delay timer, sent when the delay timer is activated."""

    _attr_icon = "mdi:timer-sand"
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = DELAY_TIMER_MIN_MINUTES
    _attr_native_max_value = DELAY_TIMER_MAX_MINUTES
    _attr_native_step = DELAY_TIMER_STEP_MINUTES
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES

    def __init__(self, device: ArgoRuntimeDevice) -> None:
        super().__init__("Delay Timer Duration", device)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (data := await self.async_get_last_number_data()) is not None and (
            data.native_value is not None
        ):
            self.coordinator.delay_timer_minutes = int(data.native_value)

    @property
    def native_value(self) -> int:
        return self.coordinator.delay_timer_minutes

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.delay_timer_minutes = int(value)
        data = self.coordinator.data
        if data.timer is ArgoTimerType.DELAY_ON_OFF:
            data.set_delay_timer_minutes(int(value))
            await self._async_send_changes()
        else:
            self.async_write_ha_state()
