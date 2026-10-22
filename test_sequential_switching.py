"""Acceptance tests for sequential 5-second consumer dispatch.

A new consumer is activated only after the previous command has had a
5-second interval AND a new real grid report. Safety reductions never wait.
"""
import pytest

from controller import run_controller
from models import ControllerInputs, ControllerState, ControllableLoad, OperatingMode


def load(name, priority, *, request=20, maximum=20, minimum=1, actual=None):
    return ControllableLoad(
        name=name, priority=priority, requested_kw=request,
        min_kw=minimum, max_kw=maximum, actual_kw=actual,
    )


def sample(*, time=0, grid=110, meter=0, mode=OperatingMode.NORMAL,
           pv=0, limit=140, interval=5):
    return ControllerInputs(
        grid_kw=grid, grid_limit_kw=limit, pv_kw=pv, mode=mode,
        now_s=time, switch_interval_s=interval,
        grid_sample_s=meter,
    )


def test_30_kw_headroom_starts_priority_one_then_priority_two_after_5s():
    devices = [
        load("WP", priority=1, request=20, maximum=20),
        load("WB", priority=2, request=11, maximum=11, minimum=4.14),
    ]
    first = run_controller(sample(), devices)
    assert first.targets_kw == pytest.approx({"WP": 20, "WB": 0})
    assert first.projected_grid_kw == pytest.approx(130)
    assert first.state.last_switch_action_s == 0

    # A new sensor reading BEFORE 5 s does not authorize WB yet.
    before = run_controller(
        sample(time=4.99, grid=130, meter=4.99), devices, first.state,
    )
    assert before.targets_kw == pytest.approx({"WP": 20, "WB": 0})
    assert before.state.last_switch_action_s == 0

    second = run_controller(
        sample(time=5, grid=130, meter=5), devices, before.state,
    )
    assert second.targets_kw == pytest.approx({"WP": 20, "WB": 10})
    assert second.projected_grid_kw == pytest.approx(140)
    assert second.state.last_switch_action_s == 5


def test_timer_does_not_accept_stale_grid_sample_after_five_seconds():
    devices = [load("WP", 1), load("WB", 2, maximum=11, minimum=4.14)]
    first = run_controller(sample(), devices)
    stale = run_controller(
        sample(time=5, grid=130, meter=0), devices, first.state,
    )
    assert stale.targets_kw == pytest.approx({"WP": 20, "WB": 0})
    assert stale.state.last_switch_action_s == 0
    fresh = run_controller(
        sample(time=5.25, grid=130, meter=5.2), devices, stale.state,
    )
    assert fresh.targets_kw == pytest.approx({"WP": 20, "WB": 10})


def test_over_pmax_sheds_immediately_even_inside_five_second_timer():
    devices = [load("WP", 1)]
    first = run_controller(sample(), devices)
    emergency = run_controller(
        sample(time=1, grid=145, meter=1), devices, first.state,
    )
    assert emergency.targets_kw["WP"] == pytest.approx(15)
    assert emergency.projected_grid_kw == pytest.approx(140)


def test_normal_off_commands_are_sequential_and_reverse_priority():
    devices = [
        load("WP", 1, request=0),
        load("WB", 2, request=0, maximum=11),
    ]
    state = ControllerState(last_targets_kw={"WP": 10, "WB": 6})
    first = run_controller(sample(grid=130), devices, state)
    assert first.targets_kw == pytest.approx({"WP": 10, "WB": 0})
    early = run_controller(
        sample(time=3, grid=124, meter=3), devices, first.state,
    )
    assert early.targets_kw == pytest.approx({"WP": 10, "WB": 0})
    second = run_controller(
        sample(time=5, grid=124, meter=5), devices, early.state,
    )
    assert second.targets_kw == pytest.approx({"WP": 0, "WB": 0})


def test_turning_off_does_not_require_fresh_meter_if_timer_expired():
    devices = [load("WP", 1, request=0), load("WB", 2, request=0)]
    state = ControllerState(last_targets_kw={"WP": 10, "WB": 6})
    first = run_controller(sample(grid=130), devices, state)
    second = run_controller(
        sample(time=5, grid=130, meter=0), devices, first.state,
    )
    assert second.targets_kw == pytest.approx({"WP": 0, "WB": 0})


def test_hard_limit_reduction_shuts_down_multiple_consumers_without_wait():
    devices = [
        load("WP", 1, request=20, minimum=5),
        load("WB", 2, request=11, maximum=11, minimum=4.14),
    ]
    state = ControllerState(
        last_targets_kw={"WP": 20, "WB": 11},
        last_switch_action_s=0,
        last_switch_grid_sample_s=0,
    )
    result = run_controller(
        sample(time=1, grid=170, meter=1), devices, state,
    )
    assert result.projected_grid_kw <= 140
    assert result.targets_kw["WP"] < 20
    assert result.targets_kw["WB"] < 11


def test_pv_export_adds_one_equal_wallbox_at_each_step():
    devices = [
        load("WB1", 1, request=11, maximum=11, minimum=4.14),
        load("WB2", 2, request=11, maximum=11, minimum=4.14),
    ]
    first = run_controller(
        sample(grid=-10, pv=30, mode=OperatingMode.SURPLUS), devices,
    )
    assert first.targets_kw == pytest.approx({"WB1": 5, "WB2": 0})
    second = run_controller(
        sample(time=5, grid=-5, meter=5, pv=30,
               mode=OperatingMode.SURPLUS), devices, first.state,
    )
    assert second.targets_kw == pytest.approx({"WB1": 5, "WB2": 5})
    assert second.projected_grid_kw <= 0


def test_pv_grid_import_triggers_urgent_reduction_without_wait():
    devices = [
        load("WB1", 1, request=11, maximum=11, minimum=4.14),
        load("WB2", 2, request=11, maximum=11, minimum=4.14),
    ]
    state = ControllerState(
        last_targets_kw={"WB1": 5, "WB2": 5},
        last_switch_action_s=0, last_switch_grid_sample_s=0,
    )
    result = run_controller(
        sample(time=1, grid=8, meter=1, pv=30,
               mode=OperatingMode.SURPLUS), devices, state,
    )
    assert result.projected_grid_kw <= 0
    assert result.targets_kw["WB1"] <= 5
    assert result.targets_kw["WB2"] <= 5


def test_invalid_timer_is_rejected():
    with pytest.raises(ValueError):
        run_controller(sample(interval=-1), [load("WP", 1)])
    with pytest.raises(ValueError):
        run_controller(
            ControllerInputs(grid_kw=10, grid_limit_kw=140,
                             switch_interval_s=float("nan")),
            [load("WP", 1)],
        )


def test_legacy_pure_controller_without_explicit_timer_remains_deterministic():
    devices = [load("WP", 1), load("WB", 2, maximum=11)]
    result = run_controller(
        ControllerInputs(grid_kw=110, grid_limit_kw=140), devices,
    )
    assert result.targets_kw["WP"] == pytest.approx(20)
    assert result.targets_kw["WB"] == pytest.approx(10)


def test_coordinator_enables_five_seconds_and_real_meter_sample():
    from pathlib import Path
    root = Path(__file__).parent / "custom_components" / "power_manager"
    coordinator = (root / "coordinator.py").read_text(encoding="utf-8")
    const = (root / "const.py").read_text(encoding="utf-8")
    assert "SEQUENTIAL_SWITCH_INTERVAL_SECONDS = 5.0" in const
    assert "switch_interval_s=SEQUENTIAL_SWITCH_INTERVAL_SECONDS" in coordinator
    assert "grid_sample_s=grid_sample_s" in coordinator
    assert "cycle_now_s - max(0.0, grid_age_s)" in coordinator


def test_safety_limit_is_not_hardcoded_to_140_kw():
    devices = [load("WP", 1, request=5, maximum=5)]
    first = run_controller(
        sample(grid=15, limit=20), devices,
    )
    assert first.targets_kw["WP"] == 5
    overload = run_controller(
        sample(time=1, grid=24, meter=1, limit=20),
        devices, first.state,
    )
    assert overload.targets_kw["WP"] <= 1
