"""Pure physical-power unit conversions and downward-only device steps.

No Home Assistant dependency: the core can be regression-tested without a
running HA instance. Native device protocol codes are deliberately excluded.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_FLOOR
from math import isfinite

POWER_FACTORS_TO_KW = {"W": 0.001, "kW": 1.0, "MW": 1000.0}


def convert_power_unit(value: float, source: str, target: str) -> float:
    if (
        not isfinite(value)
        or source not in POWER_FACTORS_TO_KW
        or target not in POWER_FACTORS_TO_KW
    ):
        raise ValueError(f"Power unit conversion {source!r} -> {target!r} invalid")
    result = value * POWER_FACTORS_TO_KW[source] / POWER_FACTORS_TO_KW[target]
    if not isfinite(result):
        raise ValueError("Power command overflow")
    return result


def quantize_down(
    value: float,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
    step: float | None = None,
) -> float:
    """Find largest permitted output step at or BELOW a finite target."""
    if not isfinite(value):
        raise ValueError("Nonfinite output command")
    if maximum is not None and value > maximum + 1e-8:
        raise ValueError(f"Output {value:g} is above max {maximum:g}")
    if minimum is not None and value < minimum - 1e-8:
        raise ValueError(f"Output {value:g} is below min {minimum:g}")
    if step is None:
        return value
    try:
        dec_step = Decimal(str(step))
        origin = Decimal(str(minimum if minimum is not None else 0.0))
        val = Decimal(str(value))
        if not (dec_step.is_finite() and dec_step > 0):
            raise ValueError("Output step must be positive")
        count = ((val - origin) / dec_step).to_integral_value(
            rounding=ROUND_FLOOR
        )
        rounded = float(origin + count * dec_step)
    except (ValueError, TypeError, ArithmeticError) as err:
        raise ValueError("Output step is invalid") from err
    if minimum is not None and rounded < minimum - 1e-8:
        raise ValueError("No usable device step within output minimum")
    if rounded > value + 1e-8:
        raise ValueError("Unsafe rounding above requested command")
    return rounded
