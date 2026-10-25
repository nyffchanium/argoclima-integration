import shutil
from datetime import timedelta
from pathlib import Path

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.automation.config import AUTOMATION_BLUEPRINT_SCHEMA
from homeassistant.components.blueprint.models import Blueprint
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util.yaml import load_yaml
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.common import async_capture_events
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from .helpers import sent_value
from .helpers import setup_integration

BLUEPRINTS = Path(__file__).parents[1] / "blueprints" / "automation" / "argoclima"
CLIMATE = "climate.living_room"
OPERATING = 2


@pytest.mark.parametrize(
    "path", sorted(BLUEPRINTS.glob("*.yaml")), ids=lambda path: path.stem
)
def test_blueprint_is_valid(path: Path) -> None:
    blueprint = Blueprint(
        load_yaml(path),
        expected_domain="automation",
        schema=AUTOMATION_BLUEPRINT_SCHEMA,
    )
    assert blueprint.metadata["source_url"].endswith(
        f"/blob/master/blueprints/automation/argoclima/{path.name}"
    )


@pytest.fixture
async def use_blueprint(hass: HomeAssistant, tmp_path: Path):
    hass.config.config_dir = str(tmp_path)
    shutil.copytree(BLUEPRINTS, tmp_path / "blueprints" / "automation" / "argoclima")

    async def setup(name: str, inputs: dict) -> None:
        assert await async_setup_component(
            hass,
            "automation",
            {
                "automation": {
                    "use_blueprint": {
                        "path": f"argoclima/{name}.yaml",
                        "input": inputs,
                    }
                }
            },
        )
        await hass.async_block_till_done()

    return setup


async def advance(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, delta: timedelta
) -> None:
    freezer.tick(delta)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def test_window_open(
    hass: HomeAssistant,
    mock_device: None,
    device_entry: MockConfigEntry,
    sent_requests: list[str],
    freezer: FrozenDateTimeFactory,
    use_blueprint,
) -> None:
    await setup_integration(hass, device_entry)
    assert await async_setup_component(hass, "scene", {})
    hass.states.async_set("binary_sensor.window", "off")
    await use_blueprint(
        "window_open", {"climate": CLIMATE, "window": "binary_sensor.window"}
    )

    hass.states.async_set("binary_sensor.window", "on")
    await advance(hass, freezer, timedelta(minutes=1, seconds=1))
    assert sent_value(sent_requests, OPERATING) == "0"

    hass.states.async_set("binary_sensor.window", "off")
    await advance(hass, freezer, timedelta(seconds=31))
    assert sent_value(sent_requests, OPERATING) == "1"


async def test_away(
    hass: HomeAssistant,
    mock_device: None,
    device_entry: MockConfigEntry,
    sent_requests: list[str],
    freezer: FrozenDateTimeFactory,
    use_blueprint,
) -> None:
    await setup_integration(hass, device_entry)
    hass.states.async_set("zone.home", "1")
    await use_blueprint("away", {"climate": [CLIMATE]})

    hass.states.async_set("zone.home", "0")
    await advance(hass, freezer, timedelta(minutes=15, seconds=1))

    assert sent_value(sent_requests, OPERATING) == "0"


@pytest.mark.parametrize("device_state", [{OPERATING: 0}])
async def test_window_open_while_off_does_not_turn_on(
    hass: HomeAssistant,
    mock_device: None,
    device_entry: MockConfigEntry,
    sent_requests: list[str],
    freezer: FrozenDateTimeFactory,
    use_blueprint,
) -> None:
    await setup_integration(hass, device_entry)
    assert await async_setup_component(hass, "scene", {})
    hass.states.async_set("binary_sensor.window", "off")
    await use_blueprint(
        "window_open", {"climate": CLIMATE, "window": "binary_sensor.window"}
    )

    hass.states.async_set("binary_sensor.window", "on")
    await advance(hass, freezer, timedelta(minutes=1, seconds=1))
    hass.states.async_set("binary_sensor.window", "off")
    await advance(hass, freezer, timedelta(seconds=31))

    assert all(request.split(",")[OPERATING] != "1" for request in sent_requests)


@pytest.mark.parametrize(("remote_switch", "notified"), [("on", 1), ("off", 0)])
async def test_remote_out_of_sight(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    use_blueprint,
    remote_switch: str,
    notified: int,
) -> None:
    events = async_capture_events(hass, "remote_out_of_sight_test")
    hass.states.async_set("sensor.source", "remote")
    hass.states.async_set("switch.use_remote", remote_switch)
    await use_blueprint(
        "remote_out_of_sight",
        {
            "temperature_source": "sensor.source",
            "use_remote_temperature": "switch.use_remote",
            "notify": [{"event": "remote_out_of_sight_test"}],
        },
    )

    hass.states.async_set("sensor.source", "device")
    await advance(hass, freezer, timedelta(minutes=1, seconds=1))

    assert len(events) == notified
