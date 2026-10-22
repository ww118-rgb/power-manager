"""V4 acceptance invariants: one controller, no hybrid state, safe fair output."""
from pathlib import Path

import pytest

from controller import run_controller
from models import (
    ControllableLoad, ControllerInputs, ControllerState, OperatingMode,
)

ROOT = Path(__file__).resolve().parent
INTEGRATION = ROOT / "custom_components" / "power_manager"


@pytest.mark.parametrize("filename", ["models.py", "allocator.py", "controller.py"])
def test_one_canonical_hacs_controller_and_identical_pure_test_mirror(filename):
    expected = (INTEGRATION / filename).read_text(encoding="utf-8")
    expected = expected.replace("from .models import", "from models import")
    expected = expected.replace("from .allocator import", "from allocator import")
    mirror = (ROOT / filename).read_text(encoding="utf-8")
    assert mirror == expected, f"{filename}: HACS and unit tests have diverged"


def _ev(name, *, priority=1, minimum=4.14, maximum=11.0, request=11.0):
    return ControllableLoad(
        name=name, priority=priority, requested_kw=request,
        min_kw=minimum, max_kw=maximum,
    )


def test_140_kw_wallboxes_with_equal_parameters_split_all_approved_growth():
    inputs = ControllerInputs(
        grid_kw=129.56, grid_limit_kw=140.0,
        grid_growth_margin_kw=0.3,
    )
    result = run_controller(inputs, [_ev("WB1"), _ev("WB2")])
    assert result.targets_kw["WB1"] == pytest.approx(5.07, abs=1e-5)
    assert result.targets_kw["WB2"] == pytest.approx(5.07, abs=1e-5)
    assert result.projected_grid_kw == pytest.approx(139.70, abs=1e-5)


def test_pv_zero_export_preserves_running_consumers_without_grid_borrowing():
    evs = [_ev("WB1"), _ev("WB2", priority=2)]
    state = ControllerState(last_targets_kw={"WB1": 6.0, "WB2": 6.5})
    previous = run_controller(
        ControllerInputs(
            grid_kw=0.0, grid_limit_kw=140.0, pv_kw=30.0,
            mode=OperatingMode.SURPLUS,
        ), evs, state,
    )
    assert previous.targets_kw == pytest.approx({"WB1": 6.0, "WB2": 6.0})
    assert previous.projected_grid_kw <= 0.0
    recovered = run_controller(
        ControllerInputs(
            grid_kw=-0.5, grid_limit_kw=140.0, pv_kw=30.0,
            mode=OperatingMode.SURPLUS, now_s=1.0,
        ), evs, previous.state,
    )
    assert recovered.targets_kw == pytest.approx({"WB1": 6.25, "WB2": 6.25})
    assert recovered.projected_grid_kw <= 0.0


def test_no_battery_or_hybrid_leak_into_the_control_contract():
    fields = ControllerInputs.__dataclass_fields__
    for field in (
        "battery_kw", "battery_soc", "surplus_min_battery_soc",
        "hybrid_probe_enabled", "grid_recovery_hold_s",
    ):
        assert field not in fields
    text = (INTEGRATION / "controller.py").read_text(encoding="utf-8")
    assert "inputs.battery" not in text
    assert "battery_bonus" not in text


def test_old_hybrid_configuration_is_migrated_without_losing_devices():
    source = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")
    flow = (INTEGRATION / "config_flow.py").read_text(encoding="utf-8")
    assert "VERSION = 5" in flow
    for key in (
        "surplus_min_battery_soc", "grid_recovery_hold_s",
        "hybrid_probe_step_kw", "feedback_tolerance_kw",
    ):
        assert f'"{key}"' in source
    assert "new_options = {key: val for key, val in entry.options.items()" in source
    assert "battery_power_entity" not in source[source.index("retired = {"):source.index("new_data =", source.index("retired = {"))]


def test_all_invalid_grid_measurements_are_rejected_before_allocation():
    load = _ev("EV")
    for value in (float("nan"), float("inf"), -float("inf")):
        with pytest.raises(ValueError):
            run_controller(ControllerInputs(grid_kw=value, grid_limit_kw=140), [load])


def test_optional_ist_sensor_not_required_for_peakshaving():
    inputs = ControllerInputs(grid_kw=139.0, grid_limit_kw=140)
    result = run_controller(inputs, [_ev("EV")])
    assert result.targets_kw["EV"] == 0.0  # Below EV minimum; safe pause.


def test_unavailable_load_is_uncontrollable_house_base_not_free_headroom():
    unavailable = ControllableLoad(
        name="UnreachableHeat", priority=1, requested_kw=20,
        min_kw=1, max_kw=20, actual_kw=10, available=False,
    )
    wallbox = ControllableLoad(
        name="EV", priority=1, requested_kw=11,
        min_kw=4.14, max_kw=11, actual_kw=None,
    )
    old = ControllerState(last_targets_kw={"EV": 5.0, "UnreachableHeat": 10})
    answer = run_controller(
        ControllerInputs(
            grid_kw=139.0, grid_limit_kw=140,
            grid_growth_margin_kw=0.3,
        ), [unavailable, wallbox], old,
    )
    assert answer.controlled_power_for_calculation_kw == pytest.approx(5)
    assert answer.base_load_kw == pytest.approx(134)
    assert answer.targets_kw["EV"] <= 5.7 + 1e-6
    assert answer.projected_grid_kw <= 140


def test_unavailable_pv_load_does_not_create_fictitious_surplus():
    unavailable = ControllableLoad(
        name="OfflineHeater", priority=1, requested_kw=20,
        min_kw=1, max_kw=20, actual_kw=10, available=False,
    )
    ev = _ev("EV")
    result = run_controller(
        ControllerInputs(
            grid_kw=0.0, pv_kw=25, grid_limit_kw=140,
            mode=OperatingMode.SURPLUS,
        ), [unavailable, ev],
    )
    assert result.surplus_budget_kw == 0
    assert result.targets_kw["EV"] == 0
