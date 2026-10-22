from datetime import (
    datetime,
    timedelta,
    timezone,
)
import math

import pytest

from custom_components.power_manager.measurements import (
    MeasurementError,
    measurement_age_seconds,
    measurement_is_fresh,
    percentage_value,
    power_to_kw,
)


def test_power_watt_is_converted_to_kw():
    result = power_to_kw(
        12500.0,
        "W",
    )

    assert result == pytest.approx(
        12.5
    )


def test_power_kw_remains_kw():
    result = power_to_kw(
        12.5,
        "kW",
    )

    assert result == pytest.approx(
        12.5
    )


def test_power_mw_is_converted_to_kw():
    result = power_to_kw(
        0.0125,
        "MW",
    )

    assert result == pytest.approx(
        12.5
    )


def test_negative_power_sign_is_preserved():
    result = power_to_kw(
        -7.5,
        "kW",
    )

    assert result == pytest.approx(
        -7.5
    )


def test_power_sign_can_be_inverted():
    result = power_to_kw(
        -7.5,
        "kW",
        invert=True,
    )

    assert result == pytest.approx(
        7.5
    )


def test_unknown_power_unit_is_rejected():
    with pytest.raises(
        MeasurementError
    ):
        power_to_kw(
            10.0,
            "VA",
        )


def test_non_finite_measurement_is_rejected():
    with pytest.raises(
        MeasurementError
    ):
        power_to_kw(
            math.nan,
            "kW",
        )


def test_percentage_sensor_is_accepted():
    result = percentage_value(
        67.5,
        "%",
    )

    assert result == pytest.approx(
        67.5
    )


def test_percentage_outside_range_is_rejected():
    with pytest.raises(
        MeasurementError
    ):
        percentage_value(
            120.0,
            "%",
        )


def test_measurement_age_is_calculated():
    now = datetime(
        2026,
        10,
        14,
        12,
        0,
        10,
        tzinfo=timezone.utc,
    )

    last_reported = (
        now
        - timedelta(
            seconds=4.5
        )
    )

    result = measurement_age_seconds(
        last_reported,
        now,
    )

    assert result == pytest.approx(
        4.5
    )


def test_future_measurement_timestamp_is_clamped_to_zero():
    now = datetime(
        2026,
        10,
        14,
        12,
        0,
        0,
        tzinfo=timezone.utc,
    )

    last_reported = (
        now
        + timedelta(
            seconds=2.0
        )
    )

    result = measurement_age_seconds(
        last_reported,
        now,
    )

    assert result == pytest.approx(
        0.0
    )


def test_measurement_is_fresh_below_timeout():
    assert (
        measurement_is_fresh(
            age_s=4.0,
            timeout_s=5.0,
        )
        is True
    )


def test_measurement_is_fresh_exactly_at_timeout():
    assert (
        measurement_is_fresh(
            age_s=5.0,
            timeout_s=5.0,
        )
        is True
    )


def test_measurement_is_stale_above_timeout():
    assert (
        measurement_is_fresh(
            age_s=5.01,
            timeout_s=5.0,
        )
        is False
    )


def test_zero_timeout_is_rejected():
    with pytest.raises(
        MeasurementError
    ):
        measurement_is_fresh(
            age_s=1.0,
            timeout_s=0.0,
        )


def test_household_watts_convert_to_kw_without_storage_inputs():
    assert power_to_kw(50.0, "W", label="Hausgrundverbrauch") == pytest.approx(0.05)
    assert power_to_kw(38550.0, "W", label="PV-Erzeugung") == pytest.approx(38.55)


def test_household_sensor_invalid_measurement_raises():
    with pytest.raises(MeasurementError):
        power_to_kw(float("nan"), "kW", label="Hausgrundverbrauch")
    with pytest.raises(MeasurementError):
        power_to_kw(0.05, None, label="Hausgrundverbrauch")
