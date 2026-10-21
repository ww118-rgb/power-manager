"""Long-run pure-core regression: stable inputs must never oscillate commands."""
from dataclasses import replace
import pytest
from controller import run_controller
from models import ControllableLoad, ControllerInputs, OperatingMode


def consumer(actual=5.0, desired=10.0):
    return ControllableLoad(
        name="EV", priority=1, available=True,
        requested_kw=desired, min_kw=0,
        max_kw=11, actual_kw=actual,
    )


def readings(now, *, grid=0, pv=10, battery=0, soc=0, limit=10, reserve=0):
    return ControllerInputs(
        grid_kw=grid, grid_limit_kw=limit, pv_kw=pv,
        grid_reserve_kw=reserve, battery_kw=battery,
        battery_soc=soc, surplus_min_battery_soc=30,
        now_s=now, mode=OperatingMode.SURPLUS,
        hybrid_battery_assist_enabled=True,
        hybrid_probe_enabled=False,
    )


def test_steady_solar_and_zero_battery_no_power_command_oscillations():
    state = None
    sequence = []
    # PV 10, house 5, EV 5 -> grid 0, SOC 0.
    for n in range(240):
        result = run_controller(readings(n * 5), [consumer()], state=state)
        sequence.append(result.targets_kw["EV"])
        state = result.state
    assert len(set(round(p, 5) for p in sequence[20:])) == 1
    assert sequence[-1] == pytest.approx(5)


def test_steady_solar_noise_within_hysteresis_does_not_toggle_evse():
    state = None
    targets = []
    for n in range(120):
        # Slight realistic meter noise, no extra real net import.
        noise = 0.01 if n % 2 else -0.01
        result = run_controller(
            readings(n * 5, grid=noise), [consumer(actual=5)],
            state=state,
        )
        state = result.state
        targets.append(result.targets_kw["EV"])
    # No repeated off/on while a stable 5 kW supply exists.
    assert all(t > 0 for t in targets)
    assert max(targets) - min(targets) <= 0.05


@pytest.mark.parametrize("grid_limit_kw", [3.0, 10.0, 140.0, 250.0])
def test_varied_pmax_never_assumes_battery_discharge(grid_limit_kw):
    # PV 10, EV 10, extra battery 8 supporting house/EV.
    # Never trust future battery discharge in either mode.
    load = consumer(actual=10, desired=10)
    for mode in (OperatingMode.NORMAL, OperatingMode.SURPLUS):
        data = replace(
            readings(0, grid=2, battery=8, soc=80, limit=grid_limit_kw),
            mode=mode,
        )
        result = run_controller(data, [load])
        assert result.projected_grid_kw <= result.effective_grid_limit_kw + 1e-6 or result.total_target_kw == 0
        assert result.targets_kw["EV"] <= result.peak_budget_kw + 1e-6
