"""Home-Assistant-free unit normalization and output-step safety tests."""
import pytest
from custom_components.power_manager.device_units import (
    convert_power_unit, quantize_down,
)

@pytest.mark.parametrize("internal_kw,unit,value", [
    (5,"W",5000),
    (5,"kW",5),
    (5,"MW",0.005),
    (11,"W",11000),
    (1,"W",1000),
])
def test_internal_kw_translates_into_device_unit(internal_kw,unit,value):
    assert convert_power_unit(internal_kw,"kW",unit) == pytest.approx(value)


@pytest.mark.parametrize("command,unit,expected", [
    (5000, "W", 5),
    (11000, "W", 11),
    (1000, "W", 1),
])
def test_watt_command_translates_to_kw_entity(command,unit,expected):
    device_kw=convert_power_unit(command,unit,"kW")
    assert quantize_down(device_kw,minimum=0,maximum=20,step=0.1) == expected


def test_runtime_96685_watt_mismatch_case_is_safely_quantized():
    assert quantize_down(9.6685, minimum=0, maximum=11,step=0.1) == 9.6


@pytest.mark.parametrize("target,expected", [
    (4.14,4.0),(4.99,4.0),(5,5),(6.9,6.0),(11,11.0),
])
def test_1000_w_steps_round_down(target,expected):
    command=convert_power_unit(target,"kW","W")
    native=quantize_down(command,minimum=0,maximum=11000,step=1000)
    assert convert_power_unit(native,"W","kW")==expected


def test_minimum_power_gate_requires_physical_minimum_after_quantization():
    candidate=quantize_down(4.99,minimum=0,maximum=11,step=1)
    assert candidate == 4
    assert candidate < 3*230*6/1000  # must pause, never round to 5


def test_no_risky_rounding_for_negative_or_out_of_range_commands():
    with pytest.raises(ValueError):
        quantize_down(11000,minimum=0,maximum=11,step=0.1)
    with pytest.raises(ValueError):
        quantize_down(float("nan"),minimum=0,maximum=11,step=0.1)
    with pytest.raises(ValueError):
        quantize_down(11.2,minimum=0,maximum=11,step=0.1)


def test_step_grid_is_based_on_entity_minimum_not_on_zero():
    assert quantize_down(6.93,minimum=0.05,maximum=11.05,step=0.1)==6.85


def test_unitless_and_ampere_cannot_be_reinterpreted_as_power():
    for unit in ("A","device","%",""):
        with pytest.raises(ValueError):
            convert_power_unit(7,unit,"kW")
