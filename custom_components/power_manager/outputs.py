"""Pure output conversion logic for Power Manager actuators."""

from __future__ import annotations

from dataclasses import dataclass
import json
from math import floor, isfinite

from .allocator import EPSILON
from .const import (
    DEFAULT_OUTPUT_VALUE_MODE,
    OUTPUT_VALUE_MODE_LINEAR,
    OUTPUT_VALUE_MODE_POWER,
    OUTPUT_VALUE_MODE_STEPS,
    LOAD_TYPE_EVSE,
    LOAD_TYPE_MODULATING,
    LOAD_TYPE_SWITCH,
    OUTPUT_UNIT_KW,
    OUTPUT_UNIT_MW,
    OUTPUT_UNIT_W,
    EVSE_OUTPUT_AMPERE, EVSE_OUTPUT_WATT, EVSE_OUTPUT_KW,
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
    step_current_a: float = 1.0,
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
    if not isfinite(step_current_a) or step_current_a <= 0.0:
        raise OutputConversionError("Invalid EVSE ampere command step")

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

    # Never send fractional currents when device demands whole ampere
    # commands. Always round DOWN; rounding up can violate the power budget.
    current_a = floor((min(current_a, max_current_a) + 1e-9)
                      / step_current_a) * step_current_a
    if current_a + 1e-9 < min_current_a:
        return pause_current_a
    return current_a


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
    evse_output_format: str = EVSE_OUTPUT_AMPERE,
    evse_current_step_a: float = 1.0,
    evse_power_step_w: float = 1000.0,
    evse_pause_power_value: float = 0.0,
    output_value_mode: str = DEFAULT_OUTPUT_VALUE_MODE,
    output_scale: float = 1.0,
    output_offset: float = 0.0,
    forbidden_value: float | None = None,
    evse_zero_unlimited: bool = False,
    output_steps_json: str = "[]",
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
        if evse_output_format not in (EVSE_OUTPUT_AMPERE, EVSE_OUTPUT_WATT, EVSE_OUTPUT_KW):
            raise OutputConversionError("Choose EVSE command format A, W or kW")
        if (evse_phases <= 0 or not isfinite(evse_voltage_v)
                or evse_voltage_v <= 0 or
                not isfinite(evse_min_current_a) or evse_min_current_a <= 0 or
                not isfinite(evse_max_current_a) or
                evse_max_current_a < evse_min_current_a):
            raise OutputConversionError("Invalid EVSE electrical parameters")
        if evse_output_format == EVSE_OUTPUT_AMPERE:
            if evse_zero_unlimited and abs(evse_pause_current_a) <= EPSILON:
                raise OutputConversionError(
                    "0 A releases the EVSE limit; require verified nonzero pause"
                )
            numeric_value = evse_target_to_current_a(
                target_kw, phases=evse_phases, voltage_v=evse_voltage_v,
                min_current_a=evse_min_current_a,
                max_current_a=evse_max_current_a,
                pause_current_a=evse_pause_current_a,
                step_current_a=evse_current_step_a,
            )
            enabled = numeric_value + EPSILON >= evse_min_current_a
            unit = EVSE_OUTPUT_AMPERE
        else:
            # Power-controlled charging uses *physical* minimum and maximum
            # dictated by phases and amps, but sends watts or kW to the device.
            if (not isfinite(evse_power_step_w) or evse_power_step_w <= 0
                    or not isfinite(evse_pause_power_value)
                    or evse_pause_power_value < 0):
                raise OutputConversionError("Invalid EVSE power step or pause code")
            min_w = evse_phases * evse_voltage_v * evse_min_current_a
            max_w = evse_phases * evse_voltage_v * evse_max_current_a
            target_w = target_kw * 1000.0
            if target_w > max_w + 1e-6:
                raise OutputConversionError("EVSE target exceeds current-derived cap")
            command_w = (
                floor((target_w + 1e-6) / evse_power_step_w)
                * evse_power_step_w
                if target_w >= min_w - 1e-6 else 0.0
            )
            enabled = command_w >= min_w - 1e-6
            numeric_value = (
                command_w if evse_output_format == EVSE_OUTPUT_WATT
                else command_w / 1000.0
            ) if enabled else evse_pause_power_value
            unit = evse_output_format
        if forbidden_value is not None and abs(numeric_value - forbidden_value) <= EPSILON:
            raise OutputConversionError("EVSE output maps to a forbidden device command")
        return OutputPlan(
            numeric_value=numeric_value,
            numeric_unit=unit,
            enabled=enabled,
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
        elif output_value_mode == OUTPUT_VALUE_MODE_STEPS:
            try:
                stages = json.loads(output_steps_json)
            except (TypeError, ValueError) as err:
                raise OutputConversionError("Invalid JSON for numeric stages") from err
            if not isinstance(stages, list) or not stages:
                raise OutputConversionError("Numeric stages require at least one stage")
            try:
                pairs = [(float(entry["kw"]), float(entry["code"])) for entry in stages]
            except (KeyError, TypeError, ValueError) as err:
                raise OutputConversionError("Stages must contain kw and code") from err
            if (
                any(not (isfinite(kw) and isfinite(code) and kw > 0) for kw, code in pairs)
                or len(set(kw for kw, _ in pairs)) != len(pairs)
                or pairs != sorted(pairs)
            ):
                raise OutputConversionError("Stages must be finite, positive, unique and sorted")
            selected = [code for kw, code in pairs if kw <= target_kw + EPSILON]
            if not selected:
                numeric_value = safe_output_value
                enabled = False
            else:
                numeric_value = selected[-1]
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
