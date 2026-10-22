"""Power Manager v3.3.0 custom device command profile regression tests.

These are device-independent command conversion tests; direct Modbus/MQTT
transports are not implemented in the first v3.3.0 development candidate.
"""
import pytest
from custom_components.power_manager.outputs import build_output_plan, OutputConversionError
from custom_components.power_manager.load_config import normalize_load_data, validate_load_data

def profile(**kwargs):
    params=dict(load_type="modulating", target_kw=0, power_unit="W",
                output_value_mode="linear", output_scale=1000,
                output_offset=0, safe_output_value=0.01, forbidden_value=0)
    params.update(kwargs)
    return build_output_plan(**params)

def conf(**kwargs):
    d=dict(load_name="Test",load_type="modulating",min_kw=1,max_kw=10,
           priority=1,output_entity="number.test",output_value_mode="linear",
           output_scale=1000,output_offset=0,safe_output_value=0.01,
           output_forbidden_value=0)
    d.update(kwargs)
    return d

def test_unsafe_zero_blocked_with_custom_pause():
    p=profile(target_kw=0)
    assert p.numeric_value == pytest.approx(0.01)
    assert not p.enabled

def test_unsafe_zero_refused():
    with pytest.raises(OutputConversionError,match="forbidden"):
        profile(safe_output_value=0)

def test_positive_target_uses_configured_multiplier():
    p=profile(target_kw=6.9)
    assert p.numeric_value == pytest.approx(6900)
    assert p.numeric_unit == "device"

def test_offset_applies_only_to_nonzero_target():
    assert profile(target_kw=2,output_scale=1,output_offset=10).numeric_value == 12
    assert profile(target_kw=0,output_scale=1,output_offset=10).numeric_value == pytest.approx(0.01)

def test_zero_never_means_off_when_evse_unlimited_is_true():
    with pytest.raises(OutputConversionError,match="unrestricted|releases"):
        build_output_plan(load_type="evse",target_kw=0,evse_pause_current_a=0,evse_zero_unlimited=True)

def test_evse_can_allow_zero_if_documented_for_another_device():
    p=build_output_plan(load_type="evse",target_kw=0,evse_pause_current_a=0,evse_zero_unlimited=False)
    assert p.numeric_value==0

def test_existing_evse_default_safe_pause_remains():
    p=build_output_plan(load_type="evse",target_kw=0,evse_zero_unlimited=True)
    assert p.numeric_value==pytest.approx(0.01)

def test_unknown_profile_refused():
    with pytest.raises(OutputConversionError,match="Unknown"):
        profile(output_value_mode="unknown",target_kw=1)

def test_nonpositive_scale_refused():
    with pytest.raises(OutputConversionError,match="positive"):
        profile(output_scale=0,target_kw=1)

def test_nonfinite_values_refused():
    with pytest.raises(OutputConversionError,match="finite"):
        profile(output_offset=float("nan"),target_kw=2)

def test_legacy_load_settings_normalize_without_data_loss():
    p=normalize_load_data(dict(load_name="Old",load_type="modulating",min_kw=1,
                               max_kw=10,priority=1,output_entity="number.old"))
    assert p["output_value_mode"]=="power"
    assert p["output_forbidden_value"] is None

def test_dangerous_off_command_rejected_preflight():
    err=validate_load_data(conf(safe_output_value=0))
    assert err["safe_output_value"]=="forbidden_pause_code"

def test_safe_config_accepted():
    assert validate_load_data(conf())=={}

def test_evse_zero_unlimited_rejects_pause_zero():
    err=validate_load_data(conf(load_type="evse",evse_pause_current_a=0))
    assert err["evse_pause_current_a"]=="evse_zero_means_unlimited"

def test_wrong_profile_guard_applies_at_output_layer_not_grid_regulator():
    p=build_output_plan(load_type="modulating",target_kw=2.5,
                        power_unit="kW",output_value_mode="power")
    assert p.numeric_value==pytest.approx(2.5)
