from dataclasses import dataclass, field
from enum import Enum


class OperatingMode(str, Enum):
    NORMAL = "normal"
    SURPLUS = "surplus"


@dataclass
class ControllableLoad:
    """
    Allgemeiner regelbarer Verbraucher.

    priority:
        1 = höchste Priorität.

    requested_kw:
        Aktuell angeforderte Leistung.

    actual_kw:
        Gemessene Istleistung.
        None = kein eigener Leistungsmesswert vorhanden.

    min_kw / max_kw:
        Technische Leistungsgrenzen.

    start_margin_kw:
        Zusätzliche Reserve zum Starten.

        Beispiel:
        min_kw = 6.0
        start_margin_kw = 0.3

        Start erst ab 6.3 kW verfügbarem Budget.

    stop_margin_kw:
        Haltereserve für bereits laufende Verbraucher.

        Muss <= start_margin_kw sein.

    min_on_time_s:
        Gewünschte Mindestlaufzeit.

        PMAX hat trotzdem immer Vorrang.

    min_off_time_s:
        Gewünschte Mindestauszeit.

    settling_time_s:
        Zeit nach einer Sollwertänderung, in der
        keine weitere Erhöhung erfolgen soll.

        Reduzierungen bleiben jederzeit erlaubt.
    """

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
    """
    Laufender Zustand eines Verbrauchers.
    """

    is_on: bool = False

    last_target_kw: float = 0.0

    last_switch_s: float | None = None

    last_target_change_s: float | None = None

    settling_until_s: float | None = None


@dataclass
class ControllerInputs:
    """
    Globale Eingänge des Energiemanagers.

    grid_kw:
        positiv = Netzbezug
        negativ = Netzeinspeisung

    grid_limit_kw:
        Hartes PMAX am Netzanschlusspunkt.

    pv_kw:
        PV-Leistung.
        PV-Erzeugung; das echte Budget ergibt sich erst
        nach Abzug der ungeregelten Hauslast.

    battery_soc:
        Ladezustand 0...100 %.
        None = kein SOC-Wert vorhanden.

    battery_kw:
        positiv = Batterie entlädt
        negativ = Batterie lädt

    surplus_min_battery_soc:
        Optionaler Mindest-SOC / Reserve-SOC für den
        Überschussbetrieb.

        None = SOC-Grenze deaktiviert.

        Bei SOC <= Reserve wird die Batterieunterstützung
        gesperrt, der echte PV-Überschuss bleibt nutzbar.

    now_s:
        Zeitwert in Sekunden.

        Der Controller verwendet absichtlich keine
        eigene Systemzeit. Dadurch ist er vollständig
        reproduzierbar und testbar.
    """

    grid_kw: float
    grid_limit_kw: float

    pv_kw: float = 0.0

    battery_soc: float | None = None
    battery_kw: float = 0.0

    grid_reserve_kw: float = 0.0

    mode: OperatingMode = OperatingMode.NORMAL

    now_s: float = 0.0

    surplus_min_battery_soc: float | None = None
    # Battery bonus is re-enabled only above reserve + hysteresis;
    # pure PV operation never depends on this state.
    battery_resume_hysteresis_soc: float = 2.0

    # Hybrid feedback parameters (plant-independent, all configurable).
    # The coordinator enables active probing only during live control.
    hybrid_battery_assist_enabled: bool = False
    hybrid_probe_enabled: bool = False
    hybrid_probe_step_kw: float = 0.0
    hybrid_probe_settle_s: float = 5.0
    hybrid_probe_retry_s: float = 30.0
    hybrid_grid_tolerance_kw: float = 0.1


@dataclass
class ControllerState:
    """
    Zustand zwischen zwei Regeldurchläufen.
    """

    last_targets_kw: dict[str, float] = field(
        default_factory=dict
    )

    load_states: dict[str, LoadRuntimeState] = field(
        default_factory=dict
    )

    # Exactly one outstanding hybrid probe; no physical battery
    # maximum is inferred from instantaneous discharge.
    hybrid_probe_until_s: float | None = None
    hybrid_probe_target_kw: float | None = None
    # Fixed authorization from the time the probe was started.
    hybrid_probe_increment_kw: float = 0.0
    hybrid_next_probe_s: float = 0.0
    battery_bonus_blocked: bool = False


@dataclass
class ControllerResult:
    """
    Ergebnis eines Regeldurchlaufs.

    Die zusätzlichen Diagnosewerte werden später
    sehr praktisch für Home-Assistant-Sensoren.
    """

    targets_kw: dict[str, float] = field(
        default_factory=dict
    )

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

    battery_discharge_kw: float = 0.0

    projected_grid_kw: float = 0.0
    grid_headroom_kw: float = 0.0

    total_requested_kw: float = 0.0
    total_target_kw: float = 0.0

    active_load_count: int = 0
    limited_load_count: int = 0
    settling_load_count: int = 0

    battery_soc_gate_enabled: bool = False
    battery_soc_blocking_surplus: bool = False

    peak_shaving_active: bool = False
    surplus_active: bool = False

    hard_limit_exceeded_now: bool = False

    grid_limit_unachievable: bool = False

    state: ControllerState = field(
        default_factory=ControllerState
    )