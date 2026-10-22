"""Simplified grid/PV controller regression tests; battery is autonomous."""
from dataclasses import replace

import pytest

from controller import run_controller
from models import ControllableLoad, ControllerInputs, ControllerState, LoadRuntimeState, OperatingMode


def load(name, *, minimum=0.0, maximum=11.0, request=11.0,
         actual=None, priority=1, peak=True, solar=True):
    return ControllableLoad(
        name=name, priority=priority, requested_kw=request,
        min_kw=minimum, max_kw=maximum, actual_kw=actual,
        peak_shaving_enabled=peak, surplus_enabled=solar,
    )


def data(*, grid, pv=0, pmax=140, mode=OperatingMode.NORMAL, now=0,
         growth=0.3):
    return ControllerInputs(
        grid_kw=grid, pv_kw=pv, grid_limit_kw=pmax,
        mode=mode, now_s=now, grid_growth_margin_kw=growth,
    )


def previous(**targets):
    return ControllerState(
        last_targets_kw=targets,
        load_states={
            name: LoadRuntimeState(is_on=value > 0, last_target_kw=value)
            for name, value in targets.items()
        },
    )


def test_no_battery_in_v4_controller_interface():
    assert "battery_kw" not in ControllerInputs.__dataclass_fields__
    assert "battery_soc" not in ControllerInputs.__dataclass_fields__


def test_simple_140_kw_peak_shaving_with_no_device_sensor():
    heat = load("Heat", minimum=1, maximum=20, request=20)
    result = run_controller(
        data(grid=122.08, pmax=140), [heat], previous(Heat=8.3),
    )
    assert result.base_load_kw == pytest.approx(113.78)
    assert result.peak_budget_kw == pytest.approx(26.22)
    assert result.targets_kw["Heat"] == pytest.approx(20)
    assert result.projected_grid_kw < 140


def test_peak_shaving_reduces_immediately_with_or_without_ist():
    for actual in (None, 10.0):
        heat = load("Heat", minimum=1, maximum=20, request=20, actual=actual)
        result = run_controller(
            data(grid=142, pmax=140), [heat], previous(Heat=10),
        )
        assert result.targets_kw["Heat"] == pytest.approx(8.0)
        assert result.projected_grid_kw <= 140


def test_normal_load_admission_respects_actual_meter_headroom():
    answer = run_controller(
        data(grid=130, pmax=140),
        [load("Heat", minimum=4, maximum=20, request=20)],
    )
    assert answer.targets_kw["Heat"] == pytest.approx(9.7)
    assert answer.projected_grid_kw == pytest.approx(139.7)


def test_normal_can_adjust_on_next_measurement_without_global_hold():
    heat = load("Heat", minimum=1, maximum=20, request=20)
    first = run_controller(
        data(grid=130),
        [heat],
    )
    second = run_controller(
        data(grid=125, now=1),
        [heat], first.state,
    )
    assert second.targets_kw["Heat"] > first.targets_kw["Heat"]


def test_priority_in_normal_mode_is_retained():
    loads = [
        load("First", priority=1, minimum=1, maximum=20, request=20),
        load("Second", priority=2, minimum=1, maximum=20, request=20),
    ]
    answer = run_controller(data(grid=130), loads)
    assert answer.targets_kw["First"] > answer.targets_kw["Second"]
    assert answer.total_target_kw <= 9.7 + 1e-6


def test_real_export_is_shared_equally_across_pv_consumers():
    loads = [
        load("EV1", minimum=4.14, priority=1),
        load("EV2", minimum=4.14, priority=99),
    ]
    result = run_controller(
        data(grid=-10, pv=30, mode=OperatingMode.SURPLUS), loads,
    )
    assert result.targets_kw == pytest.approx({"EV1": 5, "EV2": 5})
    assert result.raw_surplus_budget_kw == pytest.approx(10)


def test_existing_pv_load_does_not_toggle_at_zero_grid_export():
    solar_load = load("EV", minimum=4.14)
    state = None
    targets = []
    for now in range(100):
        result = run_controller(
            data(grid=0, pv=25, mode=OperatingMode.SURPLUS, now=now),
            [solar_load], state=previous(EV=9) if state is None else state,
        )
        state = result.state
        targets.append(result.targets_kw["EV"])
    assert targets == pytest.approx([9] * 100)


def test_pv_does_not_start_new_load_without_export():
    result = run_controller(
        data(grid=0, pv=30, mode=OperatingMode.SURPLUS),
        [load("EV", minimum=4.14)],
    )
    assert result.targets_kw["EV"] == 0


@pytest.mark.parametrize("grid,pv,expect", [
    (-5, 0, 0), (5, 30, 0), (0, 30, 0), (-6, 20, 6),
])
def test_actual_pv_export_not_installed_pv_or_battery_is_used(grid, pv, expect):
    answer = run_controller(
        data(grid=grid, pv=pv, mode=OperatingMode.SURPLUS),
        [load("Heater", minimum=0, maximum=20, request=20)],
    )
    assert answer.total_target_kw == pytest.approx(expect)


def test_pv_minimum_is_not_bypassed():
    loads = [load("EV", minimum=4.14)]
    small = run_controller(
        data(grid=-3, pv=20, mode=OperatingMode.SURPLUS), loads,
    )
    assert small.targets_kw["EV"] == 0
    large = run_controller(
        data(grid=-5, pv=20, mode=OperatingMode.SURPLUS), loads,
    )
    assert large.targets_kw["EV"] == pytest.approx(5)


def test_two_pv_devices_start_only_if_both_minima_fit():
    loads = [load("EV1", minimum=4.14), load("EV2", minimum=4.14)]
    result = run_controller(
        data(grid=-9, pv=20, mode=OperatingMode.SURPLUS), loads,
    )
    assert result.targets_kw == pytest.approx({"EV1": 4.5, "EV2": 4.5})


def test_surplus_budget_retains_existing_consumption_but_no_grid_import():
    existing = load("EV", minimum=2, maximum=20, request=20)
    result = run_controller(
        data(grid=0, pv=20, mode=OperatingMode.SURPLUS),
        [existing], state=previous(EV=9),
    )
    assert result.surplus_budget_kw == pytest.approx(9)
    assert result.targets_kw["EV"] == pytest.approx(9)


def test_solar_and_normal_modes_respect_load_eligibility():
    first = load("NormalOnly", solar=False)
    second = load("SolarOnly", peak=False, solar=True)
    solar = run_controller(
        data(grid=-15, pv=20, mode=OperatingMode.SURPLUS), [first, second],
    )
    assert solar.targets_kw == {}
    normal = run_controller(data(grid=120), [first, second])
    assert list(normal.targets_kw) == ["NormalOnly"]


def test_normal_grid_noise_does_not_force_repeated_off_on():
    heat = load("Heat", minimum=4, maximum=20, request=20)
    state = None
    out = []
    baseline = 130
    for i in range(120):
        target = 0 if state is None else state.last_targets_kw["Heat"]
        grid = baseline + target + (0.05 if i % 2 else -0.05)
        ans = run_controller(
            data(grid=grid, now=5*i), [heat], state=state,
        )
        state = ans.state
        out.append(ans.targets_kw["Heat"])
    assert all(x >= 4 for x in out)
    assert max(out[5:])-min(out[5:]) < 0.5
