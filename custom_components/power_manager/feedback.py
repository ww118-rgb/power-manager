"""Plant-independent confirmation of physical consumer power reductions.

A service-call acknowledgement is NOT a proof of a device reaching a safe
power state. Confirmation requires a *fresh* actual-power reading.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True, slots=True)
class PendingReduction:
    target_kw: float
    deadline_s: float

    def assess(
        self,
        *,
        now_s: float,
        actual_kw: float | None,
        tolerance_kw: float,
    ) -> str:
        """Return pending, confirmed or failed for measured load reaction.

        Confirmation may happen before the deadline. Failure is declared
        only after it, including if the fresh actual reading is missing.
        """
        if tolerance_kw < 0.0 or not isfinite(tolerance_kw):
            raise ValueError("Feedback tolerance must be finite and nonnegative")
        if (
            actual_kw is not None
            and isfinite(actual_kw)
            and actual_kw <= self.target_kw + tolerance_kw
        ):
            return "confirmed"
        if now_s < self.deadline_s:
            return "pending"
        return "failed"
