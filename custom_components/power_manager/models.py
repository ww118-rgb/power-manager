"""Pure data contracts for the Power Manager 4.0 controller.

The battery is deliberately absent: it operates autonomously and is never
an input into power allocation. Optional battery entities belong to HA
telemetry only, not this model.
"""
from dataclasses import dataclass, field
from enum import Enum


class OperatingMode(str, Enum):
    NORMAL = "normal"
    SURPLUS = "surplus"


@dataclass
class ControllableLoad:
    name: str
    priority: int
    requested_kw: float
    min_kw: float
    max_kw: float
    actual_kw: float | None = None
    available: bool = True
    can_modulate: bool = True
    can_shutdown: bool = True
    peak_shaving_enabled: bool = True
    surplus_enabled: bool = True
    start_margin_kw: float = 0.0
    stop_margin_kw: float = 0.0
    min_on_time_s: float = 0.0
    min_off_time_s: float = 0.0
    settling_time_s: float = 0.0


@dataclass
class LoadRuntimeState:
    is_on: bool = False
    last_target_kw: float = 0.0
    last_switch_s: float | None = None
    last_target_change_s: float | None = None
    settling_until_s: float | None = None


@dataclass
class ControllerInputs:
    # Positive grid_kw = import; negative = real metered export.
    grid_kw: float
    grid_limit_kw: float
    pv_kw: float = 0.0
    grid_reserve_kw: float = 0.0
    # Optional noise margin for NEW increases only. Not an additional PMAX.
    grid_growth_margin_kw: float = 0.0
    mode: OperatingMode = OperatingMode.NORMAL
    now_s: float = 0.0


@dataclass
class ControllerState:
    last_targets_kw: dict[str, float] = field(default_factory=dict)
    load_states: dict[str, LoadRuntimeState] = field(default_factory=dict)


@dataclass
class ControllerResult:
    targets_kw: dict[str, float] = field(default_factory=dict)
    base_load_kw: float = 0.0
    measured_controlled_power_kw: float = 0.0
    estimated_controlled_power_kw: float = 0.0
    controlled_power_for_calculation_kw: float = 0.0
    effective_grid_limit_kw: float = 0.0
    peak_budget_kw: float = 0.0
    raw_surplus_budget_kw: float = 0.0
    surplus_budget_kw: float = 0.0
    available_budget_kw: float = 0.0
    unused_budget_kw: float = 0.0
    projected_grid_kw: float = 0.0
    grid_headroom_kw: float = 0.0
    total_requested_kw: float = 0.0
    total_target_kw: float = 0.0
    active_load_count: int = 0
    limited_load_count: int = 0
    settling_load_count: int = 0
    peak_shaving_active: bool = False
    surplus_active: bool = False
    hard_limit_exceeded_now: bool = False
    grid_limit_unachievable: bool = False
    state: ControllerState = field(default_factory=ControllerState)
