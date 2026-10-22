import json
from pathlib import Path

from custom_components.power_manager.const import VERSION

ROOT = Path(__file__).parent
COMPONENT = ROOT / "custom_components" / "power_manager"


def _json(relative: str):
    return json.loads((COMPONENT / relative).read_text(encoding="utf-8"))


def test_manifest_and_runtime_version_match_v4():
    manifest = _json("manifest.json")
    assert manifest["version"] == "4.0.0-rc.3"
    assert VERSION == manifest["version"]


def test_manifest_has_no_external_python_requirements():
    manifest = _json("manifest.json")
    assert manifest["requirements"] == []


def test_all_translation_json_files_parse():
    _json("strings.json")
    _json("translations/en.json")
    _json("translations/de.json")


def test_english_reconfigure_load_form_has_all_add_form_fields():
    data = _json("strings.json")["config_subentries"]["load"]["step"]
    assert data["reconfigure"]["data"] == data["user"]["data"]
    assert data["reconfigure"]["data_description"] == data["user"]["data_description"]


def test_german_reconfigure_load_form_has_all_add_form_fields():
    data = _json("translations/de.json")["config_subentries"]["load"]["step"]
    assert data["reconfigure"]["data"] == data["user"]["data"]
    assert data["reconfigure"]["data_description"] == data["user"]["data_description"]


def test_selector_translations_cover_runtime_options():
    selectors = _json("strings.json")["selector"]
    assert set(selectors["load_type"]["options"]) == {"modulating", "switch", "evse"}
    assert "battery_soc_scale" not in selectors
    assert "house_power_entity" in _json("strings.json")["config"]["step"]["user"]["data"]
    assert "output_unit" not in selectors


def test_component_has_no_exam_simulator_address_or_participant_topic_hardcoded():
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in COMPONENT.rglob("*")
        if path.suffix in {".py", ".json"}
    )
    assert "192.168.1.37" not in source
    assert "sim/t01" not in source


def test_live_control_is_documented_as_a_runtime_safety_gate():
    strings = _json("strings.json")
    assert "live_control" in strings["entity"]["switch"]
    assert "fail_safe_active" in strings["entity"]["binary_sensor"]


def test_generic_entity_selector_omits_none_domain_filter():
    source = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
    assert 'if domain is not None:' in source
    assert 'config["domain"] = domain' in source
    assert '_optional_marker(CONF_OUTPUT_ENTITY, values): _entity_selector()' in source
    assert 'domain=["switch", "input_boolean"]' in source


def test_coordinator_load_diagnostic_age_is_wired_to_diagnostic_not_core_model():
    source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
    controllable_block = source[source.index("load = ControllableLoad("):source.index("loads.append(load)")]
    diagnostic_block = source[source.index("diagnostics[subentry_id] = LoadDiagnostic("):source.index("return loads, diagnostics")]
    assert "actual_measurement_age_s=" not in controllable_block
    assert "actual_measurement_age_s=actual_age_s" in diagnostic_block


def test_load_reconfigure_uses_parent_entry_accessor():
    source = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
    reconfigure_block = source[source.index("async def async_step_reconfigure"):source.index("async def async_step_load_basics", source.index("async def async_step_reconfigure"))]
    review_block = source[source.index("async def async_step_load_review"):source.index("def _review_form", source.index("async def async_step_load_review"))]
    assert "self._get_reconfigure_subentry()" in reconfigure_block
    assert "self._get_entry()" in review_block
    assert "self._get_reconfigure_entry()" not in reconfigure_block


def test_autonomous_battery_does_not_block_pv_mode():
    source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
    assert "hybrid_battery_assist_enabled=" not in source
    assert "hybrid_probe_enabled=" not in source
    assert "battery_kw=" not in source[source.index("inputs = ControllerInputs("):source.index("result = run_controller(")]


def test_surplus_core_uses_grid_export_and_existing_load_not_total_pv():
    source = (COMPONENT / "controller.py").read_text(encoding="utf-8")
    assert "export = max(0.0, -inputs.grid_kw)" in source
    assert "controlled - inputs.grid_kw" in source
    assert "battery_kw" not in source


def test_manifest_classifies_power_manager_as_hub():
    manifest = _json("manifest.json")
    assert manifest["integration_type"] == "hub"


def test_manifest_declares_frontend_dependencies():
    manifest = _json("manifest.json")
    assert set(manifest["dependencies"]) == {"frontend", "http"}


def test_dashboard_card_is_packaged_and_registered():
    card = COMPONENT / "frontend" / "power-manager-card.js"
    assert card.is_file()
    source = card.read_text(encoding="utf-8")
    assert 'customElements.define("power-manager-card"' in source
    assert 'type: "power-manager-card"' in source
    assert 'config/entity_registry/list' in source


def test_backend_serves_and_loads_dashboard_card():
    source = (COMPONENT / "__init__.py").read_text(encoding="utf-8")
    assert "StaticPathConfig" in source
    assert "frontend.add_extra_js_url" in source
    assert "power-manager-card.js" in source


def test_load_target_sensor_exposes_dashboard_metadata():
    source = (COMPONENT / "sensor.py").read_text(encoding="utf-8")
    for attribute in (
        '"load_name"',
        '"priority"',
        '"min_kw"',
        '"max_kw"',
        '"peak_shaving_enabled"',
        '"surplus_enabled"',
        '"requested_kw"',
        '"actual_kw"',
    ):
        assert attribute in source


def test_dashboard_card_uses_container_responsive_layout():
    source = (COMPONENT / "frontend" / "power-manager-card.js").read_text(encoding="utf-8")
    assert "container-type:inline-size" in source
    assert "@container (min-width:560px)" in source
    assert "@container (min-width:820px)" in source


def test_v3_3_has_local_ha_brand_images_and_card_logo():
    """Native brand files must travel with the installed integration."""
    for name in ("icon.png", "icon@2x.png", "logo.png", "logo@2x.png"):
        path = COMPONENT / "brand" / name
        assert path.is_file(), f"Missing local HA brand asset: {name}"
        assert path.read_bytes().startswith(bytes((137, 80, 78, 71, 13, 10, 26, 10)))
    assert (COMPONENT / "frontend" / "power-manager-icon.png").is_file()


def test_v3_3_compatible_config_schema_import():
    source = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
    assert "import voluptuous as probatio" in source
    assert "import probatio\\n" not in source


def test_v3_3_requirements_traceability_covers_all_v08_items():
    """Never silently lose a v0.8 requirement while developing toward 4.0."""
    import re
    source = (COMPONENT.parent.parent / "docs" /
              "anforderungen_v0_8_traceability.md").read_text(encoding="utf-8")
    found = re.findall(r"^\| REQ-(\d{2}) \|", source, flags=re.MULTILINE)
    assert found == [f"{i:02d}" for i in range(1, 87)]
    assert "T01–T106" in source
    assert "Offen" in source and "Teilweise" in source
