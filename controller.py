from dataclasses import replace
from math import isfinite

from allocator import (
    EPSILON,
    allocate_power,
)

from models import (
    ControllableLoad,
    ControllerInputs,
    ControllerResult,
    ControllerState,
    LoadRuntimeState,
    OperatingMode,
)


def _require_finite(
    name: str,
    value: float,
) -> None:
    """
    Verhindert NaN und unendliche Werte.

    Solche Werte könnten sonst sämtliche
    Leistungsberechnungen unbrauchbar machen.
    """

    if not isfinite(value):

        raise ValueError(
            f"{name} muss eine endliche Zahl sein."
        )


def _validate_load(
    load: ControllableLoad,
) -> None:
    """
    Plausibilitätsprüfung eines Verbrauchers.
    """

    if not load.name.strip():

        raise ValueError(
            "Verbrauchername darf nicht leer sein."
        )

    if (
        isinstance(
            load.priority,
            bool,
        )
        or not isinstance(
            load.priority,
            int,
        )
        or load.priority < 1
    ):

        raise ValueError(
            f"{load.name}: Priorität muss eine "
            f"ganze Zahl >= 1 sein."
        )

    numeric_values = {
        "requested_kw": (
            load.requested_kw
        ),
        "min_kw": (
            load.min_kw
        ),
        "max_kw": (
            load.max_kw
        ),
        "start_margin_kw": (
            load.start_margin_kw
        ),
        "stop_margin_kw": (
            load.stop_margin_kw
        ),
        "min_on_time_s": (
            load.min_on_time_s
        ),
        "min_off_time_s": (
            load.min_off_time_s
        ),
        "settling_time_s": (
            load.settling_time_s
        ),
    }

    if load.actual_kw is not None:

        numeric_values[
            "actual_kw"
        ] = load.actual_kw

    for (
        field_name,
        value,
    ) in numeric_values.items():

        _require_finite(
            f"{load.name}: {field_name}",
            value,
        )

    if (
        load.actual_kw is not None
        and load.actual_kw < 0.0
    ):

        raise ValueError(
            f"{load.name}: actual_kw darf "
            f"nicht negativ sein."
        )

    if load.min_kw < 0.0:

        raise ValueError(
            f"{load.name}: min_kw darf "
            f"nicht negativ sein."
        )

    if load.max_kw <= 0.0:

        raise ValueError(
            f"{load.name}: max_kw muss "
            f"größer als 0 sein."
        )

    if load.min_kw > load.max_kw:

        raise ValueError(
            f"{load.name}: min_kw darf nicht "
            f"größer als max_kw sein."
        )

    if (
        load.start_margin_kw < 0.0
        or load.stop_margin_kw < 0.0
    ):

        raise ValueError(
            f"{load.name}: Hysteresemargen "
            f"dürfen nicht negativ sein."
        )

    if (
        load.stop_margin_kw
        > load.start_margin_kw
    ):

        raise ValueError(
            f"{load.name}: stop_margin_kw darf "
            f"nicht größer als start_margin_kw sein."
        )

    if (
        load.min_on_time_s < 0.0
        or load.min_off_time_s < 0.0
        or load.settling_time_s < 0.0
    ):

        raise ValueError(
            f"{load.name}: Zeitwerte dürfen "
            f"nicht negativ sein."
        )

    # Ein Verbraucher, den unser Regler aktiv
    # fürs Peakshaving benutzt, muss im Notfall
    # vollständig abschaltbar sein.
    if (
        load.peak_shaving_enabled
        and not load.can_shutdown
    ):

        raise ValueError(
            f"{load.name}: Eine Peakshaving-Last "
            f"muss abschaltbar sein."
        )

    if (
        load.surplus_enabled
        and not load.can_shutdown
    ):

        raise ValueError(
            f"{load.name}: Eine Überschusslast "
            f"muss abschaltbar sein."
        )


def _validate_configuration(
    inputs: ControllerInputs,
    loads: list[ControllableLoad],
) -> None:
    """
    Globale Plausibilitätsprüfung.
    """

    # Only readings that can affect the grid/PV controller are validated.
    # Old battery/SOC/hybrid settings remain accepted for migration but
    # cannot block the grid-based controller or change its decisions.
    for name, value in (
        ("grid_kw", inputs.grid_kw),
        ("grid_limit_kw", inputs.grid_limit_kw),
        ("grid_reserve_kw", inputs.grid_reserve_kw),
        ("grid_growth_margin_kw", inputs.grid_growth_margin_kw),
        ("pv_kw", inputs.pv_kw),
        ("now_s", inputs.now_s),
    ):
        _require_finite(name, value)
    if inputs.grid_limit_kw <= 0:
        raise ValueError("PMAX muss groesser als 0 sein.")
    if inputs.grid_reserve_kw < 0 or inputs.grid_reserve_kw >= inputs.grid_limit_kw:
        raise ValueError("Netzreserve muss kleiner als PMAX und >= 0 sein.")
    if inputs.grid_growth_margin_kw < 0:
        raise ValueError("Netz-Freigabepuffer darf nicht negativ sein.")
    if inputs.now_s < 0:
        raise ValueError("now_s darf nicht negativ sein.")

    names = [
        load.name
        for load in loads
    ]

    if len(names) != len(set(names)):

        raise ValueError(
            "Jeder Verbraucher benötigt einen "
            "eindeutigen Namen."
        )

    for load in loads:

        _validate_load(
            load
        )


def _get_previous_runtime(
    load: ControllableLoad,
    state: ControllerState,
) -> LoadRuntimeState:
    """
    Vorherigen Laufzustand abrufen.

    Alte Sollwerte werden automatisch an
    die aktuellen Gerätegrenzen angepasst.
    """

    runtime = state.load_states.get(
        load.name
    )

    if runtime is not None:

        previous_target = max(
            0.0,
            min(
                runtime.last_target_kw,
                load.max_kw,
            ),
        )

        return LoadRuntimeState(
            is_on=(
                runtime.is_on
                and previous_target > EPSILON
            ),

            last_target_kw=(
                previous_target
            ),

            last_switch_s=(
                runtime.last_switch_s
            ),

            last_target_change_s=(
                runtime.last_target_change_s
            ),

            settling_until_s=(
                runtime.settling_until_s
            ),
        )

    previous_target = max(
        0.0,
        min(
            state.last_targets_kw.get(
                load.name,
                0.0,
            ),
            load.max_kw,
        ),
    )

    return LoadRuntimeState(
        is_on=(
            previous_target > EPSILON
        ),
        last_target_kw=(
            previous_target
        ),
    )


def _calculate_controlled_power(
    loads: list[ControllableLoad],
    state: ControllerState,
) -> tuple[float, float]:
    """
    Bestimmt bekannte Leistung der
    regelbaren Verbraucher.

    Istwert vorhanden:
        Istwert verwenden.

    Kein Istwert:
        letzten Sollwert als Schätzung verwenden.
    """

    measured_kw = 0.0
    estimated_kw = 0.0

    for load in loads:

        if load.actual_kw is not None:

            measured_kw += (
                load.actual_kw
            )

        else:

            runtime = (
                _get_previous_runtime(
                    load=load,
                    state=state,
                )
            )

            estimated_kw += (
                runtime.last_target_kw
            )

    return (
        measured_kw,
        estimated_kw,
    )


def _build_next_state(
    loads: list[ControllableLoad],
    targets_kw: dict[str, float],
    previous_state: ControllerState,
    now_s: float,
) -> ControllerState:
    """
    Aktualisiert den Zustand nach einem Regeldurchlauf.
    """

    next_last_targets = (
        previous_state
        .last_targets_kw
        .copy()
    )

    next_load_states = (
        previous_state
        .load_states
        .copy()
    )

    for load in loads:

        if load.name not in targets_kw:
            continue

        target_kw = max(
            0.0,
            min(
                targets_kw[
                    load.name
                ],
                load.max_kw,
            ),
        )

        previous = (
            _get_previous_runtime(
                load=load,
                state=previous_state,
            )
        )

        new_is_on = (
            target_kw > EPSILON
        )

        if (
            new_is_on
            != previous.is_on
        ):

            last_switch_s = (
                now_s
            )

        else:

            last_switch_s = (
                previous.last_switch_s
            )

        target_changed = (
            abs(
                target_kw
                - previous.last_target_kw
            )
            > EPSILON
        )

        if target_changed:

            last_target_change_s = (
                now_s
            )

            settling_until_s = (
                now_s
                + load.settling_time_s
            )

        else:

            last_target_change_s = (
                previous
                .last_target_change_s
            )

            settling_until_s = (
                previous
                .settling_until_s
            )

        next_last_targets[
            load.name
        ] = target_kw

        next_load_states[
            load.name
        ] = LoadRuntimeState(
            is_on=new_is_on,

            last_target_kw=(
                target_kw
            ),

            last_switch_s=(
                last_switch_s
            ),

            last_target_change_s=(
                last_target_change_s
            ),

            settling_until_s=(
                settling_until_s
            ),
        )

    return ControllerState(
        last_targets_kw=(
            next_last_targets
        ),

        load_states=(
            next_load_states
        ),
    )


def run_controller(
    inputs: ControllerInputs,
    loads: list[ControllableLoad],
    state: ControllerState | None = None,
) -> ControllerResult:
    """Simple grid-based peak shaving and measured PV-surplus allocation.

    NORMAL: PMAX minus uncontrolled baseline, measured at the grid meter.
    SURPLUS: actual net export plus power already allocated to PV loads.
    The autonomous battery (power, SOC, reserve and hybrid flags) is NEVER
    consulted. Optional per-load actual power refines the load estimate.
    """

    if state is None:
        state = ControllerState()
    _validate_configuration(inputs, loads)

    if inputs.mode == OperatingMode.NORMAL:
        selected = [load for load in loads if load.peak_shaving_enabled]
    elif inputs.mode == OperatingMode.SURPLUS:
        selected = [
            load for load in loads
            if load.peak_shaving_enabled and load.surplus_enabled
        ]
    else:
        raise ValueError(f"Unbekannter Betriebsmodus: {inputs.mode}")

    measured_kw, estimated_kw = _calculate_controlled_power(selected, state)
    controlled_kw = measured_kw + estimated_kw
    # The battery runs independently; do not add or subtract its power.
    base_kw = inputs.grid_kw - controlled_kw
    limit_kw = inputs.grid_limit_kw - inputs.grid_reserve_kw
    peak_budget_kw = max(0.0, limit_kw - base_kw)
    grid_limit_unachievable = base_kw > limit_kw + EPSILON
    hard_limit_exceeded_now = inputs.grid_kw > limit_kw + EPSILON

    if inputs.mode == OperatingMode.SURPLUS:
        # Only grid EXPORT proves free electrical energy after house,
        # inverter and autonomous battery have done their own work.
        # When PV loads already run, credit their current measured (or
        # last commanded) consumption: otherwise 0 export would cause
        # permanent on/off oscillation. Positive grid import subtracts
        # from this credit. PV power must actually be present.
        export_kw = max(0.0, -inputs.grid_kw) if inputs.pv_kw > EPSILON else 0.0
        surplus_budget_kw = (
            max(0.0, controlled_kw - inputs.grid_kw)
            if inputs.pv_kw > EPSILON else 0.0
        )
        available_kw = min(surplus_budget_kw, peak_budget_kw)
        # PV consumers share equally at their configured limits, independent
        # of NORMAL peak-shaving priorities.
        allocation_loads = [replace(load, priority=1) for load in selected]
        growth_kw = export_kw
    else:
        export_kw = 0.0
        surplus_budget_kw = 0.0
        available_kw = peak_budget_kw
        allocation_loads = selected
        # Tiny configurable metering/noise deadband for NEW load only;
        # never delay a necessary load reduction.
        growth_kw = max(
            0.0,
            limit_kw - inputs.grid_kw - inputs.grid_growth_margin_kw,
        )

    targets = allocate_power(
        allocation_loads, available_kw, state=state, now_s=inputs.now_s,
    )

    # Do not reuse power merely ORDERED to be shed from another device:
    # the next grid reading must show the freed capacity first.
    # No global 15-second lockout or inverter probing.
    ordered = (sorted(selected, key=lambda load: load.priority)
               if inputs.mode == OperatingMode.NORMAL else selected)
    for load in ordered:
        proposed = targets.get(load.name, 0.0)
        previous = max(
            0.0, state.last_targets_kw.get(load.name, 0.0),
            load.actual_kw if load.actual_kw is not None else 0.0,
        )
        if proposed <= previous + EPSILON:
            continue  # Immediate decreases, including PMAX shedding.
        allowed = min(proposed, previous + growth_kw)
        if allowed + EPSILON < load.min_kw:
            allowed = 0.0  # Not even a technical minimum can be supplied.
        elif not load.can_modulate and allowed + EPSILON < proposed:
            # Binary output must not be sent a fractional power command.
            allowed = min(previous, proposed) if previous > EPSILON else 0.0
        targets[load.name] = allowed
        growth_kw = max(0.0, growth_kw - max(0.0, allowed - previous))

    total_kw = sum(targets.values())
    projected_grid_kw = base_kw + total_kw
    if not grid_limit_unachievable and projected_grid_kw > limit_kw + EPSILON:
        raise RuntimeError("Interner Sicherheitsfehler: PMAX ueberschritten.")

    total_requested_kw = sum(
        min(max(0.0, load.requested_kw), load.max_kw)
        for load in selected if load.available
    )
    next_state = _build_next_state(
        selected, targets, previous_state=state, now_s=inputs.now_s,
    )
    active = sum(target > EPSILON for target in targets.values())
    limited = sum(
        load.available
        and min(max(0.0, load.requested_kw), load.max_kw)
        > targets.get(load.name, 0.0) + EPSILON
        for load in selected
    )
    settling = sum(
        runtime.settling_until_s is not None
        and inputs.now_s < runtime.settling_until_s
        for runtime in next_state.load_states.values()
    )
    return ControllerResult(
        targets_kw=targets,
        base_load_kw=base_kw,
        measured_controlled_power_kw=measured_kw,
        estimated_controlled_power_kw=estimated_kw,
        controlled_power_for_calculation_kw=controlled_kw,
        effective_grid_limit_kw=limit_kw,
        peak_budget_kw=peak_budget_kw,
        raw_surplus_budget_kw=export_kw,
        surplus_budget_kw=surplus_budget_kw,
        available_budget_kw=available_kw,
        unused_budget_kw=max(0.0, available_kw - total_kw),
        battery_discharge_kw=0.0,  # Battery does not enter the controller.
        projected_grid_kw=projected_grid_kw,
        grid_headroom_kw=limit_kw - projected_grid_kw,
        total_requested_kw=total_requested_kw,
        total_target_kw=total_kw,
        active_load_count=active,
        limited_load_count=limited,
        settling_load_count=settling,
        battery_soc_gate_enabled=False,
        battery_soc_blocking_surplus=False,
        peak_shaving_active=(
            hard_limit_exceeded_now or total_requested_kw > peak_budget_kw + EPSILON
        ),
        surplus_active=inputs.mode == OperatingMode.SURPLUS,
        hard_limit_exceeded_now=hard_limit_exceeded_now,
        grid_limit_unachievable=grid_limit_unachievable,
        state=next_state,
    )
