"""Power Manager 4.0 – one deterministic grid/PV controller.

Allocation rules inherited from stable 3.1.1: PMAX, priority, fair groups,
technical minima, optional on/off and settling times. Modern 3.3.x adapter
performs device-unit conversion AFTER this pure controller.

Grid meter = sole authoritative control measurement. Optional individual
power measurements improve the baseline; no device sensor is mandatory.
Autonomous battery has NO connection to this module.
"""
from __future__ import annotations

from math import isfinite

from models import (
    ControllableLoad, ControllerInputs, ControllerResult,
    ControllerState, LoadRuntimeState, OperatingMode,
)
from allocator import EPSILON, allocate_power


def _finite(name: str, value: float) -> None:
    if not isfinite(value):
        raise ValueError(f"{name} muss endlich sein.")


def _validate(inputs: ControllerInputs, loads: list[ControllableLoad]) -> None:
    for name in ("grid_kw", "grid_limit_kw", "pv_kw",
                 "grid_reserve_kw", "grid_growth_margin_kw", "now_s"):
        _finite(name, getattr(inputs, name))
    if inputs.grid_limit_kw <= 0:
        raise ValueError("PMAX muss positiv sein.")
    if not 0 <= inputs.grid_reserve_kw < inputs.grid_limit_kw:
        raise ValueError("Netzreserve muss zwischen 0 und PMAX liegen.")
    if inputs.grid_growth_margin_kw < 0 or inputs.now_s < 0:
        raise ValueError("Freigabepuffer und Zeit dürfen nicht negativ sein.")
    names = set()
    for load in loads:
        if not load.name or load.name in names:
            raise ValueError("Verbrauchernamen müssen eindeutig und gesetzt sein.")
        names.add(load.name)
        if load.priority < 1:
            raise ValueError(f"{load.name}: Priorität muss mindestens 1 sein.")
        for key in (
            "requested_kw", "min_kw", "max_kw", "start_margin_kw",
            "stop_margin_kw", "min_on_time_s", "min_off_time_s",
            "settling_time_s",
        ):
            value = getattr(load, key)
            _finite(f"{load.name}.{key}", value)
            if value < 0:
                raise ValueError(f"{load.name}.{key} darf nicht negativ sein.")
        if load.actual_kw is not None:
            _finite(f"{load.name}.actual_kw", load.actual_kw)
            if load.actual_kw < 0:
                raise ValueError(f"{load.name}: Istleistung darf nicht negativ sein.")
        if load.min_kw > load.max_kw:
            raise ValueError(f"{load.name}: Mindestleistung > Höchstleistung.")
        if load.stop_margin_kw > load.start_margin_kw:
            raise ValueError(f"{load.name}: Stopreserve > Startreserve.")


def _known_power(
    loads: list[ControllableLoad], state: ControllerState,
) -> tuple[float, float]:
    measured = 0.0
    estimated = 0.0
    for load in loads:
        if load.actual_kw is not None:
            measured += load.actual_kw
        else:
            estimated += max(0.0, state.last_targets_kw.get(load.name, 0.0))
    return measured, estimated


def _previous_power(load: ControllableLoad, state: ControllerState) -> float:
    # A valid device Istwert is optional, not a requirement for the controller.
    # The larger known value is safer before adding NEW load.
    return max(
        0.0,
        state.last_targets_kw.get(load.name, 0.0),
        load.actual_kw if load.actual_kw is not None else 0.0,
    )


def _admit_increases(
    selected: list[ControllableLoad],
    desired: dict[str, float],
    state: ControllerState,
    room_kw: float,
    mode: OperatingMode,
) -> dict[str, float]:
    """Apply one grid-meter headroom cap; reductions are always immediate.

    Equivalent consumers of the SAME priority in NORMAL (all PV consumers in
    SURPLUS) share their admitted growth equally, so a previous 6/6.5 kW
    imbalance cannot persist forever. The algorithm NEVER spends a device
    reduction until the next grid reading shows physical headroom.
    """
    targets = dict(desired)
    groups: dict[tuple, list[ControllableLoad]] = {}
    for load in sorted(selected, key=lambda item: item.priority if mode == OperatingMode.NORMAL else 0):
        key = (
            load.priority if mode == OperatingMode.NORMAL else 0,
            load.requested_kw, load.min_kw, load.max_kw,
            load.can_modulate, load.available,
            # Device timing rules may differ; do not override them in a group.
            load.start_margin_kw, load.stop_margin_kw,
            load.min_on_time_s, load.min_off_time_s, load.settling_time_s,
        )
        groups.setdefault(key, []).append(load)

    remaining = max(0.0, room_kw)
    for group in groups.values():
        ideal = [desired.get(load.name, 0.0) for load in group]
        previous = [_previous_power(load, state) for load in group]
        share_equally = (
            len(group) > 1
            and group[0].available
            and group[0].can_modulate
            and min(ideal) > EPSILON
            and max(ideal) - min(ideal) < EPSILON
        )
        if share_equally:
            target = min(ideal)
            needed = sum(max(0.0, target - old) for old in previous)
            if needed > remaining + EPSILON:
                # Equalize by first curtailing the higher consumer, rather
                # than borrowing still-unconfirmed reductions from the grid.
                lo, hi = 0.0, target
                for _ in range(35):
                    mid = (lo + hi) / 2
                    if sum(max(0.0, mid - p) for p in previous) <= remaining:
                        lo = mid
                    else:
                        hi = mid
                target = lo
            if target + EPSILON >= group[0].min_kw:
                for load in group:
                    targets[load.name] = target
                remaining = max(
                    0.0,
                    remaining - sum(max(0.0, target - p) for p in previous),
                )
                continue

        # Different limits/needs, or not enough power to start every peer:
        # the stable 3.1.1 allocator's admission order and minima win.
        for load, proposed, old in zip(group, ideal, previous):
            if proposed <= old + EPSILON:
                continue  # PMAX reduction/holding never waits.
            accepted = min(proposed, old + remaining)
            if accepted + EPSILON < load.min_kw:
                accepted = 0.0
            elif not load.can_modulate and accepted + EPSILON < proposed:
                accepted = min(proposed, old) if old > EPSILON else 0.0
            targets[load.name] = accepted
            remaining = max(0.0, remaining - max(0.0, accepted - old))
    return targets


def _next_state(
    selected: list[ControllableLoad], targets: dict[str, float],
    state: ControllerState, now: float,
) -> ControllerState:
    commands = dict(state.last_targets_kw)
    runtime = dict(state.load_states)
    for load in selected:
        if load.name not in targets:
            continue
        value = max(0.0, min(targets[load.name], load.max_kw))
        previous = runtime.get(load.name, LoadRuntimeState(
            is_on=commands.get(load.name, 0.0) > EPSILON,
            last_target_kw=commands.get(load.name, 0.0),
        ))
        changed = abs(value - previous.last_target_kw) > EPSILON
        on = value > EPSILON
        runtime[load.name] = LoadRuntimeState(
            is_on=on,
            last_target_kw=value,
            last_switch_s=now if on != previous.is_on else previous.last_switch_s,
            last_target_change_s=now if changed else previous.last_target_change_s,
            settling_until_s=(now + load.settling_time_s if changed
                              else previous.settling_until_s),
        )
        commands[load.name] = value
    return ControllerState(last_targets_kw=commands, load_states=runtime)


def run_controller(
    inputs: ControllerInputs,
    loads: list[ControllableLoad],
    state: ControllerState | None = None,
) -> ControllerResult:
    """Calculate one deterministic control cycle without touching hardware."""
    state = state or ControllerState()
    _validate(inputs, loads)
    if inputs.mode == OperatingMode.NORMAL:
        selected = [x for x in loads if x.peak_shaving_enabled]
    elif inputs.mode == OperatingMode.SURPLUS:
        selected = [x for x in loads if x.peak_shaving_enabled and x.surplus_enabled]
    else:
        raise ValueError(f"Unbekannter Betriebsmodus: {inputs.mode}")

    measured, estimated = _known_power(selected, state)
    controlled = measured + estimated
    # Same proven base-load identity as 3.1.1 NORMAL. Battery is excluded.
    base = inputs.grid_kw - controlled
    limit = inputs.grid_limit_kw - inputs.grid_reserve_kw
    peak_budget = max(0.0, limit - base)
    cannot_reach = base > limit + EPSILON

    if inputs.mode == OperatingMode.NORMAL:
        budget = peak_budget
        surplus_budget = 0.0
        export = 0.0
        growth_room = max(
            0.0, limit - inputs.grid_kw - inputs.grid_growth_margin_kw,
        )
        candidates = selected
    else:
        # PV generation alone is not free power. Only metered grid export
        # PLUS the existing PV consumer power can form the PV budget.
        # This avoids oscillating to OFF whenever existing loads reduce
        # grid export to exactly zero. Autonomous battery stays untouched.
        pv_present = inputs.pv_kw > EPSILON
        export = max(0.0, -inputs.grid_kw) if pv_present else 0.0
        surplus_budget = max(0.0, controlled - inputs.grid_kw) if pv_present else 0.0
        budget = min(peak_budget, surplus_budget)
        growth_room = export
        # Fair in SURPLUS regardless of NORMAL priority; preserve all other
        # technical bounds/timing parameters from the original load.
        from dataclasses import replace
        candidates = [replace(load, priority=1) for load in selected]

    requested_targets = allocate_power(
        loads=candidates, available_budget_kw=budget,
        state=state, now_s=inputs.now_s,
    )
    final_targets = _admit_increases(
        selected, requested_targets, state, growth_room, inputs.mode,
    )
    total = sum(final_targets.values())
    projected = base + total
    if not cannot_reach and projected > limit + EPSILON:
        raise RuntimeError("Reglerfehler: prognostizierter Netzbezug über PMAX.")

    next_state = _next_state(selected, final_targets, state, inputs.now_s)
    wanted = sum(
        min(load.max_kw, max(0.0, load.requested_kw))
        for load in selected if load.available
    )
    limited = sum(
        load.available and min(load.max_kw, load.requested_kw)
        > final_targets.get(load.name, 0.0) + EPSILON
        for load in selected
    )
    settling = sum(
        t.settling_until_s is not None and inputs.now_s < t.settling_until_s
        for t in next_state.load_states.values()
    )
    return ControllerResult(
        targets_kw=final_targets,
        base_load_kw=base,
        measured_controlled_power_kw=measured,
        estimated_controlled_power_kw=estimated,
        controlled_power_for_calculation_kw=controlled,
        effective_grid_limit_kw=limit,
        peak_budget_kw=peak_budget,
        raw_surplus_budget_kw=export,
        surplus_budget_kw=surplus_budget,
        available_budget_kw=budget,
        unused_budget_kw=max(0.0, budget - total),
        projected_grid_kw=projected,
        grid_headroom_kw=limit - projected,
        total_requested_kw=wanted,
        total_target_kw=total,
        active_load_count=sum(x > EPSILON for x in final_targets.values()),
        limited_load_count=limited,
        settling_load_count=settling,
        peak_shaving_active=(inputs.grid_kw > limit + EPSILON or wanted > peak_budget + EPSILON),
        surplus_active=inputs.mode == OperatingMode.SURPLUS,
        hard_limit_exceeded_now=inputs.grid_kw > limit + EPSILON,
        grid_limit_unachievable=cannot_reach,
        state=next_state,
    )
