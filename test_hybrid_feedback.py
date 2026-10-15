"""Regressions for the battery-neutral, plant-independent hybrid control loop."""

import pytest

from controller import run_controller
from models import ControllableLoad, ControllerInputs, OperatingMode


def load(*, actual=0.0, requested=30.0, min_kw=0.0):
    return ControllableLoad(
        name="Last", priority=1, requested_kw=requested,
        min_kw=min_kw, max_kw=30.0, actual_kw=actual,
    )


def plant(*, grid=0.0, pv=30.0, battery=0.0, soc=80.0,
          reserve=30.0, grid_limit=140.0, grid_reserve=0.0,
          now=0.0, live=True, meter=True, step=1.0, settle=2.0,
          retry=10.0):
    return ControllerInputs(
        grid_kw=grid, grid_limit_kw=grid_limit,
        grid_reserve_kw=grid_reserve, pv_kw=pv,
        battery_kw=battery, battery_soc=soc,
        surplus_min_battery_soc=reserve,
        mode=OperatingMode.SURPLUS, now_s=now,
        hybrid_battery_assist_enabled=meter,
        hybrid_probe_enabled=live,
        hybrid_probe_step_kw=step,
        hybrid_probe_settle_s=settle,
        hybrid_probe_retry_s=retry,
        hybrid_grid_tolerance_kw=0.1,
    )


def test_real_pv_surplus_excludes_house_load():
    # 30 PV, 10 house load, 20 controlled, no battery/grid.
    result = run_controller(plant(), [load(actual=20)])
    assert result.raw_surplus_budget_kw == pytest.approx(20)
    assert result.targets_kw["Last"] == pytest.approx(20)


def test_hybrid_retains_observed_discharge_without_invented_rating():
    # 30 PV + 10 battery covers 10 house + 30 controlled.
    result = run_controller(plant(battery=10), [load(actual=30)])
    assert result.raw_surplus_budget_kw == pytest.approx(20)
    assert result.surplus_budget_kw == pytest.approx(30)
    assert result.targets_kw["Last"] == pytest.approx(30)


@pytest.mark.parametrize("soc", [29.0, 30.0])
def test_reserve_stops_battery_support_but_keeps_pv_only(soc):
    result = run_controller(
        plant(battery=10, soc=soc), [load(actual=30)]
    )
    assert result.battery_soc_blocking_surplus
    assert result.raw_surplus_budget_kw == pytest.approx(20)
    assert result.targets_kw["Last"] == pytest.approx(20)


def test_soc_limit_is_fully_configurable():
    result = run_controller(
        plant(battery=10, soc=50.0, reserve=50.0),
        [load(actual=30)],
    )
    assert result.targets_kw["Last"] == pytest.approx(20)


def test_no_real_pv_surplus_even_if_pv_produces():
    # 3 PV, 5 non-controllable house demand, 2 from battery.
    result = run_controller(
        plant(grid=0, pv=3, battery=2), [load(actual=0)]
    )
    assert result.raw_surplus_budget_kw == 0
    assert result.targets_kw["Last"] == 0


def test_no_battery_only_when_pv_is_zero():
    result = run_controller(
        plant(pv=0, battery=10), [load(actual=0)]
    )
    assert result.targets_kw["Last"] == 0


def test_battery_support_requires_configured_soc_and_meter():
    result = run_controller(
        plant(battery=10, reserve=None), [load(actual=30)]
    )
    assert result.targets_kw["Last"] == pytest.approx(20)
    result = run_controller(
        plant(battery=10, meter=False), [load(actual=30)]
    )
    assert result.targets_kw["Last"] == pytest.approx(20)


def test_existing_battery_charge_not_assumed_instantly_divertible():
    # 30 PV = 5 house + 15 battery charging + 10 exported.
    result = run_controller(
        plant(grid=-10, battery=-15, live=False), [load(actual=0)]
    )
    assert result.raw_surplus_budget_kw == pytest.approx(25)
    assert result.targets_kw["Last"] == pytest.approx(10)


def test_load_probe_discovers_increased_discharge_from_feedback():
    r0 = run_controller(
        plant(now=0), [load(actual=20)]
    )
    assert r0.targets_kw["Last"] == pytest.approx(20)

    r1 = run_controller(
        plant(now=1), [load(actual=20)], state=r0.state,
    )
    assert r1.targets_kw["Last"] == pytest.approx(21)
    assert r1.state.hybrid_probe_until_s == pytest.approx(3)

    # Actual power, battery discharge and grid are observed.
    r2 = run_controller(
        plant(now=2, battery=1), [load(actual=21)], state=r1.state,
    )
    assert r2.targets_kw["Last"] == pytest.approx(21)

    r3 = run_controller(
        plant(now=4, battery=1), [load(actual=21)], state=r2.state,
    )
    assert r3.targets_kw["Last"] == pytest.approx(21)
    assert r3.state.hybrid_probe_until_s is None

    r4 = run_controller(
        plant(now=14, battery=1), [load(actual=21)], state=r3.state,
    )
    assert r4.targets_kw["Last"] == pytest.approx(22)


def test_failed_probe_rolls_back_after_settling_timeout():
    r0 = run_controller(plant(now=0), [load(actual=20)])
    r1 = run_controller(
        plant(now=1), [load(actual=20)], state=r0.state,
    )
    # A bounded 1 kW transient is permitted until settling ends.
    r2 = run_controller(
        plant(now=2, grid=1), [load(actual=21)], state=r1.state,
    )
    assert r2.targets_kw["Last"] == pytest.approx(21)
    r3 = run_controller(
        plant(now=4, grid=1), [load(actual=21)], state=r2.state,
    )
    assert r3.targets_kw["Last"] == pytest.approx(20)
    assert r3.state.hybrid_probe_until_s is None
    r4 = run_controller(
        plant(now=5), [load(actual=20)], state=r3.state,
    )
    assert r4.targets_kw["Last"] == pytest.approx(20)
    r5 = run_controller(
        plant(now=14), [load(actual=20)], state=r4.state,
    )
    assert r5.targets_kw["Last"] == pytest.approx(21)


def test_inverter_delay_recovers_before_settling_deadline():
    r0 = run_controller(plant(now=0), [load(actual=20)])
    r1 = run_controller(plant(now=1), [load(actual=20)], state=r0.state)
    r2 = run_controller(
        plant(now=2, grid=1), [load(actual=21)], state=r1.state,
    )
    assert r2.targets_kw["Last"] == pytest.approx(21)
    r3 = run_controller(
        plant(now=2.5, battery=1), [load(actual=21)], state=r2.state,
    )
    assert r3.targets_kw["Last"] == pytest.approx(21)
    r4 = run_controller(
        plant(now=4, battery=1), [load(actual=21)], state=r3.state,
    )
    assert r4.state.hybrid_probe_until_s is None
    assert r4.targets_kw["Last"] == pytest.approx(21)


def test_large_grid_excursion_cancels_probe_immediately():
    r0 = run_controller(plant(now=0), [load(actual=20)])
    r1 = run_controller(plant(now=1), [load(actual=20)], state=r0.state)
    r2 = run_controller(
        plant(now=2, grid=2), [load(actual=21)], state=r1.state,
    )
    assert r2.state.hybrid_probe_until_s is None
    assert r2.targets_kw["Last"] == pytest.approx(19)


def test_soc_drops_while_probe_pending():
    r0 = run_controller(plant(now=0), [load(actual=20)])
    r1 = run_controller(
        plant(now=1), [load(actual=20)], state=r0.state,
    )
    r2 = run_controller(
        plant(now=2, soc=30, battery=1),
        [load(actual=21)], state=r1.state,
    )
    assert r2.targets_kw["Last"] == pytest.approx(20)
    assert r2.state.hybrid_probe_until_s is None


def test_no_probe_when_load_measurement_is_missing():
    r0 = run_controller(plant(now=0), [load(actual=None)])
    r1 = run_controller(
        plant(now=1), [load(actual=None)], state=r0.state,
    )
    assert r1.state.hybrid_probe_until_s is None


def test_dry_run_does_not_explore_inverter():
    r0 = run_controller(
        plant(now=0, live=False), [load(actual=20)]
    )
    r1 = run_controller(
        plant(now=1, live=False), [load(actual=20)], state=r0.state,
    )
    assert r1.targets_kw["Last"] == pytest.approx(20)


def test_small_configured_pmax_wins_even_if_battery_present():
    # Current power is battery-supported, but battery could drop out.
    result = run_controller(
        plant(
            battery=10, grid_limit=10, grid_reserve=2,
            live=False,
        ),
        [load(actual=30)],
    )
    assert result.effective_grid_limit_kw == pytest.approx(8)
    assert result.peak_budget_kw == pytest.approx(28)
    assert result.targets_kw["Last"] == pytest.approx(28)
    assert result.projected_grid_kw <= 8


def test_technical_minimum_prevents_unsafe_partial_probe():
    r0 = run_controller(
        plant(now=0, grid=-5, step=0.5),
        [load(actual=0, requested=30, min_kw=6)],
    )
    assert r0.targets_kw["Last"] == 0
    r1 = run_controller(
        plant(now=1, grid=-5, step=0.5),
        [load(actual=0, requested=30, min_kw=6)],
        state=r0.state,
    )
    # A 0.5 kW probe cannot start a 6 kW minimum load with 5 kW PV.
    assert r1.targets_kw["Last"] == 0
    assert r1.state.hybrid_probe_until_s is None
