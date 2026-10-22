"""V3.3.1 beginner installation and compatibility regression tests."""
import json
from pathlib import Path

import pytest

from custom_components.power_manager.const import (
    CONF_DEMAND_MODE, DEMAND_MODE_ALWAYS, DEMAND_MODE_SENSOR,
    DEMAND_MODE_DISABLED,
)
from custom_components.power_manager.load_config import (
    normalize_load_data, validate_load_data,
)

BASE = Path(__file__).parent / "custom_components" / "power_manager"


def load(**kwargs):
    values = dict(
        load_name="Device", load_type="modulating", min_kw=1,
        max_kw=5, priority=1, output_entity="number.dummy",
    )
    values.update(kwargs)
    return values


def test_legacy_config_without_request_sensor_stays_always_available():
    normalized = normalize_load_data(load())
    assert normalized[CONF_DEMAND_MODE] == DEMAND_MODE_ALWAYS


def test_legacy_config_with_request_entity_retains_sensor_mode():
    normalized = normalize_load_data(load(request_entity="sensor.need"))
    assert normalized[CONF_DEMAND_MODE] == DEMAND_MODE_SENSOR


def test_explicit_disabled_stays_disabled():
    normalized = normalize_load_data(
        load(demand_mode=DEMAND_MODE_DISABLED, request_entity="sensor.need")
    )
    assert normalized[CONF_DEMAND_MODE] == DEMAND_MODE_DISABLED


def test_selected_sensor_mode_must_have_actual_request_entity():
    errors = validate_load_data(load(demand_mode=DEMAND_MODE_SENSOR))
    assert errors["request_entity"] == "request_sensor_required"


def test_unknown_demand_mode_rejected():
    errors = validate_load_data(load(demand_mode="mystery"))
    assert errors["demand_mode"] == "invalid_demand_mode"


@pytest.mark.parametrize("file", ["strings.json", "translations/en.json", "translations/de.json"])
def test_every_wizard_step_is_translated(file):
    j = json.loads((BASE / file).read_text(encoding="utf-8"))
    s = j["config_subentries"]["load"]["step"]
    for step in (
        "load_basics", "load_usage", "load_request", "load_connection",
        "load_connection_details", "load_commands", "load_stage_count",
        "load_stages", "load_expert", "load_review",
    ):
        assert s[step]["title"] and s[step]["description"], (file, step)
    for idx in range(1, 13):
        assert f"stage_{idx}_kw" in s["load_stages"]["data"]
        assert f"stage_{idx}_code" in s["load_stages"]["data"]
    assert j["selector"]["demand_mode"]["options"]["disabled"]
    assert "global_expert" in j["config"]["step"]
    assert "global_expert" in j["options"]["step"]


def test_translation_does_not_interpolate_mqtt_device_placeholder():
    for file in ("strings.json", "translations/en.json", "translations/de.json"):
        j = json.loads((BASE / file).read_text(encoding="utf-8"))
        for step in j["config_subentries"]["load"]["step"].values():
            assert "{value}" not in step.get("data", {}).get(
                "mqtt_payload_template", ""
            )
            assert "{value}" not in step.get("data_description", {}).get(
                "mqtt_payload_template", ""
            )


def test_wizard_does_not_surface_every_protocol_in_first_form():
    code = (BASE / "config_flow.py").read_text(encoding="utf-8")
    assert "def _subset_schema" in code
    assert "async_step_load_basics" in code
    assert "async_step_load_usage" in code
    assert "async_step_load_connection_details" in code
    assert "async_step_load_review" in code
    assert "async_step_load_stages" in code
    assert "async_step_load_expert" in code


def test_live_sensor_feedback_mandatory_gate_unchanged():
    code = (BASE / "coordinator.py").read_text(encoding="utf-8")
    assert "Live-Regelung benötigt eine echte Istleistungs-Entity" in code


def test_wizard_does_not_enable_live_control():
    code = (BASE / "config_flow.py").read_text(encoding="utf-8")
    assert "async_enable_live_control(" not in code
