import pytest

from custom_components.argoclima.const import API_UPDATE_ATTEMPTS
from custom_components.argoclima.data import ArgoData
from custom_components.argoclima.data import InvalidResponseFormatError
from custom_components.argoclima.device_type import ULISSE_ECO
from custom_components.argoclima.types import ArgoFanSpeed
from custom_components.argoclima.types import ArgoOperationMode
from custom_components.argoclima.types import ArgoUnit

from .conftest import device_response


def test_parse_response() -> None:
    data = ArgoData(ULISSE_ECO)
    data.parse_response_parameter_string(device_response())

    assert data.target_temp == 22.0
    assert data.temp == 23.5
    assert data.operating is True
    assert data.mode is ArgoOperationMode.COOL
    assert data.fan is ArgoFanSpeed.AUTO
    assert data.light is True
    assert data.eco_limit == 75
    assert data.firmware_version == 41
    assert data.unit is ArgoUnit.CELSIUS


def test_parse_response_from_device() -> None:
    data = ArgoData(ULISSE_ECO)
    data.parse_response_parameter_string(
        "180,226,0,4,3,0,1,0,0,0,0,0,0,0,101,0,101,0,0,0,0,N,75,1416,0,"
        "N,N,N,N,N,N,N,N,N,N,N,N,N,N"
    )

    assert data.target_temp == 18.0
    assert data.temp == 22.6
    assert data.operating is False
    assert data.mode is ArgoOperationMode.FAN
    assert data.fan is ArgoFanSpeed.MEDIUM
    assert data.remote_temperature is True
    assert data.eco is False
    assert data.light is False
    assert data.eco_limit == 75
    assert data.firmware_version == 1416
    assert data.unit is ArgoUnit.CELSIUS


def test_values_are_none_before_first_response() -> None:
    data = ArgoData(ULISSE_ECO)

    assert data.mode is None
    assert data.fan is None
    assert data.unit is None
    assert data.target_temp is None


def test_rejects_response_with_wrong_length() -> None:
    with pytest.raises(InvalidResponseFormatError):
        ArgoData(ULISSE_ECO).parse_response_parameter_string("1,2,3")


def test_pending_change_is_sent_until_confirmed() -> None:
    data = ArgoData(ULISSE_ECO)
    data.parse_response_parameter_string(device_response())

    data.target_temp = 25
    assert data.is_update_pending()
    assert data.target_temp == 25.0
    assert data.to_parameter_string().split(",")[0] == "250"

    data.parse_response_parameter_string(device_response({0: 250}))
    assert not data.is_update_pending()
    assert data.to_parameter_string().split(",")[0] == "N"


def test_unconfirmed_change_is_given_up() -> None:
    data = ArgoData(ULISSE_ECO)
    data.parse_response_parameter_string(device_response())

    data.light = False
    for _ in range(API_UPDATE_ATTEMPTS):
        data.to_parameter_string()
        data.parse_response_parameter_string(device_response())

    assert not data.is_update_pending()
    assert data.light is True


def test_rejects_out_of_range_value() -> None:
    data = ArgoData(ULISSE_ECO)
    with pytest.raises(ValueError):
        data.target_temp = 40
