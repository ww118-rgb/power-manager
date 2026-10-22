"""Config and load-subentry flows for Power Manager."""

from __future__ import annotations

import json

from math import isfinite
from typing import Any

import voluptuous as probatio

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    OptionsFlow,
    SubentryFlowResult,
)
from homeassistant.const import Platform
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
)

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
    DEFAULT_MQTT_ON_PAYLOAD,
    DEFAULT_MQTT_OFF_PAYLOAD,
    DEFAULT_SWITCH_ON_CODE,
    DEFAULT_SWITCH_OFF_CODE,
    DEFAULT_DEVICE_COMMANDS_CONFIRMED,
    OUTPUT_TRANSPORTS,
    MODBUS_DATA_TYPES,
    MODBUS_BYTE_ORDERS,
    BATTERY_SOC_SCALES,
    CONF_ACTUAL_POWER_ENTITY,
    CONF_ACTUAL_SENSOR_TIMEOUT_S,
    CONF_FEEDBACK_TOLERANCE_KW,
    CONF_AVAILABILITY_ENTITY,
    CONF_BATTERY_POWER_ENTITY,
    CONF_BATTERY_SOC_ENTITY,
    CONF_BATTERY_SOC_SCALE,
    CONF_DEFAULT_REQUEST_KW,
    CONF_DEMAND_MODE, DEMAND_MODE_ALWAYS, DEMAND_MODE_SENSOR,
    DEMAND_MODE_DISABLED, DEMAND_MODES,
    LOAD_TYPE_MODULATING, LOAD_TYPE_EVSE, LOAD_TYPE_SWITCH,
    OUTPUT_VALUE_MODE_STEPS, OUTPUT_VALUE_MODE_LINEAR,
    OUTPUT_TRANSPORT_ENTITY, OUTPUT_TRANSPORT_MODBUS, OUTPUT_TRANSPORT_MQTT,
    CONF_ENABLE_ENTITY,
    CONF_EVSE_MAX_CURRENT_A,
    CONF_EVSE_MIN_CURRENT_A,
    CONF_EVSE_PAUSE_CURRENT_A,
    CONF_EVSE_OUTPUT_FORMAT, CONF_EVSE_CURRENT_STEP_A,
    CONF_EVSE_POWER_STEP_W, CONF_EVSE_PAUSE_POWER_VALUE,
    DEFAULT_EVSE_OUTPUT_FORMAT, DEFAULT_EVSE_CURRENT_STEP_A,
    DEFAULT_EVSE_POWER_STEP_W, DEFAULT_EVSE_PAUSE_POWER_VALUE,
    EVSE_OUTPUT_FORMATS, EVSE_OUTPUT_AUTO,
    EVSE_OUTPUT_AMPERE, EVSE_OUTPUT_WATT, EVSE_OUTPUT_KW,
    CONF_EVSE_PHASES,
    CONF_EVSE_VOLTAGE_V,
    CONF_GRID_LIMIT_KW,
    CONF_GRID_POWER_ENTITY,
    CONF_GRID_RESERVE_KW,
    CONF_GRID_GROWTH_MARGIN_KW,
    CONF_GRID_RECOVERY_HOLD_S,
    CONF_GRID_SENSOR_TIMEOUT_S,
    CONF_INVERT_ACTUAL_POWER,
    CONF_INVERT_BATTERY_POWER,
    CONF_INVERT_GRID_POWER,
    CONF_INVERT_PV_POWER,
    CONF_LOAD_NAME,
    CONF_LOAD_TYPE,
    CONF_MAX_KW,
    CONF_MIN_KW,
    CONF_MIN_OFF_TIME_S,
    CONF_MIN_ON_TIME_S,
    CONF_OUTPUT_ENTITY,
    CONF_OUTPUT_UNIT,
    CONF_PEAK_SHAVING_ENABLED,
    CONF_PRIORITY,
    CONF_PV_POWER_ENTITY,
    CONF_REQUEST_ENTITY,
    CONF_SAFE_OUTPUT_VALUE,
    CONF_OUTPUT_VALUE_MODE, CONF_OUTPUT_SCALE, CONF_OUTPUT_OFFSET,
    CONF_OUTPUT_FORBIDDEN_VALUE, CONF_EVSE_ZERO_UNLIMITED,
    CONF_SETTLING_TIME_S,
    CONF_START_MARGIN_KW,
    CONF_STOP_MARGIN_KW,
    CONF_SURPLUS_ENABLED,
    CONF_SURPLUS_MIN_BATTERY_SOC,
    CONF_BATTERY_RESUME_HYSTERESIS_SOC,
    CONF_PV_SENSOR_TIMEOUT_S,
    CONF_BATTERY_SENSOR_TIMEOUT_S,
    CONF_BATTERY_SOC_SENSOR_TIMEOUT_S,
    CONF_HYBRID_PROBE_STEP_KW,
    CONF_HYBRID_PROBE_SETTLE_S,
    CONF_HYBRID_PROBE_RETRY_S,
    CONF_HYBRID_GRID_TOLERANCE_KW,
    DEFAULT_HYBRID_PROBE_STEP_KW,
    DEFAULT_HYBRID_PROBE_SETTLE_S,
    DEFAULT_HYBRID_PROBE_RETRY_S,
    DEFAULT_HYBRID_GRID_TOLERANCE_KW,
    DEFAULT_ACTUAL_SENSOR_TIMEOUT_S,
    DEFAULT_FEEDBACK_TOLERANCE_KW,
    DEFAULT_BATTERY_SOC_SCALE,
    DEFAULT_DEFAULT_REQUEST_KW,
    DEFAULT_EVSE_MAX_CURRENT_A,
    DEFAULT_EVSE_MIN_CURRENT_A,
    DEFAULT_EVSE_PAUSE_CURRENT_A,
    DEFAULT_EVSE_PHASES,
    DEFAULT_EVSE_VOLTAGE_V,
    DEFAULT_GRID_RESERVE_KW,
    DEFAULT_GRID_SENSOR_TIMEOUT_S,
    DEFAULT_GRID_GROWTH_MARGIN_KW,
    DEFAULT_GRID_RECOVERY_HOLD_S,
    DEFAULT_BATTERY_RESUME_HYSTERESIS_SOC,
    DEFAULT_PV_SENSOR_TIMEOUT_S,
    DEFAULT_BATTERY_SENSOR_TIMEOUT_S,
    DEFAULT_BATTERY_SOC_SENSOR_TIMEOUT_S,
    DEFAULT_INVERT_ACTUAL_POWER,
    DEFAULT_INVERT_BATTERY_POWER,
    DEFAULT_INVERT_GRID_POWER,
    DEFAULT_INVERT_PV_POWER,
    DEFAULT_LOAD_TYPE,
    DEFAULT_MAX_KW,
    DEFAULT_MIN_KW,
    DEFAULT_MIN_OFF_TIME_S,
    DEFAULT_MIN_ON_TIME_S,
    DEFAULT_OUTPUT_UNIT,
    DEFAULT_PEAK_SHAVING_ENABLED,
    DEFAULT_PRIORITY,
    DEFAULT_SAFE_OUTPUT_VALUE,
    DEFAULT_OUTPUT_VALUE_MODE, DEFAULT_OUTPUT_SCALE,
    DEFAULT_OUTPUT_OFFSET, DEFAULT_EVSE_ZERO_UNLIMITED,
    OUTPUT_VALUE_MODES,
    DEFAULT_SETTLING_TIME_S,
    DEFAULT_START_MARGIN_KW,
    DEFAULT_STOP_MARGIN_KW,
    DEFAULT_SURPLUS_ENABLED,
    DOMAIN,
    LOAD_TYPES,
    NAME,
    OUTPUT_UNITS,
    SUBENTRY_TYPE_LOAD,
)
from .load_config import normalize_load_data, validate_load_data
from .outputs import build_output_plan, OutputConversionError


def _optional_marker(key: str, values: dict[str, Any]) -> probatio.Optional:
    """Create optional marker with suggested existing value."""

    current_value = values.get(key)
    if current_value is not None and current_value != "":
        return probatio.Optional(
            key,
            description={"suggested_value": current_value},
        )
    return probatio.Optional(key)


def _required_marker(
    key: str,
    values: dict[str, Any],
    default: Any,
) -> probatio.Required:
    """Create required marker using current value or a default."""

    return probatio.Required(
        key,
        default=values.get(key, default),
    )


def _required_entity_marker(
    key: str,
    values: dict[str, Any],
) -> probatio.Required:
    """Create a required entity marker without an invalid empty default."""

    current_value = values.get(key)
    if current_value:
        return probatio.Required(key, default=current_value)
    return probatio.Required(key)


def _power_number_selector(*, minimum: float = 0.0) -> NumberSelector:
    """Build a kW number selector."""

    return NumberSelector(
        NumberSelectorConfig(
            min=minimum,
            step=0.1,
            unit_of_measurement="kW",
            mode=NumberSelectorMode.BOX,
        )
    )


def _seconds_selector() -> NumberSelector:
    """Build a seconds selector."""

    return NumberSelector(
        NumberSelectorConfig(
            min=0.0,
            step=1.0,
            unit_of_measurement="s",
            mode=NumberSelectorMode.BOX,
        )
    )


def _entity_selector(*, domain: str | list[str] | None = None) -> EntitySelector:
    """Build a single-entity selector without serializing a null domain filter."""

    config = EntitySelectorConfig(multiple=False)
    if domain is not None:
        config["domain"] = domain

    return EntitySelector(config)


def _build_global_schema(values: dict[str, Any] | None = None) -> probatio.Schema:
    """Build global configuration schema."""

    values = values or {}

    return probatio.Schema(
        {
            _required_entity_marker(CONF_GRID_POWER_ENTITY, values): _entity_selector(
                domain=Platform.SENSOR
            ),
            _required_marker(CONF_GRID_LIMIT_KW, values, 1.0): _power_number_selector(
                minimum=0.1
            ),
            _required_marker(
                CONF_GRID_RESERVE_KW,
                values,
                DEFAULT_GRID_RESERVE_KW,
            ): _power_number_selector(),
            _required_marker(
                CONF_GRID_GROWTH_MARGIN_KW, values, DEFAULT_GRID_GROWTH_MARGIN_KW,
            ): _power_number_selector(),
            _required_marker(
                CONF_GRID_RECOVERY_HOLD_S, values, DEFAULT_GRID_RECOVERY_HOLD_S,
            ): _seconds_selector(),
            _required_marker(
                CONF_GRID_SENSOR_TIMEOUT_S,
                values,
                DEFAULT_GRID_SENSOR_TIMEOUT_S,
            ): NumberSelector(
                NumberSelectorConfig(
                    min=0.1,
                    step=0.1,
                    unit_of_measurement="s",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            _required_marker(
                CONF_INVERT_GRID_POWER,
                values,
                DEFAULT_INVERT_GRID_POWER,
            ): BooleanSelector(),
            _optional_marker(CONF_PV_POWER_ENTITY, values): _entity_selector(
                domain=Platform.SENSOR
            ),
            _required_marker(
                CONF_INVERT_PV_POWER,
                values,
                DEFAULT_INVERT_PV_POWER,
            ): BooleanSelector(),
            _optional_marker(CONF_BATTERY_POWER_ENTITY, values): _entity_selector(
                domain=Platform.SENSOR
            ),
            _required_marker(
                CONF_INVERT_BATTERY_POWER,
                values,
                DEFAULT_INVERT_BATTERY_POWER,
            ): BooleanSelector(),
            _optional_marker(CONF_BATTERY_SOC_ENTITY, values): _entity_selector(
                domain=Platform.SENSOR
            ),
            _required_marker(
                CONF_BATTERY_SOC_SCALE,
                values,
                DEFAULT_BATTERY_SOC_SCALE,
            ): SelectSelector(
                SelectSelectorConfig(options=list(BATTERY_SOC_SCALES), translation_key=CONF_BATTERY_SOC_SCALE)
            ),
            _required_marker(
                CONF_PV_SENSOR_TIMEOUT_S, values, DEFAULT_PV_SENSOR_TIMEOUT_S,
            ): _seconds_selector(),
            _required_marker(
                CONF_BATTERY_SENSOR_TIMEOUT_S, values, DEFAULT_BATTERY_SENSOR_TIMEOUT_S,
            ): _seconds_selector(),
            _required_marker(
                CONF_BATTERY_SOC_SENSOR_TIMEOUT_S, values, DEFAULT_BATTERY_SOC_SENSOR_TIMEOUT_S,
            ): _seconds_selector(),
            _required_marker(
                CONF_BATTERY_RESUME_HYSTERESIS_SOC, values,
                DEFAULT_BATTERY_RESUME_HYSTERESIS_SOC,
            ): NumberSelector(NumberSelectorConfig(
                min=0.0, max=100.0, step=0.5,
                unit_of_measurement="%", mode=NumberSelectorMode.BOX,
            )),
            _optional_marker(CONF_SURPLUS_MIN_BATTERY_SOC, values): NumberSelector(
                NumberSelectorConfig(
                    min=0.0,
                    max=100.0,
                    step=1.0,
                    unit_of_measurement="%",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            _required_marker(
                CONF_HYBRID_PROBE_STEP_KW, values, DEFAULT_HYBRID_PROBE_STEP_KW,
            ): _power_number_selector(),
            _required_marker(
                CONF_HYBRID_PROBE_SETTLE_S, values, DEFAULT_HYBRID_PROBE_SETTLE_S,
            ): _seconds_selector(),
            _required_marker(
                CONF_HYBRID_PROBE_RETRY_S, values, DEFAULT_HYBRID_PROBE_RETRY_S,
            ): _seconds_selector(),
            _required_marker(
                CONF_HYBRID_GRID_TOLERANCE_KW, values,
                DEFAULT_HYBRID_GRID_TOLERANCE_KW,
            ): _power_number_selector(),
        }
    )


# Reuse canonical selectors: only reveal fields relevant to this step.
_WIZARD_EXPERT = "wizard_expert"
_WIZARD_ACK = "wizard_ack"
_WIZARD_STAGE_COUNT = "wizard_stage_count"
_GLOBAL_BASIC_KEYS = (
    CONF_GRID_POWER_ENTITY, CONF_GRID_LIMIT_KW, CONF_PV_POWER_ENTITY,
    CONF_BATTERY_POWER_ENTITY, CONF_BATTERY_SOC_ENTITY,
    CONF_BATTERY_SOC_SCALE, CONF_SURPLUS_MIN_BATTERY_SOC,
    CONF_INVERT_GRID_POWER,
)
_GLOBAL_ADVANCED_KEYS = (
    CONF_GRID_RESERVE_KW, CONF_GRID_SENSOR_TIMEOUT_S,
    CONF_GRID_GROWTH_MARGIN_KW, CONF_GRID_RECOVERY_HOLD_S,
    CONF_INVERT_PV_POWER, CONF_INVERT_BATTERY_POWER,
    CONF_PV_SENSOR_TIMEOUT_S, CONF_BATTERY_SENSOR_TIMEOUT_S,
    CONF_BATTERY_SOC_SENSOR_TIMEOUT_S,
    CONF_BATTERY_RESUME_HYSTERESIS_SOC,
    CONF_HYBRID_PROBE_STEP_KW, CONF_HYBRID_PROBE_SETTLE_S,
    CONF_HYBRID_PROBE_RETRY_S, CONF_HYBRID_GRID_TOLERANCE_KW,
)
_GLOBAL_DEFAULTS = {
    CONF_GRID_RESERVE_KW: DEFAULT_GRID_RESERVE_KW,
    CONF_GRID_GROWTH_MARGIN_KW: DEFAULT_GRID_GROWTH_MARGIN_KW,
    CONF_GRID_RECOVERY_HOLD_S: DEFAULT_GRID_RECOVERY_HOLD_S,
    CONF_GRID_SENSOR_TIMEOUT_S: DEFAULT_GRID_SENSOR_TIMEOUT_S,
    CONF_INVERT_PV_POWER: DEFAULT_INVERT_PV_POWER,
    CONF_INVERT_BATTERY_POWER: DEFAULT_INVERT_BATTERY_POWER,
    CONF_PV_SENSOR_TIMEOUT_S: DEFAULT_PV_SENSOR_TIMEOUT_S,
    CONF_BATTERY_SENSOR_TIMEOUT_S: DEFAULT_BATTERY_SENSOR_TIMEOUT_S,
    CONF_BATTERY_SOC_SENSOR_TIMEOUT_S: DEFAULT_BATTERY_SOC_SENSOR_TIMEOUT_S,
    CONF_BATTERY_RESUME_HYSTERESIS_SOC: DEFAULT_BATTERY_RESUME_HYSTERESIS_SOC,
    CONF_HYBRID_PROBE_STEP_KW: DEFAULT_HYBRID_PROBE_STEP_KW,
    CONF_HYBRID_PROBE_SETTLE_S: DEFAULT_HYBRID_PROBE_SETTLE_S,
    CONF_HYBRID_PROBE_RETRY_S: DEFAULT_HYBRID_PROBE_RETRY_S,
    CONF_HYBRID_GRID_TOLERANCE_KW: DEFAULT_HYBRID_GRID_TOLERANCE_KW,
}

def _subset_schema(
    full_schema: probatio.Schema, fields: tuple[str, ...] | list[str],
) -> probatio.Schema:
    """Retain existing HA selectors, defaults and validation types."""
    allowed = set(fields)
    result = {
        marker: validator
        for marker, validator in full_schema.schema.items()
        if getattr(marker, "schema", marker) in allowed
    }
    if len(result) != len(allowed):
        present = {getattr(key, "schema", key) for key in result}
        raise ValueError(f"Unknown setup fields: {sorted(allowed - present)}")
    return probatio.Schema(result)


def _global_simple_schema(values: dict[str, Any]) -> probatio.Schema:
    fields = dict(
        _subset_schema(_build_global_schema(values), _GLOBAL_BASIC_KEYS).schema
    )
    fields[_required_marker(_WIZARD_EXPERT, values, False)] = BooleanSelector()
    return probatio.Schema(fields)


def _global_expert_schema(values: dict[str, Any]) -> probatio.Schema:
    return _subset_schema(_build_global_schema(values), _GLOBAL_ADVANCED_KEYS)


def _merge_global_basic(old: dict[str, Any], submitted: dict[str, Any]) -> dict[str, Any]:
    """Preserve hidden expert choices, allow clearing optional sensors."""
    result = {**_GLOBAL_DEFAULTS, **old, **submitted}
    for key in (
        CONF_PV_POWER_ENTITY, CONF_BATTERY_POWER_ENTITY,
        CONF_BATTERY_SOC_ENTITY, CONF_SURPLUS_MIN_BATTERY_SOC,
    ):
        if key not in submitted:
            result[key] = None
    result.pop(_WIZARD_EXPERT, None)
    return result


def _device_preview(draft: dict[str, Any], hass: Any = None) -> dict[str, str]:
    """Explain device commands before saving, without touching hardware."""
    name = str(draft.get(CONF_LOAD_NAME, "Verbraucher"))
    transport = str(draft.get(CONF_OUTPUT_TRANSPORT, DEFAULT_OUTPUT_TRANSPORT))
    load_type = str(draft.get(CONF_LOAD_TYPE, DEFAULT_LOAD_TYPE))
    output = {
        "device": name, "transport": transport,
        "off": "nicht überprüft", "min": "nicht überprüft",
        "max": "nicht überprüft",
        "compatibility": "Live-Ausgabe noch nicht geprüft",
    }
    # Purely read-only pre-arm check: never send device commands here.
    if transport == OUTPUT_TRANSPORT_ENTITY:
        entity = draft.get(CONF_OUTPUT_ENTITY)
        if not entity:
            output["compatibility"] = "Kein Ausgang gewählt: nur Dry-Run"
        elif hass is not None:
            try:
                from .actuator import validate_actuator, ActuatorError
                validate_actuator(hass, normalize_load_data(draft))
            except (ActuatorError, TypeError, ValueError) as err:
                output["compatibility"] = (
                    "Nicht live-kompatibel: " + str(err)
                )
            else:
                output["compatibility"] = (
                    "Wertebereich und Schrittweite laut HA-Entity geprüft"
                )
    else:
        output["compatibility"] = (
            "Direkte Gerätebefehle benötigen die Bestätigung am Gerät"
        )
    if load_type == LOAD_TYPE_SWITCH:
        if transport == OUTPUT_TRANSPORT_ENTITY:
            output.update({"off": "Schalter AUS", "min": "Schalter EIN",
                           "max": "Schalter EIN"})
        elif transport == OUTPUT_TRANSPORT_MQTT and draft.get(CONF_MQTT_ON_PAYLOAD) and draft.get(CONF_MQTT_OFF_PAYLOAD):
            output.update({
                "off": str(draft[CONF_MQTT_OFF_PAYLOAD]),
                "min": str(draft[CONF_MQTT_ON_PAYLOAD]),
                "max": str(draft[CONF_MQTT_ON_PAYLOAD]),
            })
        else:
            output.update({
                "off": str(draft.get(CONF_SWITCH_OFF_CODE, DEFAULT_SWITCH_OFF_CODE)),
                "min": str(draft.get(CONF_SWITCH_ON_CODE, DEFAULT_SWITCH_ON_CODE)),
                "max": str(draft.get(CONF_SWITCH_ON_CODE, DEFAULT_SWITCH_ON_CODE)),
            })
        return output

    evse_fmt = str(draft.get(
        CONF_EVSE_OUTPUT_FORMAT, DEFAULT_EVSE_OUTPUT_FORMAT,
    ))
    if load_type == LOAD_TYPE_EVSE and evse_fmt == EVSE_OUTPUT_AUTO:
        entity = draft.get(CONF_OUTPUT_ENTITY)
        state = hass.states.get(entity) if hass is not None and entity else None
        unit = state.attributes.get("unit_of_measurement") if state else None
        if unit not in (EVSE_OUTPUT_AMPERE, EVSE_OUTPUT_WATT, EVSE_OUTPUT_KW):
            output.update({
                "off": "Einheit A/W/kW im HA-Ausgang nicht erkennbar",
                "min": "Ausgangseinheit prüfen",
                "max": "Ausgangseinheit prüfen",
            })
            return output
        evse_fmt = unit
    kwargs: dict[str, Any] = dict(
        load_type=load_type,
        evse_output_format=evse_fmt,
        evse_current_step_a=float(draft.get(
            CONF_EVSE_CURRENT_STEP_A, DEFAULT_EVSE_CURRENT_STEP_A,
        )),
        evse_power_step_w=float(draft.get(
            CONF_EVSE_POWER_STEP_W, DEFAULT_EVSE_POWER_STEP_W,
        )),
        evse_pause_power_value=float(draft.get(
            CONF_EVSE_PAUSE_POWER_VALUE, DEFAULT_EVSE_PAUSE_POWER_VALUE,
        )),
        safe_output_value=float(draft.get(CONF_SAFE_OUTPUT_VALUE, DEFAULT_SAFE_OUTPUT_VALUE)),
        evse_phases=int(draft.get(CONF_EVSE_PHASES, DEFAULT_EVSE_PHASES)),
        evse_voltage_v=float(draft.get(CONF_EVSE_VOLTAGE_V, DEFAULT_EVSE_VOLTAGE_V)),
        evse_min_current_a=float(draft.get(
            CONF_EVSE_MIN_CURRENT_A, DEFAULT_EVSE_MIN_CURRENT_A,
        )),
        evse_max_current_a=float(draft.get(
            CONF_EVSE_MAX_CURRENT_A, DEFAULT_EVSE_MAX_CURRENT_A,
        )),
        evse_pause_current_a=float(draft.get(
            CONF_EVSE_PAUSE_CURRENT_A, DEFAULT_EVSE_PAUSE_CURRENT_A,
        )),
        evse_zero_unlimited=bool(draft.get(
            CONF_EVSE_ZERO_UNLIMITED, DEFAULT_EVSE_ZERO_UNLIMITED,
        )),
        output_value_mode=str(draft.get(
            CONF_OUTPUT_VALUE_MODE, DEFAULT_OUTPUT_VALUE_MODE,
        )),
        output_scale=float(draft.get(CONF_OUTPUT_SCALE, DEFAULT_OUTPUT_SCALE)),
        output_offset=float(draft.get(CONF_OUTPUT_OFFSET, DEFAULT_OUTPUT_OFFSET)),
        output_steps_json=str(draft.get(
            CONF_OUTPUT_STEPS_JSON, DEFAULT_OUTPUT_STEPS_JSON,
        )),
        forbidden_value=(
            float(draft[CONF_OUTPUT_FORBIDDEN_VALUE])
            if draft.get(CONF_OUTPUT_FORBIDDEN_VALUE) is not None else None
        ),
        power_unit=str(draft.get(CONF_OUTPUT_UNIT, DEFAULT_OUTPUT_UNIT)),
    )
    if (
        load_type == LOAD_TYPE_MODULATING
        and kwargs["output_value_mode"] == DEFAULT_OUTPUT_VALUE_MODE
        and kwargs["power_unit"] == DEFAULT_OUTPUT_UNIT
    ):
        kwargs["power_unit"] = "kW"
        suffix = " (Einheit automatisch über HA-Entity)"
    else:
        suffix = ""
    min_kw = float(draft.get(CONF_MIN_KW, DEFAULT_MIN_KW))
    max_kw = float(draft.get(CONF_MAX_KW, DEFAULT_MAX_KW))
    if load_type == LOAD_TYPE_EVSE:
        min_kw = (
            kwargs["evse_phases"] * kwargs["evse_voltage_v"]
            * kwargs["evse_min_current_a"] / 1000.0
        )
    if min_kw <= 0.0:
        min_kw = max_kw
    try:
        for target, key in ((0.0, "off"), (min_kw, "min"), (max_kw, "max")):
            result = build_output_plan(target_kw=target, **kwargs)
            output[key] = (
                f"{result.numeric_value:g} {result.numeric_unit or 'Code'}"
                if result.numeric_value is not None else (
                    "EIN" if result.enabled else "AUS"
                )
            ) + suffix
    except (ValueError, TypeError, OverflowError, OutputConversionError):
        output["off"] = "Gerätewert prüfen!"
        output["min"] = "Gerätewert prüfen!"
        output["max"] = "Gerätewert prüfen!"
    return output


def _normalize_global_configuration(user_input: dict[str, Any]) -> dict[str, Any]:
    """Return a complete global mapping so options can also clear old values."""

    normalized = dict(user_input)
    for key in (
        CONF_PV_POWER_ENTITY,
        CONF_BATTERY_POWER_ENTITY,
        CONF_BATTERY_SOC_ENTITY,
        CONF_SURPLUS_MIN_BATTERY_SOC,
    ):
        normalized.setdefault(key, None)
    return normalized


def _validate_global_configuration(user_input: dict[str, Any]) -> dict[str, str]:
    """Validate global configuration."""

    errors: dict[str, str] = {}

    try:
        grid_limit_kw = float(user_input[CONF_GRID_LIMIT_KW])
        grid_reserve_kw = float(user_input[CONF_GRID_RESERVE_KW])
        grid_sensor_timeout_s = float(user_input[CONF_GRID_SENSOR_TIMEOUT_S])
    except (KeyError, TypeError, ValueError):
        return {"base": "invalid_number"}

    if grid_limit_kw <= 0.0:
        errors[CONF_GRID_LIMIT_KW] = "grid_limit_must_be_positive"

    if grid_reserve_kw < 0.0 or grid_reserve_kw >= grid_limit_kw:
        errors[CONF_GRID_RESERVE_KW] = "reserve_must_be_below_grid_limit"

    if grid_sensor_timeout_s <= 0.0:
        errors[CONF_GRID_SENSOR_TIMEOUT_S] = "grid_timeout_must_be_positive"

    grid_stability_parameters = (
        (CONF_GRID_GROWTH_MARGIN_KW, DEFAULT_GRID_GROWTH_MARGIN_KW),
        (CONF_GRID_RECOVERY_HOLD_S, DEFAULT_GRID_RECOVERY_HOLD_S),
    )
    for key, default in grid_stability_parameters:
        try:
            value = float(user_input.get(key, default))
            if not isfinite(value) or value < 0:
                errors[key] = "invalid_number"
        except (ValueError, TypeError):
            errors[key] = "invalid_number"

    hybrid_parameters = (
        (CONF_PV_SENSOR_TIMEOUT_S, DEFAULT_PV_SENSOR_TIMEOUT_S, True),
        (CONF_BATTERY_SENSOR_TIMEOUT_S, DEFAULT_BATTERY_SENSOR_TIMEOUT_S, True),
        (CONF_BATTERY_SOC_SENSOR_TIMEOUT_S, DEFAULT_BATTERY_SOC_SENSOR_TIMEOUT_S, True),
        (CONF_BATTERY_RESUME_HYSTERESIS_SOC, DEFAULT_BATTERY_RESUME_HYSTERESIS_SOC, False),
        (CONF_HYBRID_PROBE_STEP_KW, DEFAULT_HYBRID_PROBE_STEP_KW, False),
        (CONF_HYBRID_PROBE_SETTLE_S, DEFAULT_HYBRID_PROBE_SETTLE_S, True),
        (CONF_HYBRID_PROBE_RETRY_S, DEFAULT_HYBRID_PROBE_RETRY_S, False),
        (CONF_HYBRID_GRID_TOLERANCE_KW, DEFAULT_HYBRID_GRID_TOLERANCE_KW, False),
    )
    for key, default, positive_required in hybrid_parameters:
        try:
            value = float(user_input.get(key, default))
            if not isfinite(value) or value < 0 or (positive_required and value == 0):
                errors[key] = "invalid_number"
        except (ValueError, TypeError):
            errors[key] = "invalid_number"

    try:
        soc_resume = float(user_input.get(
            CONF_BATTERY_RESUME_HYSTERESIS_SOC,
            DEFAULT_BATTERY_RESUME_HYSTERESIS_SOC,
        ))
        if soc_resume > 100:
            errors[CONF_BATTERY_RESUME_HYSTERESIS_SOC] = "invalid_number"
    except (TypeError, ValueError):
        errors[CONF_BATTERY_RESUME_HYSTERESIS_SOC] = "invalid_number"

    battery_soc_entity = user_input.get(CONF_BATTERY_SOC_ENTITY)
    surplus_min_soc = user_input.get(CONF_SURPLUS_MIN_BATTERY_SOC)

    if surplus_min_soc is not None and not battery_soc_entity:
        errors[CONF_SURPLUS_MIN_BATTERY_SOC] = "soc_limit_requires_soc_entity"

    selected_entities = [
        user_input.get(CONF_GRID_POWER_ENTITY),
        user_input.get(CONF_PV_POWER_ENTITY),
        user_input.get(CONF_BATTERY_POWER_ENTITY),
        user_input.get(CONF_BATTERY_SOC_ENTITY),
    ]
    selected_entities = [entity for entity in selected_entities if entity]
    if len(selected_entities) != len(set(selected_entities)):
        errors["base"] = "duplicate_entities"

    return errors


def _build_load_schema(values: dict[str, Any] | None = None) -> probatio.Schema:
    """Build one complete load configuration form."""

    values = values or {}

    return probatio.Schema(
        {
            _required_marker(CONF_LOAD_NAME, values, "Verbraucher"): str,
            _required_marker(CONF_LOAD_TYPE, values, DEFAULT_LOAD_TYPE): SelectSelector(
                SelectSelectorConfig(options=list(LOAD_TYPES), translation_key=CONF_LOAD_TYPE)
            ),
            _required_marker(CONF_PRIORITY, values, DEFAULT_PRIORITY): NumberSelector(
                NumberSelectorConfig(
                    min=1,
                    max=1000,
                    step=1,
                    mode=NumberSelectorMode.BOX,
                )
            ),
            _required_marker(CONF_MIN_KW, values, DEFAULT_MIN_KW): _power_number_selector(),
            _required_marker(CONF_MAX_KW, values, DEFAULT_MAX_KW): _power_number_selector(
                minimum=0.1
            ),
            _required_marker(
                CONF_DEFAULT_REQUEST_KW,
                values,
                DEFAULT_DEFAULT_REQUEST_KW,
            ): _power_number_selector(),
            _optional_marker(CONF_ACTUAL_POWER_ENTITY, values): _entity_selector(
                domain=Platform.SENSOR
            ),
            _required_marker(
                CONF_ACTUAL_SENSOR_TIMEOUT_S,
                values,
                DEFAULT_ACTUAL_SENSOR_TIMEOUT_S,
            ): NumberSelector(
                NumberSelectorConfig(
                    min=0.1,
                    step=0.1,
                    unit_of_measurement="s",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            _required_marker(
                CONF_INVERT_ACTUAL_POWER,
                values,
                DEFAULT_INVERT_ACTUAL_POWER,
            ): BooleanSelector(),
            _required_marker(
                CONF_FEEDBACK_TOLERANCE_KW, values, DEFAULT_FEEDBACK_TOLERANCE_KW,
            ): _power_number_selector(),
            _optional_marker(CONF_REQUEST_ENTITY, values): _entity_selector(),
            _optional_marker(CONF_AVAILABILITY_ENTITY, values): _entity_selector(),
            _optional_marker(CONF_OUTPUT_ENTITY, values): _entity_selector(),
            _optional_marker(CONF_ENABLE_ENTITY, values): _entity_selector(
                domain=["switch", "input_boolean"]
            ),
            _required_marker(CONF_OUTPUT_UNIT, values, DEFAULT_OUTPUT_UNIT): SelectSelector(
                SelectSelectorConfig(
                    options=[SelectOptionDict(value=unit, label=unit) for unit in OUTPUT_UNITS]
                )
            ),
            _required_marker(
                CONF_OUTPUT_VALUE_MODE, values, DEFAULT_OUTPUT_VALUE_MODE,
            ): SelectSelector(SelectSelectorConfig(
                options=list(OUTPUT_VALUE_MODES),
                translation_key=CONF_OUTPUT_VALUE_MODE,
            )),
            _required_marker(
                CONF_OUTPUT_SCALE, values, DEFAULT_OUTPUT_SCALE,
            ): NumberSelector(NumberSelectorConfig(
                min=0.000001, step=0.001, mode=NumberSelectorMode.BOX,
            )),
            _required_marker(
                CONF_OUTPUT_OFFSET, values, DEFAULT_OUTPUT_OFFSET,
            ): NumberSelector(NumberSelectorConfig(
                min=-1000000000.0, max=1000000000.0,
                step=0.001, mode=NumberSelectorMode.BOX,
            )),
            _optional_marker(
                CONF_OUTPUT_FORBIDDEN_VALUE, values,
            ): NumberSelector(NumberSelectorConfig(
                min=-1000000000.0, max=1000000000.0,
                step=0.001, mode=NumberSelectorMode.BOX,
            )),
            _required_marker(
                CONF_EVSE_ZERO_UNLIMITED, values, DEFAULT_EVSE_ZERO_UNLIMITED,
            ): BooleanSelector(),
            _required_marker(
                CONF_EVSE_OUTPUT_FORMAT, values, DEFAULT_EVSE_OUTPUT_FORMAT,
            ): SelectSelector(SelectSelectorConfig(
                options=[
                    SelectOptionDict(value=EVSE_OUTPUT_AUTO, label="Automatisch (HA-Entity)"),
                    SelectOptionDict(value=EVSE_OUTPUT_AMPERE, label="Ampere (A)"),
                    SelectOptionDict(value=EVSE_OUTPUT_WATT, label="Watt (W)"),
                    SelectOptionDict(value=EVSE_OUTPUT_KW, label="Kilowatt (kW)"),
                ],
            )),
            _required_marker(
                CONF_EVSE_CURRENT_STEP_A, values, DEFAULT_EVSE_CURRENT_STEP_A,
            ): NumberSelector(NumberSelectorConfig(
                min=0.1, max=100.0, step=0.1, unit_of_measurement="A",
                mode=NumberSelectorMode.BOX,
            )),
            _required_marker(
                CONF_EVSE_POWER_STEP_W, values, DEFAULT_EVSE_POWER_STEP_W,
            ): NumberSelector(NumberSelectorConfig(
                min=1.0, max=100000.0, step=1.0, unit_of_measurement="W",
                mode=NumberSelectorMode.BOX,
            )),
            _required_marker(
                CONF_EVSE_PAUSE_POWER_VALUE, values, DEFAULT_EVSE_PAUSE_POWER_VALUE,
            ): NumberSelector(NumberSelectorConfig(
                min=0.0, max=100000.0, step=0.01, mode=NumberSelectorMode.BOX,
            )),
            _required_marker(
                CONF_OUTPUT_TRANSPORT, values, DEFAULT_OUTPUT_TRANSPORT,
            ): SelectSelector(SelectSelectorConfig(
                options=list(OUTPUT_TRANSPORTS),
                translation_key=CONF_OUTPUT_TRANSPORT,
            )),
            _optional_marker(CONF_OUTPUT_STEPS_JSON, values): str,
            _required_marker(
                CONF_DEVICE_COMMANDS_CONFIRMED, values,
                DEFAULT_DEVICE_COMMANDS_CONFIRMED,
            ): BooleanSelector(),
            _optional_marker(CONF_MODBUS_HOST, values): str,
            _required_marker(
                CONF_MODBUS_PORT, values, DEFAULT_MODBUS_PORT,
            ): NumberSelector(NumberSelectorConfig(
                min=1, max=65535, step=1, mode=NumberSelectorMode.BOX,
            )),
            _required_marker(
                CONF_MODBUS_UNIT_ID, values, DEFAULT_MODBUS_UNIT_ID,
            ): NumberSelector(NumberSelectorConfig(
                min=1, max=247, step=1, mode=NumberSelectorMode.BOX,
            )),
            _required_marker(
                CONF_MODBUS_REGISTER, values, 0,
            ): NumberSelector(NumberSelectorConfig(
                min=0, max=65535, step=1, mode=NumberSelectorMode.BOX,
            )),
            _required_marker(
                CONF_MODBUS_DATA_TYPE, values, DEFAULT_MODBUS_DATA_TYPE,
            ): SelectSelector(SelectSelectorConfig(
                options=list(MODBUS_DATA_TYPES),
                translation_key=CONF_MODBUS_DATA_TYPE,
            )),
            _required_marker(
                CONF_MODBUS_BYTE_ORDER, values, DEFAULT_MODBUS_BYTE_ORDER,
            ): SelectSelector(SelectSelectorConfig(
                options=[SelectOptionDict(value=x, label=x) for x in MODBUS_BYTE_ORDERS],
            )),
            _required_marker(
                CONF_MODBUS_FUNCTION, values, DEFAULT_MODBUS_FUNCTION,
            ): NumberSelector(NumberSelectorConfig(
                min=6, max=16, step=1, mode=NumberSelectorMode.BOX,
            )),
            _required_marker(
                CONF_MODBUS_TIMEOUT_S, values, DEFAULT_MODBUS_TIMEOUT_S,
            ): NumberSelector(NumberSelectorConfig(
                min=0.1, max=60, step=0.1, mode=NumberSelectorMode.BOX,
            )),
            _optional_marker(CONF_MQTT_TOPIC, values): str,
            _required_marker(
                CONF_MQTT_QOS, values, DEFAULT_MQTT_QOS,
            ): NumberSelector(NumberSelectorConfig(
                min=0, max=2, step=1, mode=NumberSelectorMode.BOX,
            )),
            _required_marker(
                CONF_MQTT_RETAIN, values, DEFAULT_MQTT_RETAIN,
            ): BooleanSelector(),
            _required_marker(
                CONF_MQTT_PAYLOAD_TEMPLATE, values, DEFAULT_MQTT_PAYLOAD_TEMPLATE,
            ): str,
            _optional_marker(CONF_MQTT_ON_PAYLOAD, values): str,
            _optional_marker(CONF_MQTT_OFF_PAYLOAD, values): str,
            _required_marker(
                CONF_SWITCH_ON_CODE, values, DEFAULT_SWITCH_ON_CODE,
            ): NumberSelector(NumberSelectorConfig(
                min=-1000000000.0, max=1000000000.0,
                step=0.001, mode=NumberSelectorMode.BOX,
            )),
            _required_marker(
                CONF_SWITCH_OFF_CODE, values, DEFAULT_SWITCH_OFF_CODE,
            ): NumberSelector(NumberSelectorConfig(
                min=-1000000000.0, max=1000000000.0,
                step=0.001, mode=NumberSelectorMode.BOX,
            )),
            _required_marker(
                CONF_SAFE_OUTPUT_VALUE,
                values,
                DEFAULT_SAFE_OUTPUT_VALUE,
            ): NumberSelector(
                NumberSelectorConfig(
                    min=0.0,
                    step=0.01,
                    mode=NumberSelectorMode.BOX,
                )
            ),
            _required_marker(
                CONF_PEAK_SHAVING_ENABLED,
                values,
                DEFAULT_PEAK_SHAVING_ENABLED,
            ): BooleanSelector(),
            _required_marker(
                CONF_SURPLUS_ENABLED,
                values,
                DEFAULT_SURPLUS_ENABLED,
            ): BooleanSelector(),
            _required_marker(
                CONF_START_MARGIN_KW,
                values,
                DEFAULT_START_MARGIN_KW,
            ): _power_number_selector(),
            _required_marker(
                CONF_STOP_MARGIN_KW,
                values,
                DEFAULT_STOP_MARGIN_KW,
            ): _power_number_selector(),
            _required_marker(
                CONF_MIN_ON_TIME_S,
                values,
                DEFAULT_MIN_ON_TIME_S,
            ): _seconds_selector(),
            _required_marker(
                CONF_MIN_OFF_TIME_S,
                values,
                DEFAULT_MIN_OFF_TIME_S,
            ): _seconds_selector(),
            _required_marker(
                CONF_SETTLING_TIME_S,
                values,
                DEFAULT_SETTLING_TIME_S,
            ): _seconds_selector(),
            _required_marker(
                CONF_EVSE_PHASES,
                values,
                DEFAULT_EVSE_PHASES,
            ): NumberSelector(
                NumberSelectorConfig(
                    min=1,
                    max=3,
                    step=1,
                    mode=NumberSelectorMode.BOX,
                )
            ),
            _required_marker(
                CONF_EVSE_VOLTAGE_V,
                values,
                DEFAULT_EVSE_VOLTAGE_V,
            ): NumberSelector(
                NumberSelectorConfig(
                    min=1,
                    step=1,
                    unit_of_measurement="V",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            _required_marker(
                CONF_EVSE_MIN_CURRENT_A,
                values,
                DEFAULT_EVSE_MIN_CURRENT_A,
            ): NumberSelector(
                NumberSelectorConfig(
                    min=0.01,
                    step=0.01,
                    unit_of_measurement="A",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            _required_marker(
                CONF_EVSE_MAX_CURRENT_A,
                values,
                DEFAULT_EVSE_MAX_CURRENT_A,
            ): NumberSelector(
                NumberSelectorConfig(
                    min=0.01,
                    step=0.01,
                    unit_of_measurement="A",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            _required_marker(
                CONF_EVSE_PAUSE_CURRENT_A,
                values,
                DEFAULT_EVSE_PAUSE_CURRENT_A,
            ): NumberSelector(
                NumberSelectorConfig(
                    min=0.0,
                    step=0.01,
                    unit_of_measurement="A",
                    mode=NumberSelectorMode.BOX,
                )
            ),
        }
    )


def _duplicate_load_name(
    entry: ConfigEntry,
    name: str,
    *,
    exclude_subentry_id: str | None = None,
) -> bool:
    """Return whether another load already uses the same name."""

    normalized_name = name.strip().casefold()
    for subentry_id, subentry in entry.subentries.items():
        if subentry_id == exclude_subentry_id:
            continue
        if subentry.subentry_type != SUBENTRY_TYPE_LOAD:
            continue
        existing_name = str(subentry.data.get(CONF_LOAD_NAME, subentry.title))
        if existing_name.strip().casefold() == normalized_name:
            return True
    return False


class PowerManagerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Configure essential plant values, optionally show expert tuning."""

    VERSION = 4
    MINOR_VERSION = 0

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            self._global_values = _merge_global_basic({}, user_input)
            if user_input.get(_WIZARD_EXPERT):
                return await self.async_step_global_expert()
            errors = _validate_global_configuration(self._global_values)
            if not errors:
                return self.async_create_entry(
                    title=NAME, data=_normalize_global_configuration(self._global_values)
                )
        values = {**getattr(self, "_global_values", {}), **(user_input or {})}
        return self.async_show_form(
            step_id="user", data_schema=_global_simple_schema(values), errors=errors,
        )

    async def async_step_global_expert(
        self, user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            self._global_values.update(user_input)
            errors = _validate_global_configuration(self._global_values)
            if not errors:
                return self.async_create_entry(
                    title=NAME, data=_normalize_global_configuration(self._global_values)
                )
        return self.async_show_form(
            step_id="global_expert",
            data_schema=_global_expert_schema(
                {**getattr(self, "_global_values", {}), **(user_input or {})}
            ), errors=errors,
        )

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry,
    ) -> dict[str, type[ConfigSubentryFlow]]:
        return {SUBENTRY_TYPE_LOAD: PowerManagerLoadSubentryFlow}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> PowerManagerOptionsFlow:
        return PowerManagerOptionsFlow()


class PowerManagerOptionsFlow(OptionsFlow):
    """Edit core sensors and PMAX with optional expert controls."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        stored = {**self.config_entry.data, **self.config_entry.options}
        errors: dict[str, str] = {}
        if user_input is not None:
            self._global_values = _merge_global_basic(stored, user_input)
            if user_input.get(_WIZARD_EXPERT):
                return await self.async_step_global_expert()
            errors = _validate_global_configuration(self._global_values)
            if not errors:
                return self.async_create_entry(
                    title="", data=_normalize_global_configuration(self._global_values)
                )
        values = {**stored, **(user_input or {})}
        return self.async_show_form(
            step_id="init", data_schema=_global_simple_schema(values), errors=errors,
        )

    async def async_step_global_expert(
        self, user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            self._global_values.update(user_input)
            errors = _validate_global_configuration(self._global_values)
            if not errors:
                return self.async_create_entry(
                    title="", data=_normalize_global_configuration(self._global_values)
                )
        return self.async_show_form(
            step_id="global_expert",
            data_schema=_global_expert_schema(
                {**getattr(self, "_global_values", {}), **(user_input or {})}
            ), errors=errors,
        )


def _load_wizard_schema(
    values: dict[str, Any], fields: list[str] | tuple[str, ...],
    *, extra: dict[Any, Any] | None = None,
) -> probatio.Schema:
    canonical = _build_load_schema(values)
    result = dict(_subset_schema(canonical, fields).schema) if fields else {}
    result.update(extra or {})
    return probatio.Schema(result)


class PowerManagerLoadSubentryFlow(ConfigSubentryFlow):
    """Small step-by-step device setup, preserving expert capabilities.

    No live commands are issued by any configuration step.
    """

    def _load_draft(self) -> dict[str, Any]:
        if not hasattr(self, "_draft"):
            self._draft = {}
        return self._draft

    def _update_draft(
        self, user_input: dict[str, Any],
        *, optional: tuple[str, ...] = (),
    ) -> None:
        draft = self._load_draft()
        draft.update(user_input)
        for key in optional:
            if key not in user_input:
                draft.pop(key, None)

    def _form(
        self, step: str, fields: tuple[str, ...] | list[str],
        *, extra: dict[Any, Any] | None = None,
        errors: dict[str, str] | None = None,
    ) -> SubentryFlowResult:
        return self.async_show_form(
            step_id=step,
            data_schema=_load_wizard_schema(self._load_draft(), fields, extra=extra),
            errors=errors or {},
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None,
    ) -> SubentryFlowResult:
        """Start a new consumer; first step asks only four essential facts."""
        if not hasattr(self, "_draft"):
            self._draft = {}
            self._editing = False
        return await self.async_step_load_basics(user_input)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None,
    ) -> SubentryFlowResult:
        """Edit existing consumer without dropping previously stored controls."""
        if not hasattr(self, "_draft"):
            subentry = self._get_reconfigure_subentry()
            self._draft = dict(subentry.data)
            # Reconfirm safe commands after *every* reconfiguration.
            self._draft[CONF_DEVICE_COMMANDS_CONFIRMED] = False
            self._editing = True
        return await self.async_step_load_basics(user_input)

    async def async_step_load_basics(
        self, user_input: dict[str, Any] | None = None,
    ) -> SubentryFlowResult:
        if user_input is not None:
            self._update_draft(
                {k: v for k, v in user_input.items() if k != _WIZARD_EXPERT}
            )
            self._expert = bool(user_input.get(_WIZARD_EXPERT))
            if not str(self._draft.get(CONF_LOAD_NAME, "")).strip():
                return self._form("load_basics", (
                    CONF_LOAD_NAME, CONF_LOAD_TYPE, CONF_PRIORITY, CONF_MAX_KW,
                ), extra={
                    _required_marker(_WIZARD_EXPERT, user_input, False): BooleanSelector(),
                }, errors={CONF_LOAD_NAME: "load_name_required"})
            if float(self._draft.get(CONF_MAX_KW, 0)) <= 0:
                return self._form("load_basics", (
                    CONF_LOAD_NAME, CONF_LOAD_TYPE, CONF_PRIORITY, CONF_MAX_KW,
                ), extra={
                    _required_marker(_WIZARD_EXPERT, user_input, False): BooleanSelector(),
                }, errors={"base": "invalid_power_range"})
            return await self.async_step_load_usage()
        return self._form(
            "load_basics",
            (CONF_LOAD_NAME, CONF_LOAD_TYPE, CONF_PRIORITY, CONF_MAX_KW),
            extra={
                _required_marker(
                    _WIZARD_EXPERT,
                    {_WIZARD_EXPERT: getattr(self, "_expert", False)},
                    False,
                ): BooleanSelector(),
            },
        )

    async def async_step_load_usage(
        self, user_input: dict[str, Any] | None = None,
    ) -> SubentryFlowResult:
        if user_input is not None:
            self._update_draft(user_input, optional=(CONF_ACTUAL_POWER_ENTITY,))
            if self._draft[CONF_DEMAND_MODE] == DEMAND_MODE_SENSOR:
                return await self.async_step_load_request()
            self._draft.pop(CONF_REQUEST_ENTITY, None)
            return await self.async_step_load_connection()
        load_type = self._load_draft().get(CONF_LOAD_TYPE, DEFAULT_LOAD_TYPE)
        fields = [
            CONF_PEAK_SHAVING_ENABLED, CONF_SURPLUS_ENABLED,
            CONF_ACTUAL_POWER_ENTITY,
        ]
        if load_type == LOAD_TYPE_MODULATING:
            fields.append(CONF_MIN_KW)
        extra = {
            _required_marker(
                CONF_DEMAND_MODE, self._draft,
                DEMAND_MODE_SENSOR if self._draft.get(CONF_REQUEST_ENTITY)
                else DEMAND_MODE_ALWAYS,
            ): SelectSelector(SelectSelectorConfig(
                options=list(DEMAND_MODES), translation_key=CONF_DEMAND_MODE,
            )),
        }
        return self._form("load_usage", fields, extra=extra)

    async def async_step_load_request(
        self, user_input: dict[str, Any] | None = None,
    ) -> SubentryFlowResult:
        if user_input is not None:
            self._update_draft(user_input)
            return await self.async_step_load_connection()
        return self._form("load_request", (CONF_REQUEST_ENTITY,))

    async def async_step_load_connection(
        self, user_input: dict[str, Any] | None = None,
    ) -> SubentryFlowResult:
        if user_input is not None:
            self._update_draft(user_input)
            self._draft[CONF_DEVICE_COMMANDS_CONFIRMED] = False
            return await self.async_step_load_connection_details()
        fields = [CONF_OUTPUT_TRANSPORT]
        if self._load_draft().get(CONF_LOAD_TYPE) == LOAD_TYPE_MODULATING:
            fields.append(CONF_OUTPUT_VALUE_MODE)
        return self._form("load_connection", fields)

    def _connection_fields(self) -> list[str]:
        transport = self._load_draft().get(
            CONF_OUTPUT_TRANSPORT, DEFAULT_OUTPUT_TRANSPORT,
        )
        load_type = self._draft.get(CONF_LOAD_TYPE, DEFAULT_LOAD_TYPE)
        if transport == OUTPUT_TRANSPORT_ENTITY:
            return [CONF_OUTPUT_ENTITY] + (
                [CONF_ENABLE_ENTITY] if load_type != LOAD_TYPE_SWITCH else []
            )
        if transport == OUTPUT_TRANSPORT_MODBUS:
            return [
                CONF_MODBUS_HOST, CONF_MODBUS_PORT, CONF_MODBUS_UNIT_ID,
                CONF_MODBUS_REGISTER, CONF_MODBUS_DATA_TYPE,
                CONF_MODBUS_BYTE_ORDER, CONF_MODBUS_FUNCTION,
            ]
        if load_type == LOAD_TYPE_SWITCH:
            return [CONF_MQTT_TOPIC, CONF_MQTT_ON_PAYLOAD, CONF_MQTT_OFF_PAYLOAD]
        return [CONF_MQTT_TOPIC, CONF_MQTT_PAYLOAD_TEMPLATE]

    async def async_step_load_evse_format(
        self, user_input: dict[str, Any] | None = None,
    ) -> SubentryFlowResult:
        """Device command units are independent of the transport."""
        if user_input is not None:
            self._update_draft(user_input)
            return await self.async_step_load_commands()
        transport = self._draft.get(
            CONF_OUTPUT_TRANSPORT, DEFAULT_OUTPUT_TRANSPORT,
        )
        suggested = (
            EVSE_OUTPUT_AUTO if transport == OUTPUT_TRANSPORT_ENTITY
            else EVSE_OUTPUT_AMPERE if transport == OUTPUT_TRANSPORT_MODBUS
            else EVSE_OUTPUT_WATT
        )
        if CONF_EVSE_OUTPUT_FORMAT not in self._draft:
            self._draft[CONF_EVSE_OUTPUT_FORMAT] = suggested
        allowed = (
            list(EVSE_OUTPUT_FORMATS)
            if transport == OUTPUT_TRANSPORT_ENTITY
            else [EVSE_OUTPUT_AMPERE, EVSE_OUTPUT_WATT, EVSE_OUTPUT_KW]
        )
        return self._form("load_evse_format", [], extra={
            _required_marker(
                CONF_EVSE_OUTPUT_FORMAT, self._draft, suggested,
            ): SelectSelector(SelectSelectorConfig(
                options=[
                    SelectOptionDict(value=x, label={
                        EVSE_OUTPUT_AUTO:"Auto (HA)", EVSE_OUTPUT_AMPERE:"Ampere (A)",
                        EVSE_OUTPUT_WATT:"Watt (W)", EVSE_OUTPUT_KW:"Kilowatt (kW)",
                    }[x]) for x in allowed
                ],
            )),
        })

    async def async_step_load_connection_details(
        self, user_input: dict[str, Any] | None = None,
    ) -> SubentryFlowResult:
        if user_input is not None:
            self._update_draft(
                user_input, optional=(
                    CONF_OUTPUT_ENTITY, CONF_ENABLE_ENTITY,
                    CONF_MQTT_ON_PAYLOAD, CONF_MQTT_OFF_PAYLOAD,
                ),
            )
            if self._draft.get(CONF_LOAD_TYPE) == LOAD_TYPE_EVSE:
                return await self.async_step_load_evse_format()
            if not self._command_fields():
                return await self._after_commands()
            return await self.async_step_load_commands()
        return self._form("load_connection_details", self._connection_fields())

    def _command_fields(self) -> list[str]:
        load_type = self._load_draft().get(CONF_LOAD_TYPE, DEFAULT_LOAD_TYPE)
        transport = self._draft.get(CONF_OUTPUT_TRANSPORT, DEFAULT_OUTPUT_TRANSPORT)
        if load_type == LOAD_TYPE_EVSE:
            fields = [
                CONF_EVSE_PHASES, CONF_EVSE_MIN_CURRENT_A,
                CONF_EVSE_MAX_CURRENT_A,
            ]
            fmt = self._draft.get(
                CONF_EVSE_OUTPUT_FORMAT, DEFAULT_EVSE_OUTPUT_FORMAT,
            )
            if fmt in (EVSE_OUTPUT_AMPERE, EVSE_OUTPUT_AUTO):
                fields.extend((
                    CONF_EVSE_PAUSE_CURRENT_A, CONF_EVSE_CURRENT_STEP_A,
                    CONF_EVSE_ZERO_UNLIMITED,
                ))
            else:
                fields.extend((
                    CONF_EVSE_POWER_STEP_W, CONF_EVSE_PAUSE_POWER_VALUE,
                ))
            return fields
        if load_type == LOAD_TYPE_SWITCH:
            if transport == OUTPUT_TRANSPORT_ENTITY:
                return []
            if (
                transport == OUTPUT_TRANSPORT_MQTT
                and self._draft.get(CONF_MQTT_ON_PAYLOAD)
                and self._draft.get(CONF_MQTT_OFF_PAYLOAD)
            ):
                return []  # textual MQTT ON/OFF needs no numeric codes
            return [CONF_SWITCH_ON_CODE, CONF_SWITCH_OFF_CODE]
        mode = self._draft.get(CONF_OUTPUT_VALUE_MODE, DEFAULT_OUTPUT_VALUE_MODE)
        if mode == OUTPUT_VALUE_MODE_LINEAR:
            return [
                CONF_OUTPUT_SCALE, CONF_OUTPUT_OFFSET,
                CONF_SAFE_OUTPUT_VALUE, CONF_OUTPUT_FORBIDDEN_VALUE,
            ]
        fields = [CONF_SAFE_OUTPUT_VALUE, CONF_OUTPUT_FORBIDDEN_VALUE]
        if mode != OUTPUT_VALUE_MODE_STEPS:
            fields.insert(0, CONF_OUTPUT_UNIT)
        return fields

    async def async_step_load_commands(
        self, user_input: dict[str, Any] | None = None,
    ) -> SubentryFlowResult:
        if user_input is not None:
            self._update_draft(
                user_input, optional=(CONF_OUTPUT_FORBIDDEN_VALUE,),
            )
            if self._draft.get(CONF_LOAD_TYPE) == LOAD_TYPE_EVSE:
                self._draft[CONF_MIN_KW] = (
                    float(self._draft.get(CONF_EVSE_PHASES, DEFAULT_EVSE_PHASES))
                    * float(self._draft.get(CONF_EVSE_VOLTAGE_V, DEFAULT_EVSE_VOLTAGE_V))
                    * float(self._draft.get(
                        CONF_EVSE_MIN_CURRENT_A, DEFAULT_EVSE_MIN_CURRENT_A,
                    )) / 1000.0
                )
            if (
                self._draft.get(CONF_LOAD_TYPE) == LOAD_TYPE_MODULATING
                and self._draft.get(CONF_OUTPUT_VALUE_MODE) == OUTPUT_VALUE_MODE_STEPS
            ):
                return await self.async_step_load_stage_count()
            return await self._after_commands()
        if not self._command_fields():
            return await self._after_commands()
        return self._form("load_commands", self._command_fields())

    async def _after_commands(self) -> SubentryFlowResult:
        if getattr(self, "_expert", False):
            return await self.async_step_load_expert()
        return await self.async_step_load_review()

    async def async_step_load_stage_count(
        self, user_input: dict[str, Any] | None = None,
    ) -> SubentryFlowResult:
        if user_input is not None:
            self._stage_count = int(user_input[_WIZARD_STAGE_COUNT])
            return await self.async_step_load_stages()
        return self._form("load_stage_count", [], extra={
            probatio.Required(_WIZARD_STAGE_COUNT, default=2):
                NumberSelector(NumberSelectorConfig(
                    min=1, max=12, step=1, mode=NumberSelectorMode.BOX,
                )),
        })

    async def async_step_load_stages(
        self, user_input: dict[str, Any] | None = None,
    ) -> SubentryFlowResult:
        count = getattr(self, "_stage_count", 2)
        if user_input is not None:
            stages = [
                {"kw": float(user_input[f"stage_{i}_kw"]),
                 "code": float(user_input[f"stage_{i}_code"])}
                for i in range(1, count + 1)
            ]
            if any(
                stages[i]["kw"] <= stages[i - 1]["kw"]
                for i in range(1, len(stages))
            ):
                return self.async_show_form(
                    step_id="load_stages",
                    data_schema=self._stages_schema(count),
                    errors={"base": "stages_must_increase"},
                )
            self._draft[CONF_OUTPUT_STEPS_JSON] = json.dumps(stages)
            self._draft[CONF_MIN_KW] = stages[0]["kw"]
            return await self._after_commands()
        return self.async_show_form(
            step_id="load_stages", data_schema=self._stages_schema(count),
        )

    @staticmethod
    def _stages_schema(count: int) -> probatio.Schema:
        schema: dict[Any, Any] = {}
        for i in range(1, count + 1):
            schema[probatio.Required(f"stage_{i}_kw")] = NumberSelector(
                NumberSelectorConfig(
                    min=0.1, step=0.01,
                    unit_of_measurement="kW", mode=NumberSelectorMode.BOX,
                )
            )
            schema[probatio.Required(f"stage_{i}_code")] = NumberSelector(
                NumberSelectorConfig(
                    min=-1000000, max=1000000,
                    step=0.01, mode=NumberSelectorMode.BOX,
                )
            )
        return probatio.Schema(schema)

    async def async_step_load_expert(
        self, user_input: dict[str, Any] | None = None,
    ) -> SubentryFlowResult:
        if user_input is not None:
            self._update_draft(
                user_input, optional=(CONF_AVAILABILITY_ENTITY,),
            )
            return await self.async_step_load_review()
        fields = [
            CONF_AVAILABILITY_ENTITY, CONF_INVERT_ACTUAL_POWER,
            CONF_ACTUAL_SENSOR_TIMEOUT_S, CONF_FEEDBACK_TOLERANCE_KW,
            CONF_START_MARGIN_KW, CONF_STOP_MARGIN_KW,
            CONF_MIN_ON_TIME_S, CONF_MIN_OFF_TIME_S, CONF_SETTLING_TIME_S,
        ]
        if self._load_draft().get(CONF_OUTPUT_TRANSPORT) == OUTPUT_TRANSPORT_MODBUS:
            fields.append(CONF_MODBUS_TIMEOUT_S)
        if self._draft.get(CONF_OUTPUT_TRANSPORT) == OUTPUT_TRANSPORT_MQTT:
            fields.extend((CONF_MQTT_QOS, CONF_MQTT_RETAIN))
        if self._draft.get(CONF_LOAD_TYPE) == LOAD_TYPE_EVSE:
            fields.append(CONF_EVSE_VOLTAGE_V)
        if (
            self._draft.get(CONF_OUTPUT_TRANSPORT) != OUTPUT_TRANSPORT_ENTITY
            and self._draft.get(CONF_LOAD_TYPE) != LOAD_TYPE_SWITCH
        ):
            fields.append(CONF_ENABLE_ENTITY)
        return self._form("load_expert", fields)

    async def async_step_load_review(
        self, user_input: dict[str, Any] | None = None,
    ) -> SubentryFlowResult:
        direct = self._load_draft().get(
            CONF_OUTPUT_TRANSPORT, DEFAULT_OUTPUT_TRANSPORT,
        ) != OUTPUT_TRANSPORT_ENTITY
        if user_input is not None:
            if direct:
                self._draft[CONF_DEVICE_COMMANDS_CONFIRMED] = bool(
                    user_input.get(CONF_DEVICE_COMMANDS_CONFIRMED, False)
                )
            if not user_input.get(_WIZARD_ACK):
                return self._review_form({"base": "ack_required"})
            if self._draft.get(CONF_LOAD_TYPE) == LOAD_TYPE_EVSE:
                self._draft[CONF_MIN_KW] = (
                    float(self._draft.get(CONF_EVSE_PHASES, DEFAULT_EVSE_PHASES))
                    * float(self._draft.get(CONF_EVSE_VOLTAGE_V, DEFAULT_EVSE_VOLTAGE_V))
                    * float(self._draft.get(
                        CONF_EVSE_MIN_CURRENT_A, DEFAULT_EVSE_MIN_CURRENT_A,
                    )) / 1000.0
                )
            try:
                normalized = normalize_load_data(self._draft)
                errors = validate_load_data(normalized)
            except (KeyError, TypeError, ValueError, OverflowError):
                return self._review_form({"base": "invalid_number"})
            if not errors:
                except_id = None
                if getattr(self, "_editing", False):
                    except_id = self._get_reconfigure_subentry().subentry_id
                if _duplicate_load_name(
                    self._get_entry(), normalized[CONF_LOAD_NAME],
                    exclude_subentry_id=except_id,
                ):
                    errors[CONF_LOAD_NAME] = "duplicate_load_name"
            if errors:
                return self._invalid_wizard_fields(errors)
            if getattr(self, "_editing", False):
                subentry = self._get_reconfigure_subentry()
                return self.async_update_and_abort(
                    self._get_entry(), subentry, data=normalized,
                    title=normalized[CONF_LOAD_NAME],
                )
            return self.async_create_entry(
                title=normalized[CONF_LOAD_NAME], data=normalized,
            )
        return self._review_form()

    def _review_form(
        self, errors: dict[str, str] | None = None,
    ) -> SubentryFlowResult:
        extra = {
            probatio.Required(_WIZARD_ACK, default=False): BooleanSelector(),
        }
        fields = (
            (CONF_DEVICE_COMMANDS_CONFIRMED,)
            if self._load_draft().get(CONF_OUTPUT_TRANSPORT)
                != OUTPUT_TRANSPORT_ENTITY else ()
        )
        return self.async_show_form(
            step_id="load_review",
            data_schema=_load_wizard_schema(self._draft, fields, extra=extra),
            errors=errors or {},
            description_placeholders=_device_preview(self._draft, self.hass),
        )

    def _invalid_wizard_fields(
        self, errors: dict[str, str],
    ) -> SubentryFlowResult:
        # Redirect the user to the page with the invalid field, never hide
        # field validation errors in a form that does not contain the field.
        key = next(iter(errors))
        basics = {
            CONF_LOAD_NAME, CONF_LOAD_TYPE, CONF_PRIORITY, CONF_MAX_KW,
        }
        usage = {
            CONF_MIN_KW, CONF_DEMAND_MODE, CONF_ACTUAL_POWER_ENTITY,
            CONF_PEAK_SHAVING_ENABLED, CONF_SURPLUS_ENABLED,
        }
        if key in basics or key == "base":
            return self._form("load_basics", (
                CONF_LOAD_NAME, CONF_LOAD_TYPE, CONF_PRIORITY, CONF_MAX_KW,
            ), extra={
                _required_marker(_WIZARD_EXPERT, {
                    _WIZARD_EXPERT: getattr(self, "_expert", False),
                }, False): BooleanSelector(),
            }, errors=errors)
        if key in usage:
            fields = list(usage - {CONF_DEMAND_MODE})
            return self._form("load_usage", fields, extra={
                _required_marker(CONF_DEMAND_MODE, self._draft, DEMAND_MODE_ALWAYS):
                    SelectSelector(SelectSelectorConfig(
                        options=list(DEMAND_MODES), translation_key=CONF_DEMAND_MODE,
                    )),
            }, errors=errors)
        if key == CONF_REQUEST_ENTITY:
            return self._form("load_request", (CONF_REQUEST_ENTITY,), errors=errors)
        if key in {
            CONF_OUTPUT_TRANSPORT, CONF_OUTPUT_VALUE_MODE,
        }:
            return self._form(
                "load_connection",
                (CONF_OUTPUT_TRANSPORT, CONF_OUTPUT_VALUE_MODE)
                if self._draft.get(CONF_LOAD_TYPE) == LOAD_TYPE_MODULATING
                else (CONF_OUTPUT_TRANSPORT,),
                errors=errors,
            )
        if key == CONF_EVSE_OUTPUT_FORMAT:
            transport = self._draft.get(
                CONF_OUTPUT_TRANSPORT, DEFAULT_OUTPUT_TRANSPORT,
            )
            choices = (
                list(EVSE_OUTPUT_FORMATS)
                if transport == OUTPUT_TRANSPORT_ENTITY
                else [EVSE_OUTPUT_AMPERE, EVSE_OUTPUT_WATT, EVSE_OUTPUT_KW]
            )
            return self._form(
                "load_evse_format", [],
                extra={
                    _required_marker(
                        CONF_EVSE_OUTPUT_FORMAT, self._draft,
                        DEFAULT_EVSE_OUTPUT_FORMAT,
                    ): SelectSelector(SelectSelectorConfig(
                        options=[
                            SelectOptionDict(value=x, label={
                                EVSE_OUTPUT_AUTO: "Auto (HA)",
                                EVSE_OUTPUT_AMPERE: "Ampere (A)",
                                EVSE_OUTPUT_WATT: "Watt (W)",
                                EVSE_OUTPUT_KW: "Kilowatt (kW)",
                            }[x]) for x in choices
                        ],
                    )),
                },
                errors=errors,
            )
        # Return to the relevant specific setup step; it will render only
        # that protocol's fields.
        if key in self._connection_fields():
            return self._form(
                "load_connection_details", self._connection_fields(), errors=errors,
            )
        if key in self._command_fields():
            return self._form("load_commands", self._command_fields(), errors=errors)
        if key in (CONF_DEVICE_COMMANDS_CONFIRMED,):
            return self._review_form(errors)
        if key == CONF_OUTPUT_STEPS_JSON:
            return self.async_show_form(
                step_id="load_stages",
                data_schema=self._stages_schema(getattr(self, "_stage_count", 2)),
                errors={"base": "invalid_output_steps"},
            )
        # For remaining errors show a safe summary and allow expert path
        # to edit unusual fields.
        return self._review_form({"base": "device_configuration_invalid"})


