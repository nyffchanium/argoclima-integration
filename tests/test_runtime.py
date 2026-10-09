from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.argoclima.const import CONF_CPU_ID
from custom_components.argoclima.const import CONF_DEVICES
from custom_components.argoclima.const import CONF_HOST
from custom_components.argoclima.const import CONF_NAME
from custom_components.argoclima.const import CONF_PORT
from custom_components.argoclima.const import CONF_ROLE
from custom_components.argoclima.const import DOMAIN
from custom_components.argoclima.const import ENTRY_ROLE_HUB
from custom_components.argoclima.runtime import async_update_hub_device
from custom_components.argoclima.runtime import match_hub_device_id


def hub_entry(hass: HomeAssistant, devices: dict | None = None) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_ROLE: ENTRY_ROLE_HUB, CONF_PORT: 8080, CONF_DEVICES: devices or {}},
    )
    entry.add_to_hass(hass)
    return entry


def test_match_prefers_cpu_id() -> None:
    devices = {"a": {CONF_CPU_ID: "ABC123", CONF_HOST: "10.0.0.5"}}

    assert match_hub_device_id(devices, "ABC123", "10.0.0.9") == "a"


def test_match_by_host_only_for_unidentified_device() -> None:
    assert (
        match_hub_device_id({"a": {CONF_HOST: "10.0.0.5"}}, "ABC123", "10.0.0.5") == "a"
    )
    assert (
        match_hub_device_id(
            {"a": {CONF_CPU_ID: "DEF456", CONF_HOST: "10.0.0.5"}}, "ABC123", "10.0.0.5"
        )
        is None
    )


async def test_device_keeps_its_key_once_identified(hass: HomeAssistant) -> None:
    entry = hub_entry(hass)

    key = async_update_hub_device(
        hass, entry, {CONF_HOST: "10.0.0.5", CONF_NAME: "Living Room"}
    )
    assert (
        async_update_hub_device(
            hass, entry, {CONF_HOST: "10.0.0.5", CONF_CPU_ID: "ABC123"}
        )
        == key
    )
    assert (
        async_update_hub_device(
            hass, entry, {CONF_HOST: "10.0.0.6", CONF_CPU_ID: "ABC123"}
        )
        == key
    )

    assert entry.data[CONF_DEVICES] == {
        key: {CONF_HOST: "10.0.0.6", CONF_NAME: "Living Room", CONF_CPU_ID: "ABC123"}
    }


async def test_new_device_gets_its_own_key(hass: HomeAssistant) -> None:
    entry = hub_entry(hass)

    first = async_update_hub_device(hass, entry, {CONF_HOST: "10.0.0.5"})
    second = async_update_hub_device(hass, entry, {CONF_HOST: "10.0.0.6"})

    assert first != second
    assert len(entry.data[CONF_DEVICES]) == 2


async def test_stale_record_for_same_host_is_replaced(hass: HomeAssistant) -> None:
    entry = hub_entry(hass, {"stale": {CONF_CPU_ID: "OLD", CONF_HOST: "10.0.0.5"}})

    key = async_update_hub_device(
        hass, entry, {CONF_HOST: "10.0.0.5", CONF_CPU_ID: "NEW"}
    )

    assert list(entry.data[CONF_DEVICES]) == [key]
