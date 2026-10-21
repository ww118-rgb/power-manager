"""Pure configuration helpers for Power Manager loads."""

from __future__ import annotations

from math import isfinite
import json
from typing import Any

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
    DEFAULT_DEVICE_COMMANDS_CONFIRMED,
    OUTPUT_VALUE_MODE_STEPS,
    OUTPUT_TRANSPORTS,
    OUTPUT_TRANSPORT_ENTITY,
    OUTPUT_TRANSPORT_MODBUS,
    OUTPUT_TRANSPORT_MQTT,
    MODBUS_DATA_TYPES,
    MODBUS_BYTE_ORDERS,
    CONF_ACTUAL_SENSOR_TIMEOUT_S,
    CONF_FEEDBACK_TOLERANCE_KW,
    CONF_DEFAULT_REQUEST_KW,
    CONF_ENABLE_ENTITY,
    CONF_EVSE_MAX_CURRENT_A,
    CONF_EVSE_MIN_CURRENT_A,
    CONF_EVSE_PAUSE_CURRENT_A,
    CONF_EVSE_PHASES,
    CONF_EVSE_VOLTAGE_V,
    CONF_LOAD_NAME,
    CONF_LOAD_TYPE,
    CONF_MAX_KW,
    CONF_MIN_KW,
    CONF_MIN_OFF_TIME_S,
    CONF_MIN_ON_TIME_S,
    CONF_OUTPUT_ENTITY,
    CONF_OUTPUT_UNIT,
    CONF_PRIORITY,
    CONF_SAFE_OUTPUT_VALUE,
    CONF_OUTPUT_VALUE_MODE, CONF_OUTPUT_SCALE, CONF_OUTPUT_OFFSET,
    CONF_OUTPUT_FORBIDDEN_VALUE, CONF_EVSE_ZERO_UNLIMITED,
    CONF_SETTLING_TIME_S,
    CONF_START_MARGIN_KW,
    CONF_STOP_MARGIN_KW,
    DEFAULT_ACTUAL_SENSOR_TIMEOUT_S,
    DEFAULT_FEEDBACK_TOLERANCE_KW,
    DEFAULT_DEFAULT_REQUEST_KW,
    DEFAULT_EVSE_MAX_CURRENT_A,
    DEFAULT_EVSE_MIN_CURRENT_A,
    DEFAULT_EVSE_PAUSE_CURRENT_A,
    DEFAULT_EVSE_PHASES,
    DEFAULT_EVSE_VOLTAGE_V,
    DEFAULT_LOAD_TYPE,
    DEFAULT_MAX_KW,
    DEFAULT_MIN_KW,
    DEFAULT_MIN_OFF_TIME_S,
    DEFAULT_MIN_ON_TIME_S,
    DEFAULT_OUTPUT_UNIT,
    DEFAULT_PRIORITY,
    DEFAULT_SAFE_OUTPUT_VALUE,
    DEFAULT_OUTPUT_VALUE_MODE, DEFAULT_OUTPUT_SCALE, DEFAULT_OUTPUT_OFFSET,
    DEFAULT_EVSE_ZERO_UNLIMITED, OUTPUT_VALUE_MODES, OUTPUT_VALUE_MODE_LINEAR,
    DEFAULT_SETTLING_TIME_S,
    DEFAULT_START_MARGIN_KW,
    DEFAULT_STOP_MARGIN_KW,
    LOAD_TYPE_EVSE,
    LOAD_TYPE_SWITCH,
    LOAD_TYPES,
    OUTPUT_UNITS,
    SUPPORTED_NUMBER_DOMAINS,
    SUPPORTED_SWITCH_DOMAINS,
)


def _float_value(data: dict[str, Any], key: str, default: float) -> float:
    """Return a finite float or raise ValueError."""

    value = float(data.get(key, default))
    if not isfinite(value):
        raise ValueError(f"{key} must be finite")
    return value


def _entity_domain(entity_id: str | None) -> str | None:
    """Return the domain part of an entity id."""

    if not entity_id or "." not in entity_id:
        return None
    return entity_id.split(".", 1)[0]


def normalize_load_data(data: dict[str, Any]) -> dict[str, Any]:
    """Return normalized JSON-serializable load configuration."""

    normalized = dict(data)
    load_type = str(normalized.get(CONF_LOAD_TYPE, DEFAULT_LOAD_TYPE))

    normalized[CONF_LOAD_NAME] = str(normalized.get(CONF_LOAD_NAME, "")).strip()
    normalized[CONF_LOAD_TYPE] = load_type
    normalized[CONF_PRIORITY] = int(normalized.get(CONF_PRIORITY, DEFAULT_PRIORITY))
    normalized[CONF_MIN_KW] = _float_value(normalized, CONF_MIN_KW, DEFAULT_MIN_KW)
    normalized[CONF_MAX_KW] = _float_value(normalized, CONF_MAX_KW, DEFAULT_MAX_KW)
    normalized[CONF_DEFAULT_REQUEST_KW] = _float_value(
        normalized,
        CONF_DEFAULT_REQUEST_KW,
        DEFAULT_DEFAULT_REQUEST_KW,
    )
    normalized[CONF_ACTUAL_SENSOR_TIMEOUT_S] = _float_value(
        normalized,
        CONF_ACTUAL_SENSOR_TIMEOUT_S,
        DEFAULT_ACTUAL_SENSOR_TIMEOUT_S,
    )
    normalized[CONF_FEEDBACK_TOLERANCE_KW] = _float_value(
        normalized, CONF_FEEDBACK_TOLERANCE_KW, DEFAULT_FEEDBACK_TOLERANCE_KW,
    )
    normalized[CONF_START_MARGIN_KW] = _float_value(
        normalized,
        CONF_START_MARGIN_KW,
        DEFAULT_START_MARGIN_KW,
    )
    normalized[CONF_STOP_MARGIN_KW] = _float_value(
        normalized,
        CONF_STOP_MARGIN_KW,
        DEFAULT_STOP_MARGIN_KW,
    )
    normalized[CONF_MIN_ON_TIME_S] = _float_value(
        normalized,
        CONF_MIN_ON_TIME_S,
        DEFAULT_MIN_ON_TIME_S,
    )
    normalized[CONF_MIN_OFF_TIME_S] = _float_value(
        normalized,
        CONF_MIN_OFF_TIME_S,
        DEFAULT_MIN_OFF_TIME_S,
    )
    normalized[CONF_SETTLING_TIME_S] = _float_value(
        normalized,
        CONF_SETTLING_TIME_S,
        DEFAULT_SETTLING_TIME_S,
    )
    normalized[CONF_SAFE_OUTPUT_VALUE] = _float_value(
        normalized,
        CONF_SAFE_OUTPUT_VALUE,
        DEFAULT_SAFE_OUTPUT_VALUE,
    )
    normalized[CONF_OUTPUT_UNIT] = str(
        normalized.get(CONF_OUTPUT_UNIT, DEFAULT_OUTPUT_UNIT)
    )
    normalized[CONF_OUTPUT_VALUE_MODE] = str(
        normalized.get(CONF_OUTPUT_VALUE_MODE, DEFAULT_OUTPUT_VALUE_MODE)
    )
    normalized[CONF_OUTPUT_SCALE] = _float_value(
        normalized, CONF_OUTPUT_SCALE, DEFAULT_OUTPUT_SCALE,
    )
    normalized[CONF_OUTPUT_OFFSET] = _float_value(
        normalized, CONF_OUTPUT_OFFSET, DEFAULT_OUTPUT_OFFSET,
    )
    forbidden = normalized.get(CONF_OUTPUT_FORBIDDEN_VALUE)
    normalized[CONF_OUTPUT_FORBIDDEN_VALUE] = (
        None if forbidden is None or forbidden == ""
        else _float_value(normalized, CONF_OUTPUT_FORBIDDEN_VALUE, 0.0)
    )
    normalized[CONF_EVSE_ZERO_UNLIMITED] = bool(
        normalized.get(CONF_EVSE_ZERO_UNLIMITED, DEFAULT_EVSE_ZERO_UNLIMITED)
    )

    normalized[CONF_OUTPUT_STEPS_JSON] = str(
        normalized.get(CONF_OUTPUT_STEPS_JSON, DEFAULT_OUTPUT_STEPS_JSON)
    )
    normalized[CONF_OUTPUT_TRANSPORT] = str(
        normalized.get(CONF_OUTPUT_TRANSPORT, DEFAULT_OUTPUT_TRANSPORT)
    )
    normalized[CONF_MODBUS_HOST] = str(normalized.get(CONF_MODBUS_HOST, "")).strip()
    normalized[CONF_MODBUS_PORT] = int(normalized.get(CONF_MODBUS_PORT, DEFAULT_MODBUS_PORT))
    normalized[CONF_MODBUS_UNIT_ID] = int(normalized.get(CONF_MODBUS_UNIT_ID, DEFAULT_MODBUS_UNIT_ID))
    normalized[CONF_MODBUS_REGISTER] = int(normalized.get(CONF_MODBUS_REGISTER, 0))
    normalized[CONF_MODBUS_DATA_TYPE] = str(normalized.get(CONF_MODBUS_DATA_TYPE, DEFAULT_MODBUS_DATA_TYPE))
    normalized[CONF_MODBUS_BYTE_ORDER] = str(normalized.get(CONF_MODBUS_BYTE_ORDER, DEFAULT_MODBUS_BYTE_ORDER))
    normalized[CONF_MODBUS_FUNCTION] = int(normalized.get(CONF_MODBUS_FUNCTION, DEFAULT_MODBUS_FUNCTION))
    normalized[CONF_MODBUS_TIMEOUT_S] = _float_value(normalized, CONF_MODBUS_TIMEOUT_S, DEFAULT_MODBUS_TIMEOUT_S)
    normalized[CONF_MQTT_TOPIC] = str(normalized.get(CONF_MQTT_TOPIC, "")).strip()
    normalized[CONF_MQTT_QOS] = int(normalized.get(CONF_MQTT_QOS, DEFAULT_MQTT_QOS))
    normalized[CONF_MQTT_RETAIN] = bool(normalized.get(CONF_MQTT_RETAIN, DEFAULT_MQTT_RETAIN))
    normalized[CONF_MQTT_PAYLOAD_TEMPLATE] = str(normalized.get(CONF_MQTT_PAYLOAD_TEMPLATE, DEFAULT_MQTT_PAYLOAD_TEMPLATE))
    normalized[CONF_SWITCH_ON_CODE] = _float_value(normalized, CONF_SWITCH_ON_CODE, DEFAULT_SWITCH_ON_CODE)
    normalized[CONF_SWITCH_OFF_CODE] = _float_value(normalized, CONF_SWITCH_OFF_CODE, DEFAULT_SWITCH_OFF_CODE)
    normalized[CONF_DEVICE_COMMANDS_CONFIRMED] = bool(
        normalized.get(CONF_DEVICE_COMMANDS_CONFIRMED, DEFAULT_DEVICE_COMMANDS_CONFIRMED)
    )

    normalized[CONF_EVSE_PHASES] = int(
        normalized.get(CONF_EVSE_PHASES, DEFAULT_EVSE_PHASES)
    )
    normalized[CONF_EVSE_VOLTAGE_V] = _float_value(
        normalized,
        CONF_EVSE_VOLTAGE_V,
        DEFAULT_EVSE_VOLTAGE_V,
    )
    normalized[CONF_EVSE_MIN_CURRENT_A] = _float_value(
        normalized,
        CONF_EVSE_MIN_CURRENT_A,
        DEFAULT_EVSE_MIN_CURRENT_A,
    )
    normalized[CONF_EVSE_MAX_CURRENT_A] = _float_value(
        normalized,
        CONF_EVSE_MAX_CURRENT_A,
        DEFAULT_EVSE_MAX_CURRENT_A,
    )
    normalized[CONF_EVSE_PAUSE_CURRENT_A] = _float_value(
        normalized,
        CONF_EVSE_PAUSE_CURRENT_A,
        DEFAULT_EVSE_PAUSE_CURRENT_A,
    )

    # A switchable load cannot physically modulate. Its technical minimum is
    # therefore identical to its rated / maximum power.
    if load_type == LOAD_TYPE_SWITCH:
        normalized[CONF_MIN_KW] = normalized[CONF_MAX_KW]

    return normalized


def validate_load_data(data: dict[str, Any]) -> dict[str, str]:
    """Validate load configuration and return Home Assistant style errors."""

    errors: dict[str, str] = {}

    try:
        values = normalize_load_data(data)
    except (TypeError, ValueError, OverflowError):
        return {"base": "invalid_number"}

    name = values[CONF_LOAD_NAME]
    load_type = values[CONF_LOAD_TYPE]
    priority = values[CONF_PRIORITY]
    min_kw = values[CONF_MIN_KW]
    max_kw = values[CONF_MAX_KW]
    default_request_kw = values[CONF_DEFAULT_REQUEST_KW]
    start_margin_kw = values[CONF_START_MARGIN_KW]
    stop_margin_kw = values[CONF_STOP_MARGIN_KW]

    if not name:
        errors[CONF_LOAD_NAME] = "load_name_required"

    if load_type not in LOAD_TYPES:
        errors[CONF_LOAD_TYPE] = "invalid_load_type"

    if priority < 1:
        errors[CONF_PRIORITY] = "priority_must_be_positive"

    if min_kw < 0.0 or max_kw <= 0.0 or min_kw > max_kw:
        errors["base"] = "invalid_power_range"

    if default_request_kw < 0.0 or default_request_kw > max_kw:
        errors[CONF_DEFAULT_REQUEST_KW] = "invalid_default_request"
    elif 0.0 < default_request_kw < min_kw:
        errors[CONF_DEFAULT_REQUEST_KW] = "request_below_minimum"

    if values[CONF_ACTUAL_SENSOR_TIMEOUT_S] <= 0.0:
        errors[CONF_ACTUAL_SENSOR_TIMEOUT_S] = "actual_timeout_must_be_positive"
    if values[CONF_FEEDBACK_TOLERANCE_KW] < 0:
        errors[CONF_FEEDBACK_TOLERANCE_KW] = "invalid_number"

    if start_margin_kw < 0.0 or stop_margin_kw < 0.0:
        errors["base"] = "invalid_hysteresis"
    elif stop_margin_kw > start_margin_kw:
        errors[CONF_STOP_MARGIN_KW] = "stop_margin_above_start_margin"

    for key in (CONF_MIN_ON_TIME_S, CONF_MIN_OFF_TIME_S, CONF_SETTLING_TIME_S):
        if values[key] < 0.0:
            errors[key] = "time_must_be_nonnegative"

    if values[CONF_OUTPUT_UNIT] not in OUTPUT_UNITS:
        errors[CONF_OUTPUT_UNIT] = "invalid_output_unit"

    if values[CONF_SAFE_OUTPUT_VALUE] < 0.0:
        errors[CONF_SAFE_OUTPUT_VALUE] = "safe_output_must_be_nonnegative"
    if values[CONF_OUTPUT_VALUE_MODE] not in OUTPUT_VALUE_MODES:
        errors[CONF_OUTPUT_VALUE_MODE] = "invalid_output_value_mode"
    if values[CONF_OUTPUT_VALUE_MODE] == OUTPUT_VALUE_MODE_LINEAR:
        if values[CONF_OUTPUT_SCALE] <= 0:
            errors[CONF_OUTPUT_SCALE] = "output_scale_must_be_positive"
    forbidden = values[CONF_OUTPUT_FORBIDDEN_VALUE]
    if forbidden is not None and abs(
        values[CONF_SAFE_OUTPUT_VALUE] - forbidden
    ) <= 0.000001 and load_type != LOAD_TYPE_EVSE:
        errors[CONF_SAFE_OUTPUT_VALUE] = "forbidden_pause_code"

    transport = values[CONF_OUTPUT_TRANSPORT]
    if transport not in OUTPUT_TRANSPORTS:
        errors[CONF_OUTPUT_TRANSPORT] = "invalid_transport"
    if transport != OUTPUT_TRANSPORT_ENTITY and not values[CONF_DEVICE_COMMANDS_CONFIRMED]:
        errors[CONF_DEVICE_COMMANDS_CONFIRMED] = "unsafe_command_unconfirmed"
    if transport == OUTPUT_TRANSPORT_MODBUS:
        if not values[CONF_MODBUS_HOST] or any(c in values[CONF_MODBUS_HOST] for c in "/ \\n\\x00"):
            errors[CONF_MODBUS_HOST] = "invalid_modbus_host"
        if not (1 <= values[CONF_MODBUS_PORT] <= 65535 and 1 <= values[CONF_MODBUS_UNIT_ID] <= 247
                and 0 <= values[CONF_MODBUS_REGISTER] <= 65535):
            errors[CONF_MODBUS_REGISTER] = "invalid_modbus_address"
        if (values[CONF_MODBUS_DATA_TYPE] not in MODBUS_DATA_TYPES
                or values[CONF_MODBUS_BYTE_ORDER] not in MODBUS_BYTE_ORDERS):
            errors[CONF_MODBUS_DATA_TYPE] = "invalid_modbus_encoding"
        if values[CONF_MODBUS_FUNCTION] not in (6, 16):
            errors[CONF_MODBUS_FUNCTION] = "invalid_modbus_function"
        if not 0 < values[CONF_MODBUS_TIMEOUT_S] <= 60:
            errors[CONF_MODBUS_TIMEOUT_S] = "invalid_modbus_timeout"
        if values[CONF_MODBUS_FUNCTION] == 6 and values[CONF_MODBUS_DATA_TYPE] != "uint16" and values[CONF_MODBUS_DATA_TYPE] != "int16":
            errors[CONF_MODBUS_FUNCTION] = "invalid_modbus_function"
    if transport == OUTPUT_TRANSPORT_MQTT:
        topic = values[CONF_MQTT_TOPIC]
        if not topic or any(c in topic for c in "#+\\x00"):
            errors[CONF_MQTT_TOPIC] = "invalid_mqtt_topic"
        if values[CONF_MQTT_QOS] not in (0,1,2):
            errors[CONF_MQTT_QOS] = "invalid_mqtt_qos"
        if "{value}" not in values[CONF_MQTT_PAYLOAD_TEMPLATE]:
            errors[CONF_MQTT_PAYLOAD_TEMPLATE] = "invalid_mqtt_template"
    if values[CONF_OUTPUT_VALUE_MODE] == OUTPUT_VALUE_MODE_STEPS and load_type == LOAD_TYPE_MODULATING:
        try:
            steps = json.loads(values[CONF_OUTPUT_STEPS_JSON])
            if (not isinstance(steps,list) or not steps
                    or any(not isinstance(v,dict) or
                       not {"kw","code"} <= v.keys() for v in steps)):
                raise ValueError("Steps must be ordered [kw,code] objects")
            entries = [(float(v["kw"]),float(v["code"])) for v in steps]
            if (any(not (isfinite(k) and isfinite(c) and k > 0) for k,c in entries)
                    or entries != sorted(entries)
                    or len({k for k,_ in entries}) != len(entries)
                    or entries[0][0] > min_kw + 1e-6):
                raise ValueError("Invalid ordered stages or device minimum")
            if forbidden is not None and any(abs(c-forbidden)<1e-6 for _,c in entries):
                raise ValueError("Forbidden device code in stages")
        except (ValueError, TypeError, KeyError):
            errors[CONF_OUTPUT_STEPS_JSON] = "invalid_output_steps"
    if (transport != OUTPUT_TRANSPORT_ENTITY and
            load_type != LOAD_TYPE_SWITCH and
            values[CONF_OUTPUT_VALUE_MODE] == "power" and
            values[CONF_OUTPUT_UNIT] == "auto" and load_type != LOAD_TYPE_EVSE):
        errors[CONF_OUTPUT_UNIT] = "unit_required_for_direct_transport"


    output_domain = _entity_domain(values.get(CONF_OUTPUT_ENTITY))
    enable_domain = _entity_domain(values.get(CONF_ENABLE_ENTITY))

    if values.get(CONF_OUTPUT_ENTITY):
        if load_type == LOAD_TYPE_SWITCH:
            if output_domain not in SUPPORTED_SWITCH_DOMAINS:
                errors[CONF_OUTPUT_ENTITY] = "switch_output_required"
        elif output_domain not in SUPPORTED_NUMBER_DOMAINS:
            errors[CONF_OUTPUT_ENTITY] = "number_output_required"

    if values.get(CONF_ENABLE_ENTITY) and enable_domain not in SUPPORTED_SWITCH_DOMAINS:
        errors[CONF_ENABLE_ENTITY] = "enable_switch_required"

    if load_type == LOAD_TYPE_EVSE:
        phases = values[CONF_EVSE_PHASES]
        voltage_v = values[CONF_EVSE_VOLTAGE_V]
        min_current_a = values[CONF_EVSE_MIN_CURRENT_A]
        max_current_a = values[CONF_EVSE_MAX_CURRENT_A]
        pause_current_a = values[CONF_EVSE_PAUSE_CURRENT_A]

        if phases not in (1, 2, 3):
            errors[CONF_EVSE_PHASES] = "invalid_evse_phases"
        if voltage_v <= 0.0:
            errors[CONF_EVSE_VOLTAGE_V] = "must_be_positive"
        if min_current_a <= 0.0 or max_current_a < min_current_a:
            errors["base"] = "invalid_current_range"
        if pause_current_a < 0.0 or pause_current_a >= min_current_a:
            errors[CONF_EVSE_PAUSE_CURRENT_A] = "invalid_pause_current"
        if values[CONF_EVSE_ZERO_UNLIMITED] and pause_current_a <= 0.0:
            errors[CONF_EVSE_PAUSE_CURRENT_A] = "evse_zero_means_unlimited"
        if (forbidden is not None and abs(pause_current_a - forbidden) <= 0.000001
                and not (values[CONF_EVSE_ZERO_UNLIMITED] and pause_current_a <= 0.0)):
            errors[CONF_EVSE_PAUSE_CURRENT_A] = "forbidden_pause_code"

        min_power_kw = phases * voltage_v * min_current_a / 1000.0
        max_power_kw = phases * voltage_v * max_current_a / 1000.0
        if min_kw + 0.000001 < min_power_kw:
            errors[CONF_MIN_KW] = "evse_min_power_below_current_minimum"
        if max_kw > max_power_kw + 0.000001:
            errors[CONF_MAX_KW] = "evse_max_power_above_current_maximum"

    return errors
