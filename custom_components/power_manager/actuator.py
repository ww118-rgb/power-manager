"""Home Assistant actuator layer for Power Manager."""

from __future__ import annotations

from dataclasses import dataclass, replace
from math import isfinite
from typing import Any

from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant, State

from .const import (
    CONF_OUTPUT_STEPS_JSON,
    CONF_OUTPUT_TRANSPORT,
    CONF_MODBUS_HOST,
    CONF_MODBUS_PORT,
    CONF_MODBUS_UNIT_ID,
    CONF_MODBUS_REGISTER,
    CONF_MODBUS_DATA_TYPE,
    CONF_MODBUS_BYTE_ORDER,
    CONF_MODBUS_FUNCTION,
    CONF_MODBUS_TIMEOUT_S,
    CONF_MQTT_TOPIC,
    CONF_MQTT_QOS,
    CONF_MQTT_RETAIN,
    CONF_MQTT_PAYLOAD_TEMPLATE,
    CONF_MQTT_ON_PAYLOAD,
    CONF_MQTT_OFF_PAYLOAD,
    CONF_SWITCH_ON_CODE,
    CONF_SWITCH_OFF_CODE,
    CONF_DEVICE_COMMANDS_CONFIRMED,
    DEFAULT_OUTPUT_STEPS_JSON,
    DEFAULT_OUTPUT_TRANSPORT,
    DEFAULT_MODBUS_PORT,
    DEFAULT_MODBUS_UNIT_ID,
    DEFAULT_MODBUS_DATA_TYPE,
    DEFAULT_MODBUS_BYTE_ORDER,
    DEFAULT_MODBUS_FUNCTION,
    DEFAULT_MODBUS_TIMEOUT_S,
    DEFAULT_MQTT_QOS,
    DEFAULT_MQTT_RETAIN,
    DEFAULT_MQTT_PAYLOAD_TEMPLATE,
    DEFAULT_SWITCH_ON_CODE,
    DEFAULT_SWITCH_OFF_CODE,
    OUTPUT_TRANSPORT_ENTITY,
    OUTPUT_TRANSPORT_MODBUS,
    OUTPUT_TRANSPORT_MQTT,
    CONF_ENABLE_ENTITY,
    CONF_EVSE_MAX_CURRENT_A,
    CONF_EVSE_MIN_CURRENT_A,
    CONF_EVSE_PAUSE_CURRENT_A,
    CONF_EVSE_OUTPUT_FORMAT, CONF_EVSE_CURRENT_STEP_A,
    CONF_EVSE_POWER_STEP_W, CONF_EVSE_PAUSE_POWER_VALUE,
    DEFAULT_EVSE_OUTPUT_FORMAT, DEFAULT_EVSE_CURRENT_STEP_A,
    DEFAULT_EVSE_POWER_STEP_W, DEFAULT_EVSE_PAUSE_POWER_VALUE,
    EVSE_OUTPUT_AUTO, EVSE_OUTPUT_AMPERE, EVSE_OUTPUT_WATT, EVSE_OUTPUT_KW,
    CONF_EVSE_PHASES,
    CONF_EVSE_VOLTAGE_V,
    CONF_LOAD_TYPE,
    CONF_MAX_KW,
    CONF_MIN_KW,
    CONF_OUTPUT_ENTITY,
    CONF_OUTPUT_UNIT,
    CONF_SAFE_OUTPUT_VALUE,
    CONF_OUTPUT_VALUE_MODE, CONF_OUTPUT_SCALE, CONF_OUTPUT_OFFSET,
    CONF_OUTPUT_FORBIDDEN_VALUE, CONF_EVSE_ZERO_UNLIMITED,
    DEFAULT_OUTPUT_VALUE_MODE, DEFAULT_OUTPUT_SCALE, DEFAULT_OUTPUT_OFFSET,
    DEFAULT_EVSE_ZERO_UNLIMITED,
    OUTPUT_VALUE_MODE_LINEAR,
    DEFAULT_EVSE_MAX_CURRENT_A,
    DEFAULT_EVSE_MIN_CURRENT_A,
    DEFAULT_EVSE_PAUSE_CURRENT_A,
    DEFAULT_EVSE_PHASES,
    DEFAULT_EVSE_VOLTAGE_V,
    DEFAULT_MAX_KW,
    DEFAULT_MIN_KW,
    DEFAULT_OUTPUT_UNIT,
    DEFAULT_SAFE_OUTPUT_VALUE,
    LOAD_TYPE_EVSE,
    LOAD_TYPE_MODULATING,
    LOAD_TYPE_SWITCH,
    OUTPUT_VALUE_MODE_POWER,
    OUTPUT_UNIT_W,
    OUTPUT_UNIT_KW,
    OUTPUT_UNIT_MW,
    OUTPUT_UNIT_AUTO,
    SUPPORTED_NUMBER_DOMAINS,
    SUPPORTED_OUTPUT_POWER_UNITS,
    SUPPORTED_SWITCH_DOMAINS,
)
from .outputs import OutputConversionError, OutputPlan, build_output_plan
from .protocols import TransportError, async_modbus_write, async_mqtt_publish
from .load_config import validate_load_data
from .device_units import convert_power_unit, quantize_down


class ActuatorError(RuntimeError):
    """Raised when a configured actuator cannot be used safely."""


@dataclass(frozen=True, slots=True)
class AppliedCommand:
    """Result of applying one load target."""

    target_kw: float
    # Physical command power after HA device-step rounding (NOT measured power).
    effective_target_kw: float | None = None
    numeric_value: float | None = None
    numeric_unit: str | None = None
    enabled: bool | None = None
    wrote_numeric: bool = False
    wrote_enable: bool = False


def _domain(entity_id: str) -> str:
    """Return entity domain."""

    return entity_id.split(".", 1)[0] if "." in entity_id else ""


def _state_or_error(hass: HomeAssistant, entity_id: str, label: str) -> State:
    """Return an entity state or raise an actuator error."""

    state = hass.states.get(entity_id)
    if state is None:
        raise ActuatorError(f"{label}: Entity '{entity_id}' wurde nicht gefunden.")
    if state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
        raise ActuatorError(f"{label}: Entity '{entity_id}' ist {state.state}.")
    return state


def _effective_power_unit(hass: HomeAssistant, load_data: dict[str, Any]) -> str:
    """Resolve generic power output unit without guessing."""

    configured_unit = str(load_data.get(CONF_OUTPUT_UNIT, DEFAULT_OUTPUT_UNIT))
    if configured_unit != OUTPUT_UNIT_AUTO:
        if configured_unit not in SUPPORTED_OUTPUT_POWER_UNITS:
            raise ActuatorError(
                f"Ausgangseinheit '{configured_unit}' wird nicht unterstützt."
            )
        return configured_unit

    output_entity = str(load_data.get(CONF_OUTPUT_ENTITY, ""))
    state = _state_or_error(hass, output_entity, "Leistungsausgang")
    unit = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
    if unit not in SUPPORTED_OUTPUT_POWER_UNITS:
        raise ActuatorError(
            "Leistungsausgang hat keine unterstützte Einheit. "
            "Wähle W, kW oder MW explizit in der Verbraucher-Konfiguration."
        )
    return str(unit)


def _numeric_limits(state: State) -> tuple[float | None, float | None]:
    """Read optional min/max attributes from number-like entities."""

    def parsed(name: str) -> float | None:
        raw = state.attributes.get(name)
        if raw is None:
            return None
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return None
        return value if isfinite(value) else None

    return parsed("min"), parsed("max")


def _numeric_in_range(value: float, state: State) -> bool:
    """Return whether a numeric value is accepted by advertised limits."""

    minimum, maximum = _numeric_limits(state)
    if minimum is not None and value < minimum - 1e-9:
        return False
    if maximum is not None and value > maximum + 1e-9:
        return False
    raw_step = state.attributes.get("step")
    if raw_step is not None:
        try:
            step = float(raw_step)
        except (TypeError, ValueError):
            return False
        if not isfinite(step) or step <= 0:
            return False
        base = _numeric_limits(state)[0] or 0.0
        steps = (value - base) / step
        if abs(steps - round(steps)) > 1e-6:
            return False
    return True


def _convert_power_unit(value: float, source: str, target: str) -> float:
    """Unit-only adapter, never interpret raw device codes as power."""
    try:
        return convert_power_unit(value, source, target)
    except ValueError as err:
        raise ActuatorError(str(err)) from err


def _quantize_down(value: float, state: State) -> float:
    """Respect the number entity's bounds and its physical command step."""
    minimum, maximum = _numeric_limits(state)
    raw_step = state.attributes.get("step")
    try:
        return quantize_down(
            value, minimum=minimum, maximum=maximum,
            step=float(raw_step) if raw_step is not None else None,
        )
    except (ValueError, TypeError) as err:
        raise ActuatorError(
            f"Gerätesollwert {value:g} passt nicht zur Entity: "
            f"Bereich [{minimum}, {maximum}], Schrittweite {raw_step}: {err}"
        ) from err


def _effective_power_kw(
    command: float,
    unit: str,
    load_data: dict[str, Any],
) -> float:
    """Infer the maximum physical output that the translated command permits."""
    if unit == EVSE_OUTPUT_AMPERE:
        return (
            command * int(load_data.get(CONF_EVSE_PHASES, DEFAULT_EVSE_PHASES))
            * float(load_data.get(CONF_EVSE_VOLTAGE_V, DEFAULT_EVSE_VOLTAGE_V))
            / 1000.0
        )
    return _convert_power_unit(command, unit, OUTPUT_UNIT_KW)


def _effective_command_kw(
    plan: OutputPlan, load_data: dict[str, Any], target_kw: float,
) -> float | None:
    """Physical commanded kW after quantization; None for opaque device codes."""
    if plan.enabled is False:
        return 0.0
    if plan.numeric_value is None:
        return target_kw if plan.enabled else None  # binary on/off output
    if plan.numeric_unit in (*SUPPORTED_OUTPUT_POWER_UNITS, EVSE_OUTPUT_AMPERE):
        return max(0.0, min(target_kw, _effective_power_kw(
            float(plan.numeric_value), str(plan.numeric_unit), load_data,
        )))
    return None


def _entity_output_plan(
    hass: HomeAssistant,
    load_data: dict[str, Any],
    target_kw: float,
    state: State,
) -> OutputPlan:
    """Translate kW -> device command -> HA entity unit -> legal numeric step.

    The HA entity's physical unit is authoritative. Only physical power
    commands (W/kW/MW) can be converted to other physical power units.
    Never reinterpret raw device codes or Ampere as power without an EVSE
    electrical profile. Never round a command *up* to satisfy a step.
    """
    plan = _build_plan(hass, load_data, target_kw)
    if plan.numeric_value is None:
        return plan
    command = float(plan.numeric_value)
    unit = plan.numeric_unit
    actual_unit = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
    source_power = unit in SUPPORTED_OUTPUT_POWER_UNITS
    target_power = actual_unit in SUPPORTED_OUTPUT_POWER_UNITS
    if source_power and target_power and unit != actual_unit:
        if plan.enabled is False and abs(command) > 1e-9:
            raise ActuatorError(
                "Nicht-null-Pausencode besitzt eigene Gerätebedeutung; "
                "automatische Einheitenumrechnung ist dafür nicht sicher."
            )
        command = _convert_power_unit(command, str(unit), str(actual_unit))
        unit = str(actual_unit)
    elif actual_unit is not None and unit not in (actual_unit, None):
        if unit == "device" and actual_unit not in SUPPORTED_OUTPUT_POWER_UNITS:
            pass  # Explicit manufacturer code in a unitless/custom entity.
        elif unit in SUPPORTED_OUTPUT_POWER_UNITS or actual_unit in SUPPORTED_OUTPUT_POWER_UNITS:
            raise ActuatorError(
                f"Ausgangseinheiten unvereinbar: Gerätebefehl {unit!r}, "
                f"HA-Entity {actual_unit!r}. Wähle die passende A/W/kW-Einheit."
            )

    if not plan.enabled:
        # Pause/special codes must be representable *exactly*: never round them.
        if not _numeric_in_range(command, state):
            return replace(plan, numeric_value=command, numeric_unit=unit)
        return replace(plan, numeric_value=command, numeric_unit=unit)

    if unit not in SUPPORTED_OUTPUT_POWER_UNITS and unit != EVSE_OUTPUT_AMPERE:
        # Opaque register code: step quantization changes device meaning.
        if not _numeric_in_range(command, state):
            raise ActuatorError(
                "Gerätecode liegt außerhalb des erlaubten Entity-Schrittrasters. "
                "Bitte das Geräteprofil prüfen."
            )
        return replace(plan, numeric_value=command, numeric_unit=unit)

    rounded = _quantize_down(command, state)
    effective_kw = _effective_power_kw(rounded, str(unit), load_data)
    if effective_kw > target_kw + 1e-6:
        raise ActuatorError("Rundung würde die vom Regler erlaubte Leistung überschreiten.")
    physical_min_kw = float(load_data.get(CONF_MIN_KW, DEFAULT_MIN_KW))
    if load_data.get(CONF_LOAD_TYPE) == LOAD_TYPE_EVSE:
        physical_min_kw = max(
            physical_min_kw,
            int(load_data.get(CONF_EVSE_PHASES, DEFAULT_EVSE_PHASES))
            * float(load_data.get(CONF_EVSE_VOLTAGE_V, DEFAULT_EVSE_VOLTAGE_V))
            * float(load_data.get(CONF_EVSE_MIN_CURRENT_A, DEFAULT_EVSE_MIN_CURRENT_A))
            / 1000.0,
        )
    if rounded <= 1e-9 or effective_kw + 1e-6 < physical_min_kw:
        pause = _build_plan(hass, load_data, 0.0)
        if pause.numeric_value is None:
            raise ActuatorError("Sicherer Pausenbefehl fehlt.")
        pause_value = float(pause.numeric_value)
        pause_unit = pause.numeric_unit
        if pause_unit in SUPPORTED_OUTPUT_POWER_UNITS and target_power and pause_unit != actual_unit:
            if abs(pause_value) > 1e-9:
                raise ActuatorError(
                    "Nicht-null-Pausenbefehl kann nicht sicher umgerechnet werden."
                )
            pause_value = _convert_power_unit(pause_value, str(pause_unit), str(actual_unit))
            pause_unit = str(actual_unit)
        return replace(pause, numeric_value=pause_value, numeric_unit=pause_unit)
    return replace(plan, numeric_value=rounded, numeric_unit=unit)


def _numeric_equal(state: State, value: float) -> bool:
    """Compare current numeric entity state with a target."""

    try:
        current = float(state.state)
    except (TypeError, ValueError):
        return False
    # Absolute tiny float tolerance; 0.001 MW would silently hide 1 kW.
    return isfinite(current) and abs(current - value) <= 1e-6


def _build_plan(
    hass: HomeAssistant,
    load_data: dict[str, Any],
    target_kw: float,
) -> OutputPlan:
    """Build one output plan and translate conversion errors."""

    load_type = str(load_data.get(CONF_LOAD_TYPE, ""))
    power_unit = "kW"
    if (
        load_type not in (LOAD_TYPE_EVSE, LOAD_TYPE_SWITCH)
        and load_data.get(CONF_OUTPUT_VALUE_MODE, DEFAULT_OUTPUT_VALUE_MODE)
            == "power"
    ):
        if load_data.get(CONF_OUTPUT_TRANSPORT, DEFAULT_OUTPUT_TRANSPORT) == OUTPUT_TRANSPORT_ENTITY:
            power_unit = _effective_power_unit(hass, load_data)
        else:
            power_unit = str(load_data.get(CONF_OUTPUT_UNIT, DEFAULT_OUTPUT_UNIT))
            if power_unit not in SUPPORTED_OUTPUT_POWER_UNITS:
                raise ActuatorError("Direkter Geräteausgang erfordert explizit W, kW oder MW")

    evse_format = str(load_data.get(
        CONF_EVSE_OUTPUT_FORMAT, DEFAULT_EVSE_OUTPUT_FORMAT,
    ))
    if load_type == LOAD_TYPE_EVSE and evse_format == EVSE_OUTPUT_AUTO:
        if (
            load_data.get(CONF_OUTPUT_TRANSPORT, DEFAULT_OUTPUT_TRANSPORT)
            != OUTPUT_TRANSPORT_ENTITY
        ):
            raise ActuatorError(
                "Automatische Wallbox-Einheit nur für Home-Assistant-Entity verfügbar."
            )
        output = _state_or_error(
            hass, str(load_data.get(CONF_OUTPUT_ENTITY, "")), "Wallbox-Ausgang",
        )
        candidate = output.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
        if candidate not in (EVSE_OUTPUT_AMPERE, EVSE_OUTPUT_WATT, EVSE_OUTPUT_KW):
            raise ActuatorError(
                "Wallbox-Ausgang hat keine erkennbare Einheit A, W oder kW. "
                "Bitte die Sollwert-Einheit ausdrücklich wählen."
            )
        evse_format = str(candidate)
    try:
        return build_output_plan(
            load_type=load_type,
            target_kw=max(0.0, target_kw),
            power_unit=power_unit,
            safe_output_value=float(
                load_data.get(CONF_SAFE_OUTPUT_VALUE, DEFAULT_SAFE_OUTPUT_VALUE)
            ),
            evse_phases=int(load_data.get(CONF_EVSE_PHASES, DEFAULT_EVSE_PHASES)),
            evse_voltage_v=float(
                load_data.get(CONF_EVSE_VOLTAGE_V, DEFAULT_EVSE_VOLTAGE_V)
            ),
            evse_min_current_a=float(
                load_data.get(CONF_EVSE_MIN_CURRENT_A, DEFAULT_EVSE_MIN_CURRENT_A)
            ),
            evse_max_current_a=float(
                load_data.get(CONF_EVSE_MAX_CURRENT_A, DEFAULT_EVSE_MAX_CURRENT_A)
            ),
            evse_pause_current_a=float(
                load_data.get(CONF_EVSE_PAUSE_CURRENT_A, DEFAULT_EVSE_PAUSE_CURRENT_A)
            ),
            evse_output_format=evse_format,
            evse_current_step_a=float(load_data.get(
                CONF_EVSE_CURRENT_STEP_A, DEFAULT_EVSE_CURRENT_STEP_A,
            )),
            evse_power_step_w=float(load_data.get(
                CONF_EVSE_POWER_STEP_W, DEFAULT_EVSE_POWER_STEP_W,
            )),
            evse_pause_power_value=float(load_data.get(
                CONF_EVSE_PAUSE_POWER_VALUE, DEFAULT_EVSE_PAUSE_POWER_VALUE,
            )),
            output_value_mode=str(
                load_data.get(CONF_OUTPUT_VALUE_MODE, DEFAULT_OUTPUT_VALUE_MODE)
            ),
            output_scale=float(
                load_data.get(CONF_OUTPUT_SCALE, DEFAULT_OUTPUT_SCALE)
            ),
            output_offset=float(
                load_data.get(CONF_OUTPUT_OFFSET, DEFAULT_OUTPUT_OFFSET)
            ),
            forbidden_value=(
                float(load_data[CONF_OUTPUT_FORBIDDEN_VALUE])
                if load_data.get(CONF_OUTPUT_FORBIDDEN_VALUE) is not None else None
            ),
            evse_zero_unlimited=bool(
                load_data.get(CONF_EVSE_ZERO_UNLIMITED, DEFAULT_EVSE_ZERO_UNLIMITED)
            ),
            output_steps_json=str(
                load_data.get(CONF_OUTPUT_STEPS_JSON, DEFAULT_OUTPUT_STEPS_JSON)
            ),
        )
    except OutputConversionError as err:
        raise ActuatorError(str(err)) from err


async def _async_set_number(
    hass: HomeAssistant,
    entity_id: str,
    value: float,
) -> bool:
    """Set a number/input_number only when its state differs."""

    state = _state_or_error(hass, entity_id, "Numerischer Ausgang")
    if _numeric_equal(state, value):
        return False

    domain = _domain(entity_id)
    await hass.services.async_call(
        domain,
        "set_value",
        {"entity_id": entity_id, "value": value},
        blocking=True,
    )
    return True


async def _async_set_switch(
    hass: HomeAssistant,
    entity_id: str,
    enabled: bool,
) -> bool:
    """Set switch/input_boolean only when its state differs."""

    state = _state_or_error(hass, entity_id, "Schaltausgang")
    target_state = STATE_ON if enabled else STATE_OFF
    if state.state == target_state:
        return False

    domain = _domain(entity_id)
    await hass.services.async_call(
        domain,
        SERVICE_TURN_ON if enabled else SERVICE_TURN_OFF,
        {"entity_id": entity_id},
        blocking=True,
    )
    return True


def _validate_positive_plan_range(
    plan: OutputPlan,
    state: State,
    *,
    label: str,
) -> None:
    """Require a positive controller target to be exactly representable."""

    if plan.numeric_value is None:
        raise ActuatorError(f"{label}: kein numerischer Ausgangswert berechnet.")
    if plan.enabled is not True:
        raise ActuatorError(
            f"{label}: die gewünschte Leistung liegt unter der nächsten "
            "erreichbaren Gerätestufe und wird deshalb sicher pausiert. "
            "Eine höhere Lastfreigabe darf PMAX nicht überschreiten."
        )
    if not _numeric_in_range(plan.numeric_value, state):
        minimum, maximum = _numeric_limits(state)
        step = state.attributes.get("step")
        raise ActuatorError(
            f"{label}: berechneter Sollwert {plan.numeric_value:g} {plan.numeric_unit or ''} "
            f"passt nicht zu erlaubtem Bereich [{minimum}, {maximum}] "
            f"und Schrittweite {step}. Prüfe Ausgangseinheit A/W/kW "
            "und die zulässigen Gerätestufen."
        )


async def _async_write_direct(
    hass: HomeAssistant, load_data: dict[str, Any], value: float,
    *, payload_override: str | None = None,
) -> None:
    """Transmit a prevalidated device command without claiming physical success."""
    transport = str(load_data.get(CONF_OUTPUT_TRANSPORT, DEFAULT_OUTPUT_TRANSPORT))
    try:
        if transport == OUTPUT_TRANSPORT_MODBUS:
            await async_modbus_write(
                host=str(load_data.get(CONF_MODBUS_HOST, "")),
                port=int(load_data.get(CONF_MODBUS_PORT, DEFAULT_MODBUS_PORT)),
                unit_id=int(load_data.get(CONF_MODBUS_UNIT_ID, DEFAULT_MODBUS_UNIT_ID)),
                address=int(load_data.get(CONF_MODBUS_REGISTER, 0)),
                value=value,
                data_type=str(load_data.get(CONF_MODBUS_DATA_TYPE, DEFAULT_MODBUS_DATA_TYPE)),
                byte_order=str(load_data.get(CONF_MODBUS_BYTE_ORDER, DEFAULT_MODBUS_BYTE_ORDER)),
                function=int(load_data.get(CONF_MODBUS_FUNCTION, DEFAULT_MODBUS_FUNCTION)),
                timeout_s=float(load_data.get(CONF_MODBUS_TIMEOUT_S, DEFAULT_MODBUS_TIMEOUT_S)),
            )
        elif transport == OUTPUT_TRANSPORT_MQTT:
            await async_mqtt_publish(
                hass, topic=str(load_data.get(CONF_MQTT_TOPIC, "")),
                value=value,
                template=str(load_data.get(
                    CONF_MQTT_PAYLOAD_TEMPLATE, DEFAULT_MQTT_PAYLOAD_TEMPLATE,
                )),
                qos=int(load_data.get(CONF_MQTT_QOS, DEFAULT_MQTT_QOS)),
                retain=bool(load_data.get(CONF_MQTT_RETAIN, DEFAULT_MQTT_RETAIN)),
                payload_override=payload_override,
            )
        else:
            raise TransportError("Unknown device transport")
    except TransportError as err:
        raise ActuatorError(str(err)) from err


def validate_actuator(hass: HomeAssistant, load_data: dict[str, Any]) -> None:
    """Validate physical kW targets against legal device units and steps.

    Live use requires fresh measured feedback. Power commands may be rounded
    down safely to the nearest accepted step, but never rounded upward.
    Opaque manufacturer codes and special off values are never quantized.
    """

    transport = str(load_data.get(CONF_OUTPUT_TRANSPORT, DEFAULT_OUTPUT_TRANSPORT))
    if transport != OUTPUT_TRANSPORT_ENTITY:
        errors = validate_load_data(load_data)
        if errors:
            raise ActuatorError(f"Geräteprofil ungültig: {errors}")
        if not load_data.get(CONF_DEVICE_COMMANDS_CONFIRMED):
            raise ActuatorError("AUS-/EIN-Codes des Geräts müssen bestätigt werden")
        if load_data.get(CONF_ENABLE_ENTITY):
            enable_entity = str(load_data[CONF_ENABLE_ENTITY])
            if _domain(enable_entity) not in SUPPORTED_SWITCH_DOMAINS:
                raise ActuatorError("Freigabe-Entity muss switch oder input_boolean sein.")
            _state_or_error(hass, enable_entity, "Freigabe-Ausgang")
        min_kw = float(load_data.get(CONF_MIN_KW, DEFAULT_MIN_KW))
        max_kw = float(load_data.get(CONF_MAX_KW, DEFAULT_MAX_KW))
        for kw in (0.0, min_kw, max_kw):
            plan = _build_plan(hass, load_data, kw)
            if kw > 0 and plan.enabled is not True:
                raise ActuatorError("Geräteprofil stellt technische Mindestleistung nicht dar")
            code = (
                float(load_data.get(
                    CONF_SWITCH_ON_CODE if plan.enabled else CONF_SWITCH_OFF_CODE,
                    DEFAULT_SWITCH_ON_CODE if plan.enabled else DEFAULT_SWITCH_OFF_CODE,
                )) if load_data.get(CONF_LOAD_TYPE) == LOAD_TYPE_SWITCH
                else plan.numeric_value
            )
            if code is None or not isfinite(code):
                raise ActuatorError("Kein gültiger Gerätebefehl")
            forbidden = load_data.get(CONF_OUTPUT_FORBIDDEN_VALUE)
            if forbidden is not None and abs(code - float(forbidden)) <= 1e-6:
                raise ActuatorError("Geräteprofil erzeugt einen verbotenen Befehl")
        return

    output_entity = str(load_data.get(CONF_OUTPUT_ENTITY, ""))
    if not output_entity:
        raise ActuatorError(
            "Für jeden Verbraucher ist im Livebetrieb ein Ausgang erforderlich."
        )

    load_type = str(load_data.get(CONF_LOAD_TYPE, ""))
    output_domain = _domain(output_entity)

    enable_entity = str(load_data.get(CONF_ENABLE_ENTITY, ""))
    if enable_entity:
        if _domain(enable_entity) not in SUPPORTED_SWITCH_DOMAINS:
            raise ActuatorError("Freigabe-Entity muss switch oder input_boolean sein.")
        _state_or_error(hass, enable_entity, "Freigabe-Ausgang")

    if load_type == LOAD_TYPE_SWITCH:
        if output_domain not in SUPPORTED_SWITCH_DOMAINS:
            raise ActuatorError(
                f"Schaltverbraucher '{output_entity}' muss switch oder input_boolean sein."
            )
        _state_or_error(hass, output_entity, "Schaltausgang")
        return

    if output_domain not in SUPPORTED_NUMBER_DOMAINS:
        raise ActuatorError(
            f"Modulierender Ausgang '{output_entity}' muss number oder input_number sein."
        )

    output_state = _state_or_error(hass, output_entity, "Numerischer Ausgang")

    min_kw = float(load_data.get(CONF_MIN_KW, DEFAULT_MIN_KW))
    max_kw = float(load_data.get(CONF_MAX_KW, DEFAULT_MAX_KW))

    # Verify that every positive technical boundary is representable without
    # modifying the controller's target behind its back.
    if min_kw > 0.0:
        first_plan = _entity_output_plan(hass, load_data, min_kw, output_state)
        if first_plan.enabled is True:
            _validate_positive_plan_range(
                first_plan, output_state, label="Mindestleistung",
            )
        elif load_type != LOAD_TYPE_EVSE:
            _validate_positive_plan_range(
                first_plan, output_state, label="Mindestleistung",
            )
        # A whole-kW wallbox output cannot represent 4.14 kW: the
        # controller must pause until it can safely command 5 kW.
        # Do not round UP to start charging below the physical minimum.
    else:
        # With min_kw == 0 the controller may legitimately produce arbitrarily
        # small positive targets. The numeric output must therefore accept zero
        # as its lower boundary; a separate enable switch only solves target 0,
        # not positive targets below a number entity's minimum.
        minimum, _maximum = _numeric_limits(output_state)
        if minimum is not None and minimum > 1e-9:
            raise ActuatorError(
                "min_kw ist 0, aber die numerische Ausgangs-Entity hat einen "
                "positiven Mindestwert. Setze min_kw auf die technische Mindestleistung."
            )

    _validate_positive_plan_range(
        _entity_output_plan(hass, load_data, max_kw, output_state),
        output_state,
        label="Maximalleistung",
    )

    zero_plan = _entity_output_plan(hass, load_data, 0.0, output_state)
    if zero_plan.numeric_value is None:
        raise ActuatorError("Für den sicheren Zustand wurde kein Zahlenwert berechnet.")

    # A separate enable output can safely switch the device off even when its
    # numeric entity cannot represent the pause/zero value.
    if not enable_entity and not _numeric_in_range(zero_plan.numeric_value, output_state):
        raise ActuatorError(
            "Der sichere numerische Ausgangswert liegt außerhalb des Entity-Bereichs "
            "und es ist keine separate Freigabe-Entity konfiguriert."
        )


async def async_apply_target(
    hass: HomeAssistant,
    load_data: dict[str, Any],
    target_kw: float,
) -> AppliedCommand:
    """Apply one controller target to Home Assistant output entities."""

    transport = str(load_data.get(CONF_OUTPUT_TRANSPORT, DEFAULT_OUTPUT_TRANSPORT))
    if transport != OUTPUT_TRANSPORT_ENTITY:
        plan = _build_plan(hass, load_data, target_kw)
        enabled = bool(plan.enabled)
        code = (
            float(load_data.get(
                CONF_SWITCH_ON_CODE if enabled else CONF_SWITCH_OFF_CODE,
                DEFAULT_SWITCH_ON_CODE if enabled else DEFAULT_SWITCH_OFF_CODE,
            )) if load_data.get(CONF_LOAD_TYPE) == LOAD_TYPE_SWITCH
            else plan.numeric_value
        )
        if code is None or not isfinite(code):
            raise ActuatorError("No valid direct numeric command")
        forbidden = load_data.get(CONF_OUTPUT_FORBIDDEN_VALUE)
        if forbidden is not None and abs(code - float(forbidden)) <= 1e-6:
            raise ActuatorError("Refusing forbidden device command")
        enable_entity = str(load_data.get(CONF_ENABLE_ENTITY, ""))
        wrote_enable = False
        if not enabled and enable_entity:
            wrote_enable = await _async_set_switch(hass, enable_entity, False)
        payload_override = None
        if (
            transport == OUTPUT_TRANSPORT_MQTT
            and load_data.get(CONF_LOAD_TYPE) == LOAD_TYPE_SWITCH
        ):
            payload_override = str(load_data.get(
                CONF_MQTT_ON_PAYLOAD if enabled else CONF_MQTT_OFF_PAYLOAD,
                "",
            )) or None
        await _async_write_direct(
            hass, load_data, code, payload_override=payload_override,
        )
        if enabled and enable_entity:
            wrote_enable = await _async_set_switch(hass, enable_entity, True)
        return AppliedCommand(
            target_kw=target_kw,
            effective_target_kw=_effective_command_kw(plan, load_data, target_kw),
            numeric_value=code,
            numeric_unit=plan.numeric_unit or "device",
            enabled=enabled, wrote_numeric=True,
            wrote_enable=wrote_enable,
        )

    output_entity = str(load_data.get(CONF_OUTPUT_ENTITY, ""))
    if not output_entity:
        raise ActuatorError("Kein Ausgang konfiguriert.")

    load_type = str(load_data.get(CONF_LOAD_TYPE, ""))
    enable_entity = str(load_data.get(CONF_ENABLE_ENTITY, ""))
    plan = _build_plan(hass, load_data, target_kw)

    wrote_numeric = False
    wrote_enable = False

    if load_type == LOAD_TYPE_SWITCH:
        assert plan.enabled is not None
        wrote_enable = await _async_set_switch(hass, output_entity, plan.enabled)
        return AppliedCommand(
            target_kw=target_kw,
            effective_target_kw=(target_kw if plan.enabled else 0.0),
            enabled=plan.enabled,
            wrote_enable=wrote_enable,
        )

    output_state = _state_or_error(hass, output_entity, "Numerischer Ausgang")
    plan = _entity_output_plan(hass, load_data, target_kw, output_state)
    desired_numeric = plan.numeric_value
    if desired_numeric is None:
        raise ActuatorError("Numerischer Verbraucher hat keinen berechneten Ausgangswert.")

    if plan.enabled is False:
        # Disable first to avoid a transient command increase. If a separate
        # enable exists, a numeric pause value outside the number entity range
        # can simply be skipped because the physical enable is already off.
        if enable_entity:
            wrote_enable = await _async_set_switch(hass, enable_entity, False)

        if _numeric_in_range(desired_numeric, output_state):
            wrote_numeric = await _async_set_number(hass, output_entity, desired_numeric)
        elif not enable_entity:
            raise ActuatorError(
                "Sicherer Ausgangswert wird von der Entity nicht akzeptiert und keine "
                "separate Freigabe-Entity ist konfiguriert."
            )

        return AppliedCommand(
            target_kw=target_kw,
            effective_target_kw=0.0,
            numeric_value=(desired_numeric if _numeric_in_range(desired_numeric, output_state) else None),
            numeric_unit=plan.numeric_unit,
            enabled=False,
            wrote_numeric=wrote_numeric,
            wrote_enable=wrote_enable,
        )

    # PMAX invariant: positive targets must be representable exactly enough by
    # the configured HA entity. Never clamp up/down or silently disable here.
    if not _numeric_in_range(desired_numeric, output_state):
        minimum, maximum = _numeric_limits(output_state)
        raise ActuatorError(
            f"Berechneter Ausgangswert {desired_numeric:g} liegt außerhalb "
            f"des Entity-Bereichs [{minimum}, {maximum}]."
        )

    wrote_numeric = await _async_set_number(hass, output_entity, desired_numeric)

    if enable_entity:
        wrote_enable = await _async_set_switch(hass, enable_entity, True)

    return AppliedCommand(
        target_kw=target_kw,
        effective_target_kw=_effective_command_kw(plan, load_data, target_kw),
        numeric_value=desired_numeric,
        numeric_unit=plan.numeric_unit,
        enabled=True,
        wrote_numeric=wrote_numeric,
        wrote_enable=wrote_enable,
    )


async def async_apply_safe_state(
    hass: HomeAssistant,
    load_data: dict[str, Any],
) -> AppliedCommand:
    """Apply the load's configured zero-power / pause state."""

    return await async_apply_target(hass, load_data, 0.0)
