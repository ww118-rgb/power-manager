"""Regression coverage: EVSE A vs W/kW command formats and safe quantization."""
import pytest

from custom_components.power_manager.outputs import (
    OutputConversionError, build_output_plan,
)
from custom_components.power_manager.load_config import (
    normalize_load_data, validate_load_data,
)


def plan(kw, **kwds):
    cfg = {
        "load_type": "evse",
        "target_kw": kw,
        "evse_phases": 3,
        "evse_voltage_v": 230,
        "evse_min_current_a": 6,
        "evse_max_current_a": 16,
        "evse_pause_current_a": 0.01,
        "evse_zero_unlimited": True,
    }
    cfg.update(kwds)
    return build_output_plan(**cfg)


@pytest.mark.parametrize("kw,expected", [
    (0, 0.01), (4.13, 0.01), (4.14, 6),
    (6.0, 8), (6.9, 10), (11.0, 15), (11.04, 16),
])
def test_ampere_whole_step_never_exceeds_budget(kw, expected):
    result = plan(kw, evse_output_format="A", evse_current_step_a=1)
    assert result.numeric_value == pytest.approx(expected)
    assert result.numeric_unit == "A"
    if result.enabled:
        assert result.numeric_value * 3 * 230 / 1000 <= kw + 1e-6


@pytest.mark.parametrize("kw,expected,enabled", [
    (0, 0, False), (4.14, 0, False), (4.99, 0, False),
    (5.0, 5000, True), (5.99, 5000, True),
    (6.0, 6000, True), (6.9, 6000, True),
    (10.99, 10000, True), (11.0, 11000, True),
])
def test_mqtt_style_watts_in_1000_watt_steps(kw, expected, enabled):
    result = plan(kw, evse_output_format="W", evse_power_step_w=1000,
                  evse_pause_power_value=0)
    assert result.numeric_value == pytest.approx(expected)
    assert result.numeric_unit == "W"
    assert result.enabled is enabled
    if result.enabled:
        assert result.numeric_value <= kw * 1000 + 1e-6
        assert result.numeric_value >= 4140


def test_kw_entity_11_kw_out_matches_range_0_to_11():
    value = plan(11, evse_output_format="kW", evse_power_step_w=1000)
    assert value.numeric_value == pytest.approx(11)
    assert value.numeric_unit == "kW"


def test_amperes_nonzero_pause_when_zero_means_unlimited():
    result = plan(0, evse_output_format="A", evse_zero_unlimited=True)
    assert result.numeric_value == pytest.approx(0.01)
    with pytest.raises(OutputConversionError):
        plan(0, evse_output_format="A", evse_zero_unlimited=True,
             evse_pause_current_a=0)


def test_watts_zero_pause_not_affected_by_amperes_unlimited_code():
    result = plan(0, evse_output_format="W", evse_zero_unlimited=True,
                  evse_pause_power_value=0)
    assert result.numeric_value == 0
    assert result.enabled is False


def test_custom_steps_and_devices_are_not_assumed_by_protocol():
    assert plan(6.0, evse_output_format="A",
                evse_current_step_a=2).numeric_value == 8
    assert plan(6.0, evse_output_format="W",
                evse_power_step_w=500).numeric_value == 6000
    assert plan(6.0, evse_output_format="kW",
                evse_power_step_w=2000).numeric_value == 6


@pytest.mark.parametrize("fmt,step", [("A", 0), ("W", -1000), ("kW", 0)])
def test_invalid_steps_fail_closed(fmt, step):
    with pytest.raises(OutputConversionError):
        plan(6, evse_output_format=fmt, **({
            "evse_current_step_a": step} if fmt == "A" else {
            "evse_power_step_w": step}))


def test_legacy_331_load_retains_ampere_format():
    cfg = normalize_load_data({"load_name":"Old","load_type":"evse",
        "priority":1,"min_kw":4.14,"max_kw":11})
    assert cfg["evse_output_format"] == "A"
    assert cfg["evse_current_step_a"] == 1
    assert cfg["evse_power_step_w"] == 1000


def test_auto_format_only_allowed_for_home_assistant_entities():
    cfg = {"load_name":"Car","load_type":"evse", "priority":1,
        "min_kw":4.14, "max_kw":11,"evse_output_format":"auto",
        "output_transport":"modbus_tcp","modbus_host":"192.168.1.37",
        "modbus_register":770,"device_commands_confirmed":True}
    assert "evse_output_format" in validate_load_data(cfg)
    cfg["output_transport"] = "entity"
    assert "evse_output_format" not in validate_load_data(cfg)
