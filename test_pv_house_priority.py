"""PV-priority regression: allocate measured production minus uncontrollable house use.

No storage readings, storage commands, hybrid gates or inferred inverter behavior.
"""
from pathlib import Path

import pytest

from controller import run_controller
from models import ControllableLoad, ControllerInputs, ControllerState, OperatingMode


def device(name, priority, limit, minimum=1):
    return ControllableLoad(
        name=name, priority=priority, requested_kw=limit,
        min_kw=minimum, max_kw=limit,
    )


def sample(grid=0, pv=38.6, house=0.05, *, now=0, meter=0, interval=0):
    return ControllerInputs(
        grid_kw=grid, grid_limit_kw=140, pv_kw=pv, house_kw=house,
        mode=OperatingMode.SURPLUS, now_s=now,
        switch_interval_s=interval, grid_sample_s=meter,
    )


def test_screenshot_zero_grid_export_does_not_prevent_pv_dispatch():
    # Simulator 13:25: PV 38.60, house 0.05, grid 0.00.
    # Independent metering supports 38.55 kW PV after base consumption.
    wp = device("WP", 1, 20)
    wb = device("WB", 2, 11, minimum=4.14)
    result = run_controller(sample(), [wp, wb])
    assert result.surplus_budget_kw == pytest.approx(38.55)
    assert result.targets_kw == pytest.approx({"WP": 20, "WB": 11})
    assert result.available_budget_kw == pytest.approx(38.55)


def test_pv_priority_starts_wp_then_wb_after_new_grid_sample():
    wp = device("WP", 1, 20)
    wb = device("WB", 2, 11, minimum=4.14)
    first = run_controller(sample(interval=5), [wp, wb])
    assert first.targets_kw == pytest.approx({"WP": 20, "WB": 0})
    before = run_controller(sample(now=4, meter=4, interval=5), [wp, wb], first.state)
    assert before.targets_kw == pytest.approx(first.targets_kw)
    stale = run_controller(sample(now=5, meter=0, interval=5), [wp, wb], before.state)
    assert stale.targets_kw == pytest.approx(first.targets_kw)
    second = run_controller(sample(now=5.2, meter=5.1, interval=5), [wp, wb], stale.state)
    assert second.targets_kw == pytest.approx({"WP": 20, "WB": 11})


def test_actual_import_sheds_pv_load_immediately_even_inside_timer():
    wp, wb = device("WP", 1, 20), device("WB", 2, 11, minimum=4.14)
    first = run_controller(sample(interval=5), [wp, wb])
    result = run_controller(
        sample(grid=5, now=1, meter=1, interval=5),
        [wp, wb], first.state,
    )
    assert result.surplus_budget_kw == pytest.approx(15)
    assert result.targets_kw["WP"] <= 15 + 1e-6
    assert result.targets_kw["WB"] == 0


def test_no_house_meter_falls_back_to_real_export_only():
    wp = device("WP", 1, 20)
    without_meter = run_controller(sample(house=None), [wp])
    assert without_meter.targets_kw["WP"] == 0
    exporting = run_controller(sample(grid=-7, house=None), [wp])
    assert exporting.targets_kw["WP"] == pytest.approx(7)


def test_insufficient_actual_generation_cannot_start_load():
    wp = device("WP", 1, 20)
    answer = run_controller(sample(pv=2, house=3), [wp])
    assert answer.surplus_budget_kw == 0
    assert answer.targets_kw["WP"] == 0


def test_negative_or_nonfinite_house_readings_rejected():
    for val in (-1, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            run_controller(sample(house=val), [device("WP", 1, 20)])


def test_global_setup_and_ui_contain_no_storage_controls():
    root = Path(__file__).parent / "custom_components" / "power_manager"
    for name in ("controller.py", "coordinator.py", "config_flow.py", "const.py",
                 "sensor.py", "frontend/power-manager-card.js"):
        text = (root / name).read_text(encoding="utf-8").lower()
        assert "battery" not in text and "batterie" not in text and "hybrid" not in text, name
    setup = (root / "config_flow.py").read_text(encoding="utf-8")
    assert "CONF_HOUSE_POWER_ENTITY" in setup
    coordinator = (root / "coordinator.py").read_text(encoding="utf-8")
    assert "house_kw=house_kw" in coordinator
    # Older installations are cleaned via migration, not live storage policy.
    migration = (root / "__init__.py").read_text(encoding="utf-8")
    assert '"battery_power_entity"' in migration
    assert "version=6" in migration
