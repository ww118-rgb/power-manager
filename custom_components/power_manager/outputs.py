"""Pure output conversion logic for Power Manager actuators."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from .allocator import EPSILON
from .const import (
    DEFAULT_OUTPUT_VALUE_MODE,
    OUTPUT_VALUE_MODE_LINEAR,
    OUTPUT_VALUE_MODE_POWER,
    LOAD_TYPE_EVSE,
    LOAD_TYPE_MODULATING,
    LOAD_TYPE_SWITCH,
    OUTPUT_UNIT_KW,
    OUTPUT_UNIT_MW,
    OUTPUT_UNIT_W,
)


class OutputConversionError(ValueError):
    """Raised when a target cannot safely be converted to an actuator value."""


@dataclass(frozen=True, slots=True)
class OutputPlan:
    """Device-independent output plan for one load."""

    numeric_value: float | None = None
    numeric_unit: str | None = None
    enabled: bool | None = None


def kw_to_power_value(target_kw: float, unit: str) -> float:
    """Convert kW to a supported actuator power unit."""

    if not isfinite(target_kw):
        raise OutputConversionError("Target power must be finite")

    if unit == OUTPUT_UNIT_W:
        return target_kw * 1000.0
    if unit == OUTPUT_UNIT_KW:
        return target_kw
    if unit == OUTPUT_UNIT_MW:
        return target_kw / 1000.0

    raise OutputConversionError(f"Unsupported actuator power unit: {unit}")


def evse_target_to_current_a(
    target_kw: float,
    *,
    phases: int,
    voltage_v: float,
    min_current_a: float,
    max_current_a: float,
    pause_current_a: float,
) -> float:
    """Convert an EVSE power target to amps without exceeding the target."""

    if not isfinite(target_kw) or target_kw < 0.0:
        raise OutputConversionError("EVSE target must be a finite non-negative value")
    if phases <= 0 or voltage_v <= 0.0:
        raise OutputConversionError("EVSE phases and voltage must be positive")
    if min_current_a <= 0.0 or max_current_a < min_current_a:
        raise OutputConversionError("Invalid EVSE current range")
    if pause_current_a < 0.0 or pause_current_a >= min_current_a:
        raise OutputConversionError("Invalid EVSE pause current")

    if target_kw <= EPSILON:
        return pause_current_a

    current_a = target_kw * 1000.0 / (phases * voltage_v)

    # Never round a target below the technical minimum upward: that could cause
    # a real grid import above the controller's calculated PMAX budget.
    if current_a + EPSILON < min_current_a:
        return pause_current_a

    if current_a > max_current_a + EPSILON:
        raise OutputConversionError(
            "EVSE target requires more than the configured maximum current"
        )

    return min(current_a, max_current_a)


def build_output_plan(
    *,
    load_type: str,
    target_kw: float,
    power_unit: str = OUTPUT_UNIT_KW,
    safe_output_value: float = 0.0,
    evse_phases: int = 3,
    evse_voltage_v: float = 230.0,
    evse_min_current_a: float = 6.0,
    evse_max_current_a: float = 16.0,
    evse_pause_current_a: float = 0.01,
    output_value_mode: str = DEFAULT_OUTPUT_VALUE_MODE,
    output_scale: float = 1.0,
    output_offset: float = 0.0,
    forbidden_value: float | None = None,
    evse_zero_unlimited: bool = False,
) -> OutputPlan:
    """Convert one kW target into a generic output plan."""

    if not isfinite(target_kw) or target_kw < 0.0:
        raise OutputConversionError("Target power must be finite and non-negative")

    for name, value in (
        ("output_scale", output_scale),
        ("output_offset", output_offset),
        ("safe_output_value", safe_output_value),
    ):
        if not isfinite(value):
            raise OutputConversionError(f"{name} must be finite")
    if forbidden_value is not None and not isfinite(forbidden_value):
        raise OutputConversionError("forbidden command must be finite")

    enabled = target_kw > EPSILON

    if load_type == LOAD_TYPE_SWITCH:
        return OutputPlan(enabled=enabled)

    if load_type == LOAD_TYPE_EVSE:
        if evse_zero_unlimited and abs(evse_pause_current_a) <= EPSILON:
            raise OutputConversionError(
                "0 A releases the EVSE current limit; use a non-zero safe pause command"
            )
        current_a = evse_target_to_current_a(
            target_kw,
            phases=evse_phases,
            voltage_v=evse_voltage_v,
            min_current_a=evse_min_current_a,
            max_current_a=evse_max_current_a,
            pause_current_a=evse_pause_current_a,
        )
        if forbidden_value is not None and abs(current_a - forbidden_value) <= EPSILON:
            raise OutputConversionError("EVSE output maps to a forbidden device command")
        evse_enabled = current_a + EPSILON >= evse_min_current_a
        return OutputPlan(
            numeric_value=current_a,
            numeric_unit="A",
            enabled=evse_enabled,
        )

    if load_type == LOAD_TYPE_MODULATING:
        if output_value_mode == OUTPUT_VALUE_MODE_POWER:
            numeric_value = (
                kw_to_power_value(target_kw, power_unit)
                if enabled else safe_output_value
            )
            unit = power_unit
        elif output_value_mode == OUTPUT_VALUE_MODE_LINEAR:
            if output_scale <= 0.0:
                raise OutputConversionError(
                    "Linear device mapping requires a positive scale"
                )
            numeric_value = (
                target_kw * output_scale + output_offset
                if enabled else safe_output_value
            )
            unit = "device"
        else:
            raise OutputConversionError("Unknown numeric device command profile")
        if not isfinite(numeric_value):
            raise OutputConversionError("Device command overflow")
        if forbidden_value is not None and abs(numeric_value - forbidden_value) <= EPSILON:
            raise OutputConversionError(
                "Calculated command matches a forbidden device value"
            )
        return OutputPlan(
            numeric_value=numeric_value,
            numeric_unit=unit,
            enabled=enabled,
        )

    raise OutputConversionError(f"Unsupported load type: {load_type}")
