"""Confirm that physically measured power reductions, not HA writes,
are required before allowing additional load increases."""
import pytest

from custom_components.power_manager.feedback import PendingReduction


def test_measured_reduction_confirms_early():
    check = PendingReduction(target_kw=3.0, deadline_s=15.0)
    assert check.assess(now_s=11, actual_kw=3.1, tolerance_kw=0.2) == "confirmed"


def test_wait_until_device_settled():
    check = PendingReduction(target_kw=0.0, deadline_s=15.0)
    assert check.assess(now_s=11, actual_kw=7, tolerance_kw=0.1) == "pending"
    assert check.assess(now_s=15, actual_kw=7, tolerance_kw=0.1) == "failed"


def test_missing_fresh_measurement_is_not_positive_confirmation():
    check = PendingReduction(target_kw=0.0, deadline_s=15.0)
    assert check.assess(now_s=14, actual_kw=None, tolerance_kw=0.1) == "pending"
    assert check.assess(now_s=16, actual_kw=None, tolerance_kw=0.1) == "failed"


def test_threshold_is_configurable_and_in_physical_kw():
    check = PendingReduction(target_kw=10, deadline_s=20)
    assert check.assess(now_s=20, actual_kw=10.3, tolerance_kw=0.2) == "failed"
    assert check.assess(now_s=20, actual_kw=10.3, tolerance_kw=0.4) == "confirmed"


def test_invalid_feedback_tolerance_never_grants_confirmation():
    check = PendingReduction(target_kw=0, deadline_s=1)
    for tolerance in (-1, float("nan")):
        with pytest.raises(ValueError):
            check.assess(now_s=2, actual_kw=0, tolerance_kw=tolerance)


def test_nonfinite_actual_does_not_confirm_device():
    check = PendingReduction(target_kw=0, deadline_s=1)
    assert check.assess(
        now_s=2, actual_kw=float("nan"), tolerance_kw=0.1,
    ) == "failed"


def test_live_control_requires_grid_not_per_load_actual_sensor():
    from pathlib import Path
    source = (Path(__file__).parent / "custom_components" /
              "power_manager" / "coordinator.py").read_text(encoding="utf-8")
    assert "Live-Regelung benötigt eine echte Istleistungs-Entity" not in source
    assert "Actual-power sensors are optional" in source
    assert "self._pending_reductions" in source
    assert "Leistungsreduzierung auf" in source
