"""PMAX grid-meter-only regression, including optional device feedback and anti-oscillation.

No device actual-power sensor is required to calculate valid NORMAL targets.
Hardware cannot guarantee no transient PMAX violation after battery failure.
"""
from dataclasses import replace

import pytest

from controller import run_controller
from models import (
    ControllableLoad, ControllerInputs, ControllerState,
    LoadRuntimeState, OperatingMode,
)


def load(name="Heat", *, requested=20, minimum=1, maximum=20,
         actual=None, priority=1, can_modulate=True):
    return ControllableLoad(
        name=name, priority=priority, requested_kw=requested,
        min_kw=minimum, max_kw=maximum, actual_kw=actual,
        can_modulate=can_modulate, available=True,
    )


def values(now, *, grid=129.56, pmax=140, margin=0.3):
    return ControllerInputs(
        grid_kw=grid, grid_limit_kw=pmax,
        grid_growth_margin_kw=margin,
        mode=OperatingMode.NORMAL, now_s=now,
    )


def previous_target(name, target):
    return ControllerState(
        last_targets_kw={name: target},
        load_states={
            name: LoadRuntimeState(is_on=target > 0,
                                   last_target_kw=target)
        },
    )


def test_140_kw_site_uses_measured_grid_not_current_battery_discharge():
    old = previous_target("Heat", 9.6)
    result = run_controller(values(0), [load()], state=old)
    # Actual import: 129.56 kW. Current grid room: 10.44 kW,
    # less 0.3 kW for possible metering jitter.
    assert result.base_load_kw == pytest.approx(129.56 - 9.6)
    assert result.peak_budget_kw == pytest.approx(20.04)
    assert result.targets_kw["Heat"] == pytest.approx(19.74)
    assert result.projected_grid_kw == pytest.approx(139.70)
    # No global 15-second hold: next fresh grid reading can be used immediately.
    assert not hasattr(result.state, 'grid_growth_block_until_s')
    assert result.targets_kw["Heat"] > 9.6


def test_no_load_meter_uses_last_command_only_as_estimate():
    previous = previous_target("Heat", 9.6)
    result = run_controller(values(0), [load(actual=None)], previous)
    assert result.measured_controlled_power_kw == 0
    assert result.estimated_controlled_power_kw == pytest.approx(9.6)
    # NO assumed positive feedback from the last target: a new increase
    # cannot exceed the instantaneous grid headroom after the margin.
    assert result.total_target_kw - 9.6 <= 140 - 129.56 - 0.3 + 1e-6


def test_next_grid_cycle_can_recover_without_15_second_wait():
    first = run_controller(values(0), [load()], previous_target("Heat", 9.6))
    assert first.targets_kw["Heat"] == pytest.approx(19.74)
    hold = run_controller(values(5, grid=139.70), [load()], first.state)
    assert hold.targets_kw["Heat"] == pytest.approx(19.74)
    # Even within the hold period a genuine grid overrun must reduce NOW.
    shed = run_controller(values(6, grid=142.0), [load()], hold.state)
    assert shed.targets_kw["Heat"] == pytest.approx(17.74)
    assert shed.targets_kw["Heat"] < hold.targets_kw["Heat"]
    assert shed.projected_grid_kw <= 140 + 1e-6
    # Net power has dropped and can be reallocated on the next reading.
    rebound = run_controller(values(7, grid=138.0), [load()], shed.state)
    assert rebound.targets_kw["Heat"] > shed.targets_kw["Heat"]
    assert rebound.projected_grid_kw <= 140


def test_small_grid_noise_does_not_toggle_consumer():
    state = previous_target("Heat", 9.6)
    results = []
    for i in range(90):
        grid = 129.56 + (0.05 if i % 2 else -0.05)
        answer = run_controller(values(i * 5, grid=grid), [load()], state)
        state = answer.state
        results.append(answer.targets_kw["Heat"])
    assert all(x > 0 for x in results)
    assert max(results) - min(results) < 0.5


def test_no_same_tick_reallocation_from_unconfirmed_shed_without_ist():
    current = previous_target("Old", 10)
    old = load("Old", requested=0, minimum=0, maximum=10)
    new = load("New", requested=12, minimum=4.14, maximum=12)
    first = run_controller(values(0, grid=139.5), [old, new], current)
    assert first.targets_kw["Old"] == 0
    assert first.targets_kw["New"] == 0  # Do not spend assumed 10 kW reduction.
    second = run_controller(values(5, grid=129.5), [old, new], first.state)
    # Once the grid meter physically shows 10 kW freed, reuse it NOW.
    assert second.targets_kw["New"] >= 4.14
    assert second.projected_grid_kw <= 140


@pytest.mark.parametrize("pmax,grid", [(10, 4), (25, 19), (140, 134), (250, 244)])
def test_limit_is_configurable_not_hardcoded_140(pmax, grid):
    result = run_controller(
        values(0, grid=grid, pmax=pmax),
        [load(requested=15, minimum=4, maximum=15)],
    )
    assert 0 <= result.total_target_kw <= pmax - grid + 1e-6
    assert result.projected_grid_kw <= pmax + 1e-6


def test_unrepresentable_evse_minimum_must_not_be_started():
    evse = load("EV", requested=11, minimum=4.14, maximum=11)
    answer = run_controller(values(0, grid=137.0), [evse])
    assert answer.targets_kw["EV"] == 0


def test_missing_ist_and_battery_sensor_is_normal():
    result = run_controller(
        values(0),
        [load(actual=None)],
    )
    assert result.targets_kw["Heat"] > 0
    assert result.total_target_kw <= 140 - 129.56 - 0.3 + 1e-6


def test_anti_oscillation_settings_are_validated():
    with pytest.raises(ValueError):
        run_controller(replace(values(0), grid_growth_margin_kw=-0.1), [load()])
