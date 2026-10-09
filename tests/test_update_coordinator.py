import pytest
from homeassistant.core import HomeAssistant

from custom_components.argoclima.data import ArgoData
from custom_components.argoclima.device_type import ULISSE_ECO
from custom_components.argoclima.update_coordinator import ArgoDataUpdateCoordinator


class FakeClient:
    def __init__(self, results: list) -> None:
        self._results = results

    async def async_sync_data(self, data: ArgoData) -> ArgoData:
        result = self._results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def coordinator(hass: HomeAssistant, results: list) -> ArgoDataUpdateCoordinator:
    return ArgoDataUpdateCoordinator(hass, FakeClient(results), ULISSE_ECO)


async def test_keeps_last_state_on_first_failures(hass: HomeAssistant) -> None:
    coord = coordinator(hass, [TimeoutError(), TimeoutError()])
    last_known = coord.data

    assert await coord._async_update() is last_known
    assert await coord._async_update() is last_known


async def test_raises_after_repeated_failures(hass: HomeAssistant) -> None:
    coord = coordinator(hass, [TimeoutError(), TimeoutError(), TimeoutError()])

    await coord._async_update()
    await coord._async_update()
    with pytest.raises(TimeoutError):
        await coord._async_update()


async def test_success_resets_failure_count(hass: HomeAssistant) -> None:
    recovered = ArgoData(ULISSE_ECO)
    coord = coordinator(
        hass,
        [TimeoutError(), TimeoutError(), recovered, TimeoutError(), TimeoutError()],
    )

    await coord._async_update()
    await coord._async_update()
    assert await coord._async_update() is recovered
    await coord._async_update()
    await coord._async_update()


async def test_push_updates_pause_polling(hass: HomeAssistant) -> None:
    coord = coordinator(hass, [])
    assert coord.update_interval is not None

    coord.async_set_push_updates_enabled(True)
    assert coord.update_interval is None

    coord.async_set_push_updates_enabled(False)
    assert coord.update_interval.total_seconds() == ULISSE_ECO.update_interval
