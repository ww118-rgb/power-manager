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
         battery=0, soc=None, growth=0.3):
    return ControllerInputs(
        grid_kw=grid, pv_kw=pv, grid_limit_kw=pmax,
        mode=mode, now_s=now, grid_growth_margin_kw=growth,
        battery_kw=battery, battery_soc=soc,
        hybrid_probe_enabled=True, hybrid_battery_assist_enabled=True,
        hybrid_probe_step_kw=10,
    )


def previous(**targets):
    return ControllerState(
        last_targets_kw=targets,
        load_states={
            name: LoadRuntimeState(is_on=value > 0, last_target_kw=value)
            for name, value in targets.items()
        },
    )


@pytest.mark.parametrize("battery,soc", [
    (-30.0, 0.0), (-10, 99), (0, None), (20, 0), (30, 100),
])
def test_battery_never_changes_grid_or_pv_targets(battery, soc):
    normal = data(grid=129.56, pmax=140, battery=battery, soc=soc)
    solar = data(grid=-10, pv=25, pmax=140, mode=OperatingMode.SURPLUS,
                 battery=battery, soc=soc)
    loads = [load("EV1", minimum=4.14), load("EV2", minimum=4.14)]
    normal_result = run_controller(normal, loads)
    pv_result = run_controller(solar, loads)
    assert normal_result.total_target_kw == pytest.approx(10.14)
    assert pv_result.targets_kw == pytest.approx({"EV1": 5, "EV2": 5})
    assert not pv_result.battery_soc_gate_enabled
    assert not pv_result.battery_soc_blocking_surplus


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
        replace(data(grid=130), grid_recovery_hold_s=999),
        [heat],
    )
    second = run_controller(
        replace(data(grid=125, now=1), grid_recovery_hold_s=999),
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


def test_equal_wallboxes_converge_when_pmax_is_full_without_grid_borrowing():
    """Previous 6/6.5 kW should not remain uneven at exactly 140 kW import."""
    evs = [
        load("WB1", minimum=4.14, maximum=11, request=11, priority=1),
        load("WB2", minimum=4.14, maximum=11, request=11, priority=1),
    ]
    result = run_controller(
        data(grid=140, pmax=140),
        evs, previous(WB1=6.0, WB2=6.5),
    )
    assert result.targets_kw == pytest.approx({"WB1": 6.0, "WB2": 6.0})
    assert result.projected_grid_kw <= 140
    # A reduction is not spent before it appears on the next grid reading.
    second = run_controller(
        data(grid=139.5, pmax=140, now=1), evs, result.state,
    )
    assert second.targets_kw["WB1"] == pytest.approx(second.targets_kw["WB2"])
    assert second.projected_grid_kw <= 140


def test_pv_equalizes_existing_wallboxes_without_fictitious_export():
    evs = [
        load("WB1", minimum=4.14, maximum=11, request=11, priority=1),
        load("WB2", minimum=4.14, maximum=11, request=11, priority=99),
    ]
    current = previous(WB1=6.0, WB2=6.5)
    first = run_controller(
        data(grid=0, pv=20, mode=OperatingMode.SURPLUS), evs, current,
    )
    assert first.targets_kw == pytest.approx({"WB1": 6.0, "WB2": 6.0})
    assert first.projected_grid_kw <= 0  # Never borrow from the grid to equalize.
    # If the grid meter then confirms 0.5 kW of export, share it equally.
    second = run_controller(
        data(grid=-0.5, pv=20, mode=OperatingMode.SURPLUS, now=1),
        evs, first.state,
    )
    assert second.targets_kw == pytest.approx({"WB1": 6.25, "WB2": 6.25})
    assert second.projected_grid_kw <= 0


def test_different_limits_are_not_rounded_to_artificial_equality():
    evs = [
        load("WB1", minimum=4.14, maximum=6, request=6, priority=1),
        load("WB2", minimum=4.14, maximum=11, request=11, priority=1),
    ]
    result = run_controller(
        data(grid=0, pv=20, mode=OperatingMode.SURPLUS),
        evs, previous(WB1=6.0, WB2=6.5),
    )
    assert result.targets_kw["WB1"] == pytest.approx(6.0)
    assert result.targets_kw["WB2"] > result.targets_kw["WB1"]


def test_non_equivalent_wallboxes_keep_normal_priority():
    evs = [
        load("WB1", minimum=4.14, maximum=11, request=11, priority=1),
        load("WB2", minimum=4.14, maximum=11, request=11, priority=2),
    ]
    result = run_controller(data(grid=133, pmax=140), evs)
    assert result.targets_kw["WB1"] > result.targets_kw["WB2"]


def test_screenshot_139_17_kw_rebalances_equal_wallboxes_within_grid_limit():
    """Same config, 6.0 vs 6.5 kW, PMAX 140 and 0.3 kW noise margin."""
    evs = [
        load("WB1", minimum=4.14, maximum=11, request=11),
        load("WB2", minimum=4.14, maximum=11, request=11),
    ]
    result = run_controller(
        data(grid=139.17, pmax=140),
        evs, previous(WB1=6.0, WB2=6.5),
    )
    assert result.targets_kw["WB1"] == pytest.approx(
        result.targets_kw["WB2"], abs=1e-5,
    )
    assert result.targets_kw["WB1"] >= 6.0
    assert result.projected_grid_kw <= 139.7 + 1e-5
    assert sum(
        max(0.0, result.targets_kw[name] - previous_target)
        for name, previous_target in (("WB1", 6.0), ("WB2", 6.5))
    ) <= 140 - 139.17 - 0.3 + 1e-5


def test_two_new_equal_wallboxes_split_net_headroom_fairly():
    evs = [load("WB1", minimum=4.14), load("WB2", minimum=4.14)]
    result = run_controller(data(grid=129.56, pmax=140), evs)
    assert result.targets_kw["WB1"] == pytest.approx(5.07)
    assert result.targets_kw["WB2"] == pytest.approx(5.07)
    assert result.projected_grid_kw <= 139.7 + 1e-6


def test_single_starter_is_not_disabled_when_two_minima_do_not_fit():
    evs = [load("WB1", minimum=4.14), load("WB2", minimum=4.14)]
    result = run_controller(data(grid=135, pmax=140), evs)
    assert result.targets_kw["WB1"] >= 4.14
    assert result.targets_kw["WB2"] == 0.0
    assert result.projected_grid_kw <= 140
