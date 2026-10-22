"""Regression tests for a universal internal-kW to physical device command pipeline."""
from types import SimpleNamespace

import pytest

from custom_components.power_manager.actuator import (
    ActuatorError, _entity_output_plan, validate_actuator,
)


class FakeHA:
    def __init__(self, *, unit="kW", minimum=0, maximum=11, step=0.1):
        attrs = {"min": minimum, "max": maximum, "step": step}
        if unit is not None:
            attrs["unit_of_measurement"] = unit
        self._state = SimpleNamespace(state="0", attributes=attrs)
        self.states = SimpleNamespace(get=lambda entity_id: self._state)


def load(kind="modulating", **values):
    data = {
        "load_name": "Test",
        "load_type": kind,
        "priority": 1,
        "min_kw": 1,
        "max_kw": 11,
        "output_entity": "number.control",
        "output_transport": "entity",
        "output_value_mode": "power",
        "output_unit": "W",
        "safe_output_value": 0,
    }
    data.update(values)
    if kind == "evse":
        data.update({
            "evse_phases": 3,
            "evse_voltage_v": 230,
            "evse_min_current_a": 6,
            "evse_max_current_a": 16,
            "evse_pause_current_a": 0.01,
            "evse_power_step_w": 1000,
            "evse_zero_unlimited": True,
        })
        data.update(values)
    return data


@pytest.mark.parametrize("unit,expected", [
    ("W", 5000.0), ("kW", 5.0), ("MW", 0.005),
])
def test_kilowatt_internal_is_converted_to_real_entity_units(unit, expected):
    hass = FakeHA(unit=unit, minimum=0, maximum=20000 if unit == "W" else 20,
                  step=1000 if unit == "W" else 0.001)
    result = _entity_output_plan(
        hass, load(output_unit="W", min_kw=1, max_kw=11),
        5.0, hass._state,
    )
    assert result.numeric_value == pytest.approx(expected)
    assert result.numeric_unit == unit


def test_generic_thermal_load_step_rounded_down_in_native_kw():
    hass = FakeHA(unit="kW", step=0.1, maximum=20)
    result = _entity_output_plan(
        hass, load(output_unit="W", max_kw=20), 9.6685, hass._state,
    )
    assert result.numeric_value == pytest.approx(9.6)
    assert result.numeric_unit == "kW"


def test_thermal_and_heater_limits_are_not_confused_with_watts():
    hass = FakeHA(unit="kW", maximum=20, step=0.1)
    for kw in (1, 5, 10):
        result = _entity_output_plan(
            hass, load(min_kw=1, max_kw=20, output_unit="W"), kw, hass._state,
        )
        assert result.numeric_value == kw
    validate_actuator(hass, load(min_kw=1, max_kw=20, output_unit="W"))


def test_evse_power_output_watt_plan_writes_kw_to_kw_entity():
    hass = FakeHA(unit="kW", maximum=11, step=0.1)
    data = load("evse", min_kw=4.14, max_kw=11,
                evse_output_format="W", evse_power_step_w=1000)
    plan = _entity_output_plan(hass, data, 11, hass._state)
    assert plan.numeric_value == 11
    assert plan.numeric_unit == "kW"
    validate_actuator(hass, data)


def test_evse_dynamic_kw_step_never_causes_unrepresentable_fraction():
    hass = FakeHA(unit="kW", step=0.1)
    data = load("evse", min_kw=4.14, max_kw=11,
                evse_output_format="kW", evse_power_step_w=100)
    plan = _entity_output_plan(hass, data, 9.6685, hass._state)
    assert plan.numeric_value == pytest.approx(9.6)


def test_evse_physical_minimum_enforced_after_step_rounding():
    hass = FakeHA(unit="kW", step=1)
    data = load("evse", min_kw=4.14, max_kw=11,
                evse_output_format="kW", evse_power_step_w=100)
    plan = _entity_output_plan(hass, data, 4.99, hass._state)
    assert plan.enabled is False
    assert plan.numeric_value == 0
    plan = _entity_output_plan(hass, data, 5.0, hass._state)
    assert plan.enabled is True
    assert plan.numeric_value == 5


def test_ampere_is_not_silently_confused_with_kilowatts():
    hass = FakeHA(unit="kW", maximum=11, step=0.1)
    with pytest.raises(ActuatorError, match="Ausgangseinheiten unvereinbar"):
        _entity_output_plan(
            hass, load("evse", evse_output_format="A"), 6.9, hass._state,
        )


def test_unsafe_pause_special_code_is_never_rounded_or_unit_converted():
    hass = FakeHA(unit="kW", step=0.1)
    with pytest.raises(ActuatorError, match="Nicht-null-Pausencode"):
        _entity_output_plan(
            hass, load(output_unit="W", safe_output_value=0.001), 0, hass._state,
        )


def test_custom_device_code_is_not_quantized_into_another_device_code():
    hass = FakeHA(unit=None, step=1, maximum=100)
    cfg = load(output_value_mode="linear", output_scale=1, output_offset=0)
    with pytest.raises(ActuatorError, match="Gerätecode"):
        _entity_output_plan(hass, cfg, 7.7, hass._state)


def test_no_silent_unit_guess_without_entity_unit_when_value_out_of_range():
    hass = FakeHA(unit=None, maximum=11, step=0.1)
    with pytest.raises(ActuatorError, match="Obergrenze"):
        _entity_output_plan(
            hass, load(output_unit="W"), 11, hass._state,
        )
