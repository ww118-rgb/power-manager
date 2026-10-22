"""Coordinator for the Power Manager integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import isfinite
import logging
from time import monotonic
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .actuator import (
    ActuatorError,
    AppliedCommand,
    async_apply_safe_state,
    async_apply_target,
    validate_actuator,
)
from .allocator import EPSILON
from .const import (
    CONF_ACTUAL_POWER_ENTITY,
    CONF_ACTUAL_SENSOR_TIMEOUT_S,
    CONF_AVAILABILITY_ENTITY,
    CONF_DEFAULT_REQUEST_KW,
    CONF_DEMAND_MODE, DEMAND_MODE_ALWAYS, DEMAND_MODE_SENSOR,
    DEMAND_MODE_DISABLED,
    CONF_ENABLE_ENTITY,
    CONF_GRID_LIMIT_KW,
    CONF_GRID_POWER_ENTITY,
    CONF_GRID_RESERVE_KW,
    CONF_GRID_GROWTH_MARGIN_KW,
    CONF_GRID_SENSOR_TIMEOUT_S,
    CONF_INVERT_ACTUAL_POWER,
    CONF_INVERT_GRID_POWER,
    CONF_INVERT_PV_POWER,
    CONF_LOAD_NAME,
    CONF_LOAD_TYPE,
    CONF_MAX_KW,
    CONF_MIN_KW,
    CONF_MIN_OFF_TIME_S,
    CONF_MIN_ON_TIME_S,
    CONF_OUTPUT_ENTITY,
    CONF_OUTPUT_TRANSPORT,
    CONF_DIRECT_REFRESH_S,
    DEFAULT_DIRECT_REFRESH_S,
    DEFAULT_OUTPUT_TRANSPORT,
    OUTPUT_TRANSPORT_ENTITY,
    CONF_PEAK_SHAVING_ENABLED,
    CONF_PRIORITY,
    CONF_PV_POWER_ENTITY,
    CONF_HOUSE_POWER_ENTITY,
    CONF_REQUEST_ENTITY,
    CONF_SETTLING_TIME_S,
    CONF_START_MARGIN_KW,
    CONF_STOP_MARGIN_KW,
    CONF_SURPLUS_ENABLED,
    CONF_PV_SENSOR_TIMEOUT_S,
    DEFAULT_ACTUAL_SENSOR_TIMEOUT_S,
    DEFAULT_DEFAULT_REQUEST_KW,
    DEFAULT_GRID_SENSOR_TIMEOUT_S,
    DEFAULT_GRID_GROWTH_MARGIN_KW,
    DEFAULT_PV_SENSOR_TIMEOUT_S,
    DEFAULT_INVERT_ACTUAL_POWER,
    DEFAULT_MAX_KW,
    DEFAULT_MIN_KW,
    DEFAULT_MIN_OFF_TIME_S,
    DEFAULT_MIN_ON_TIME_S,
    DEFAULT_PEAK_SHAVING_ENABLED,
    DEFAULT_PRIORITY,
    DEFAULT_SETTLING_TIME_S,
    DEFAULT_START_MARGIN_KW,
    DEFAULT_STOP_MARGIN_KW,
    DEFAULT_SURPLUS_ENABLED,
    HEARTBEAT_INTERVAL_SECONDS,
    SEQUENTIAL_SWITCH_INTERVAL_SECONDS,
    LOAD_TYPE_SWITCH,
    NAME,
    REFRESH_DEBOUNCE_SECONDS,
    SUBENTRY_TYPE_LOAD,
)
from .controller import run_controller
from .load_adapter import (
    actual_kw_from_source,
    availability_from_source,
    requested_kw_from_source,
)
from .load_config import normalize_load_data
from .measurements import (
    MeasurementError,
    measurement_age_seconds,
    measurement_is_fresh,
    power_to_kw,
)
from .models import (
    ControllableLoad,
    ControllerInputs,
    ControllerResult,
    ControllerState,
    OperatingMode,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class LoadDiagnostic:
    """Runtime values for one configured controllable load."""

    subentry_id: str
    name: str
    load_type: str
    requested_kw: float
    actual_kw: float | None
    actual_measurement_age_s: float | None
    available: bool
    calculated_target_kw: float = 0.0
    commanded_target_kw: float | None = None
    output_entity: str | None = None
    enable_entity: str | None = None
    command_value: float | None = None
    command_unit: str | None = None
    command_enabled: bool | None = None
    input_error: str | None = None
    command_error: str | None = None


@dataclass(slots=True)
class PowerManagerCoordinatorData:
    """Data produced by one coordinator cycle."""

    inputs: ControllerInputs | None
    result: ControllerResult | None
    grid_power_kw: float | None
    grid_measurement_age_s: float | None
    grid_measurement_healthy: bool
    fail_safe_active: bool
    fail_safe_reason: str | None
    live_control_enabled: bool
    operating_mode: OperatingMode
    output_healthy: bool
    last_output_error: str | None
    loads: dict[str, LoadDiagnostic]


class PowerManagerCoordinator(DataUpdateCoordinator[PowerManagerCoordinatorData]):
    """Connect Home Assistant entity states to the tested controller core."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the Power Manager coordinator."""

        super().__init__(
            hass,
            _LOGGER,
            name=NAME,
            config_entry=config_entry,
            request_refresh_debouncer=Debouncer(
                hass,
                _LOGGER,
                cooldown=REFRESH_DEBOUNCE_SECONDS,
                immediate=True,
            ),
        )

        self.config_entry = config_entry
        self.controller_state = ControllerState()
        self.operating_mode = OperatingMode.NORMAL

        # Live control is intentionally never restored after a Home Assistant
        # restart or integration reload. The user must explicitly arm it again.
        self.live_control_enabled = False
        self._tracking_started = False
        self._last_output_error: str | None = None
        self._direct_last_command: dict[str, tuple[float, float, float]] = {}

    @property
    def settings(self) -> dict[str, Any]:
        """Return effective global integration settings."""

        values = dict(self.config_entry.data)
        values.update(self.config_entry.options)
        return values

    def _load_subentries(self) -> list[tuple[str, dict[str, Any]]]:
        """Return normalized configured load subentries in stable entry order."""

        result: list[tuple[str, dict[str, Any]]] = []
        for subentry_id, subentry in self.config_entry.subentries.items():
            if subentry.subentry_type != SUBENTRY_TYPE_LOAD:
                continue
            result.append((subentry_id, normalize_load_data(dict(subentry.data))))
        return result

    def _configured_entity_ids(self) -> list[str]:
        """Return all source entity ids that should trigger recalculation."""

        values = self.settings
        entity_ids: list[str | None] = [
            values.get(CONF_GRID_POWER_ENTITY),
            values.get(CONF_PV_POWER_ENTITY),
            values.get(CONF_HOUSE_POWER_ENTITY),
        ]

        for _subentry_id, load_data in self._load_subentries():
            entity_ids.extend(
                [
                    load_data.get(CONF_ACTUAL_POWER_ENTITY),
                    load_data.get(CONF_REQUEST_ENTITY),
                    load_data.get(CONF_AVAILABILITY_ENTITY),
                ]
            )

        # Preserve first occurrence and remove empty values.
        return list(dict.fromkeys(entity_id for entity_id in entity_ids if entity_id))

    @callback
    def async_start_tracking(self) -> None:
        """Start source-state tracking and the timing heartbeat."""

        if self._tracking_started:
            return

        self._tracking_started = True
        entity_ids = self._configured_entity_ids()

        if entity_ids:
            self.config_entry.async_on_unload(
                async_track_state_change_event(
                    self.hass,
                    entity_ids,
                    self._async_source_state_changed,
                )
            )

        self.config_entry.async_on_unload(
            async_track_time_interval(
                self.hass,
                self._async_heartbeat,
                timedelta(seconds=HEARTBEAT_INTERVAL_SECONDS),
            )
        )

    @callback
    def _async_source_state_changed(self, _event: Event) -> None:
        """Refresh after a relevant Home Assistant source changes."""

        self.hass.async_create_task(self.async_request_refresh())

    @callback
    def _async_heartbeat(self, _now: Any) -> None:
        """Refresh periodically for stale sensors and time-dependent core logic."""

        self.hass.async_create_task(self.async_request_refresh())

    def _get_state(self, entity_id: str, *, label: str) -> State:
        """Return a Home Assistant state or raise a measurement error."""

        state = self.hass.states.get(entity_id)
        if state is None:
            raise MeasurementError(f"{label}: Entity '{entity_id}' wurde nicht gefunden.")
        return state

    def _state_value_and_unit(
        self,
        state: State,
        *,
        label: str,
    ) -> tuple[str, str | None]:
        """Validate state availability and return value plus unit."""

        if state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            raise MeasurementError(f"{label}: Entity ist {state.state}.")

        return state.state, state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)

    def _grid_timeout_s(self) -> float:
        """Return configured grid measurement timeout."""

        try:
            timeout_s = float(
                self.settings.get(
                    CONF_GRID_SENSOR_TIMEOUT_S,
                    DEFAULT_GRID_SENSOR_TIMEOUT_S,
                )
            )
        except (TypeError, ValueError) as err:
            raise MeasurementError("Netzsensor-Timeout ist keine Zahl.") from err

        if timeout_s <= 0.0:
            raise MeasurementError("Netzsensor-Timeout muss größer als 0 sein.")
        return timeout_s

    def _aux_sensor_timeout_s(self, config_key: str, default_s: float) -> float:
        """Validate configured freshness for optional production and house meters."""
        try:
            value = float(self.settings.get(config_key, default_s))
        except (TypeError, ValueError) as err:
            raise MeasurementError(f"Ungültiger Sensor-Timeout: {config_key}") from err
        if not isfinite(value) or value <= 0.0:
            raise MeasurementError(f"Ungültiger Sensor-Timeout: {config_key}")
        return value

    def _read_grid_measurement(
        self,
    ) -> tuple[float | None, float | None, str | None]:
        """Read the critical grid value; any problem becomes fail-safe."""

        values = self.settings
        entity_id = values.get(CONF_GRID_POWER_ENTITY)
        if not entity_id:
            return None, None, "Keine Netzleistungs-Entity konfiguriert."

        age_s: float | None = None
        try:
            state = self._get_state(entity_id, label="Netzleistung")
            age_s = measurement_age_seconds(
                state.last_reported,
                datetime.now(timezone.utc),
            )
            raw_value, unit = self._state_value_and_unit(state, label="Netzleistung")
            grid_kw = power_to_kw(
                raw_value,
                unit,
                invert=bool(values.get(CONF_INVERT_GRID_POWER, False)),
                label="Netzleistung",
            )
            timeout_s = self._grid_timeout_s()
            if not measurement_is_fresh(age_s, timeout_s):
                return (
                    grid_kw,
                    age_s,
                    "Netzleistungsmesswert ist "
                    f"{age_s:.1f} s alt; Timeout ist {timeout_s:.1f} s.",
                )
            return grid_kw, age_s, None
        except MeasurementError as err:
            return None, age_s, str(err)

    def _read_optional_power_kw(
        self,
        *,
        entity_key: str,
        invert_key: str | None,
        label: str,
        require_fresh: bool = False,
        timeout_key: str = CONF_GRID_SENSOR_TIMEOUT_S,
        default_timeout_s: float = DEFAULT_GRID_SENSOR_TIMEOUT_S,
    ) -> float:
        """Read an optional global power entity in kW."""

        values = self.settings
        entity_id = values.get(entity_key)
        if not entity_id:
            return 0.0

        state = self._get_state(entity_id, label=label)
        if require_fresh:
            age_s = measurement_age_seconds(
                state.last_reported, datetime.now(timezone.utc)
            )
            timeout_s = self._aux_sensor_timeout_s(timeout_key, default_timeout_s)
            if not measurement_is_fresh(age_s, timeout_s):
                raise MeasurementError(
                    f"{label}: Messwert ist {age_s:.1f} s alt "
                    f"(Timeout {timeout_s:g} s)."
                )
        raw_value, unit = self._state_value_and_unit(state, label=label)
        return power_to_kw(
            raw_value,
            unit,
            invert=bool(values.get(invert_key, False)) if invert_key else False,
            label=label,
        )

    def _read_optional_source_state(
        self,
        entity_id: str | None,
        *,
        label: str,
    ) -> tuple[str | None, str | None]:
        """Read an optional source state; omitted source returns (None, None)."""

        if not entity_id:
            return None, None
        state = self._get_state(entity_id, label=label)
        return self._state_value_and_unit(state, label=label)

    def _build_loads(
        self,
    ) -> tuple[list[ControllableLoad], dict[str, LoadDiagnostic]]:
        """Build pure-core loads from configured Home Assistant source entities."""

        loads: list[ControllableLoad] = []
        diagnostics: dict[str, LoadDiagnostic] = {}

        for subentry_id, data in self._load_subentries():
            name = str(data[CONF_LOAD_NAME])
            load_type = str(data[CONF_LOAD_TYPE])
            max_kw = float(data.get(CONF_MAX_KW, DEFAULT_MAX_KW))
            input_errors: list[str] = []

            # Availability errors make only this load unavailable, not the whole
            # controller. That is conservative and preserves peak-shaving safety.
            available = True
            availability_entity = data.get(CONF_AVAILABILITY_ENTITY)
            if availability_entity:
                try:
                    raw_availability, _unit = self._read_optional_source_state(
                        str(availability_entity),
                        label=f"{name} Verfügbarkeit",
                    )
                    available = availability_from_source(raw_availability)
                except MeasurementError as err:
                    available = False
                    input_errors.append(str(err))

            requested_kw = 0.0
            demand_mode = data.get(
                CONF_DEMAND_MODE,
                DEMAND_MODE_SENSOR if data.get(CONF_REQUEST_ENTITY)
                else DEMAND_MODE_ALWAYS,
            )
            request_entity = (
                data.get(CONF_REQUEST_ENTITY)
                if demand_mode == DEMAND_MODE_SENSOR else None
            )
            try:
                raw_request, request_unit = self._read_optional_source_state(
                    str(request_entity) if request_entity else None,
                    label=f"{name} Anforderung",
                )
                requested_kw = requested_kw_from_source(
                    raw_request,
                    request_unit,
                    load_type=load_type,
                    max_kw=max_kw,
                    default_request_kw_value=float(
                        data.get(CONF_DEFAULT_REQUEST_KW, DEFAULT_DEFAULT_REQUEST_KW)
                    ),
                )
            except MeasurementError as err:
                # Unknown demand must never cause a load to be turned on.
                requested_kw = 0.0
                input_errors.append(str(err))
            if demand_mode == DEMAND_MODE_DISABLED:
                requested_kw = 0.0
            elif demand_mode == DEMAND_MODE_SENSOR and not request_entity:
                requested_kw = 0.0
                input_errors.append("Bedarfssensor fehlt.")

            actual_kw: float | None = None
            actual_age_s: float | None = None
            actual_entity = data.get(CONF_ACTUAL_POWER_ENTITY)
            if actual_entity:
                try:
                    actual_state = self._get_state(
                        str(actual_entity),
                        label=f"{name} Istleistung",
                    )
                    actual_age_s = measurement_age_seconds(
                        actual_state.last_reported,
                        datetime.now(timezone.utc),
                    )
                    actual_timeout_s = float(
                        data.get(
                            CONF_ACTUAL_SENSOR_TIMEOUT_S,
                            DEFAULT_ACTUAL_SENSOR_TIMEOUT_S,
                        )
                    )
                    if not measurement_is_fresh(actual_age_s, actual_timeout_s):
                        raise MeasurementError(
                            f"{name} Istleistung: Messwert ist {actual_age_s:.1f} s alt; "
                            f"Timeout ist {actual_timeout_s:.1f} s."
                        )

                    raw_actual, actual_unit = self._state_value_and_unit(
                        actual_state,
                        label=f"{name} Istleistung",
                    )
                    actual_kw = actual_kw_from_source(
                        raw_actual,
                        actual_unit,
                        invert=bool(
                            data.get(
                                CONF_INVERT_ACTUAL_POWER,
                                DEFAULT_INVERT_ACTUAL_POWER,
                            )
                        ),
                    )
                except (MeasurementError, TypeError, ValueError) as err:
                    # A stale/invalid actual value is less safe than the core's
                    # explicit previous-target estimate, so never keep using it.
                    actual_kw = None
                    input_errors.append(str(err))

            load = ControllableLoad(
                name=name,
                priority=int(data.get(CONF_PRIORITY, DEFAULT_PRIORITY)),
                requested_kw=requested_kw,
                min_kw=float(data.get(CONF_MIN_KW, DEFAULT_MIN_KW)),
                max_kw=max_kw,
                actual_kw=actual_kw,
                available=available,
                can_modulate=(load_type != LOAD_TYPE_SWITCH),
                can_shutdown=True,
                peak_shaving_enabled=bool(
                    data.get(CONF_PEAK_SHAVING_ENABLED, DEFAULT_PEAK_SHAVING_ENABLED)
                ),
                surplus_enabled=bool(
                    data.get(CONF_SURPLUS_ENABLED, DEFAULT_SURPLUS_ENABLED)
                ),
                start_margin_kw=float(
                    data.get(CONF_START_MARGIN_KW, DEFAULT_START_MARGIN_KW)
                ),
                stop_margin_kw=float(
                    data.get(CONF_STOP_MARGIN_KW, DEFAULT_STOP_MARGIN_KW)
                ),
                min_on_time_s=float(
                    data.get(CONF_MIN_ON_TIME_S, DEFAULT_MIN_ON_TIME_S)
                ),
                min_off_time_s=float(
                    data.get(CONF_MIN_OFF_TIME_S, DEFAULT_MIN_OFF_TIME_S)
                ),
                settling_time_s=float(
                    data.get(CONF_SETTLING_TIME_S, DEFAULT_SETTLING_TIME_S)
                ),
            )
            loads.append(load)

            diagnostics[subentry_id] = LoadDiagnostic(
                subentry_id=subentry_id,
                name=name,
                load_type=load_type,
                requested_kw=requested_kw,
                actual_kw=actual_kw,
                actual_measurement_age_s=actual_age_s,
                available=available,
                output_entity=(
                    str(data[CONF_OUTPUT_ENTITY]) if data.get(CONF_OUTPUT_ENTITY) else None
                ),
                enable_entity=(
                    str(data[CONF_ENABLE_ENTITY]) if data.get(CONF_ENABLE_ENTITY) else None
                ),
                input_error=" | ".join(input_errors) if input_errors else None,
            )

        return loads, diagnostics

    def _set_calculated_targets(
        self,
        diagnostics: dict[str, LoadDiagnostic],
        result: ControllerResult,
    ) -> None:
        """Copy pure-core target values into subentry diagnostics."""

        for diagnostic in diagnostics.values():
            diagnostic.calculated_target_kw = result.targets_kw.get(diagnostic.name, 0.0)

    async def _async_apply_safe_outputs(
        self,
        diagnostics: dict[str, LoadDiagnostic],
    ) -> str | None:
        """Best-effort safe-state command for every configured load."""

        errors: list[str] = []
        data_by_id = dict(self._load_subentries())

        for subentry_id, diagnostic in diagnostics.items():
            load_data = data_by_id.get(subentry_id)
            if load_data is None:
                continue
            if (
                load_data.get(CONF_OUTPUT_TRANSPORT, DEFAULT_OUTPUT_TRANSPORT)
                == OUTPUT_TRANSPORT_ENTITY
                and not load_data.get(CONF_OUTPUT_ENTITY)
            ):
                continue

            try:
                command = await async_apply_safe_state(self.hass, load_data)
                self._direct_last_command.pop(subentry_id, None)
                self._apply_command_diagnostic(diagnostic, command, commanded_target_kw=0.0)
            except (ActuatorError, HomeAssistantError, ValueError) as err:
                diagnostic.command_error = str(err)
                errors.append(f"{diagnostic.name}: {err}")

        return " | ".join(errors) if errors else None

    def _apply_command_diagnostic(
        self,
        diagnostic: LoadDiagnostic,
        command: AppliedCommand,
        *,
        commanded_target_kw: float,
    ) -> None:
        """Store output command information in one diagnostic record."""

        diagnostic.commanded_target_kw = (
            command.effective_target_kw
            if command.effective_target_kw is not None else commanded_target_kw
        )
        diagnostic.command_value = command.numeric_value
        diagnostic.command_unit = command.numeric_unit
        diagnostic.command_enabled = command.enabled
        diagnostic.command_error = None

    async def _async_apply_targets(
        self,
        diagnostics: dict[str, LoadDiagnostic],
    ) -> str | None:
        """Write calculated targets to configured HA actuators."""

        errors: list[str] = []
        data_by_id = dict(self._load_subentries())

        # Execute shedding/reductions before increases. The pure controller
        # already respects PMAX in its final target vector; this ordering also
        # avoids intentionally issuing an increase before a compensating
        # reduction in the same control cycle. Physical actuator/network lag
        # can still exist, which is why the grid meter remains the source of
        # truth and settling times are configurable.
        def command_order(item: tuple[str, LoadDiagnostic]) -> tuple[int, float]:
            _subentry_id, diagnostic = item
            previous_kw = self.controller_state.last_targets_kw.get(
                diagnostic.name, 0.0
            )
            delta_kw = diagnostic.calculated_target_kw - previous_kw
            if delta_kw < -EPSILON:
                return (0, delta_kw)  # largest reduction first
            if delta_kw > EPSILON:
                return (2, delta_kw)  # increases last
            return (1, 0.0)

        for subentry_id, diagnostic in sorted(
            diagnostics.items(), key=command_order
        ):
            load_data = data_by_id.get(subentry_id)
            if load_data is None:
                continue

            if (
                load_data.get(CONF_OUTPUT_TRANSPORT, DEFAULT_OUTPUT_TRANSPORT)
                == OUTPUT_TRANSPORT_ENTITY
                and not load_data.get(CONF_OUTPUT_ENTITY)
            ):
                error = "Kein Ausgang konfiguriert."
                diagnostic.command_error = error
                errors.append(f"{diagnostic.name}: {error}")
                continue

            try:
                previous_kw = self.controller_state.last_targets_kw.get(
                    diagnostic.name, 0.0,
                )
                transport = load_data.get(CONF_OUTPUT_TRANSPORT, DEFAULT_OUTPUT_TRANSPORT)
                if transport != OUTPUT_TRANSPORT_ENTITY:
                    previous_direct = self._direct_last_command.get(subentry_id)
                    requested_kw = diagnostic.calculated_target_kw
                    refresh_s = float(load_data.get(
                        CONF_DIRECT_REFRESH_S, DEFAULT_DIRECT_REFRESH_S,
                    ))
                    if (
                        previous_direct is not None
                        and abs(previous_direct[0] - requested_kw) <= EPSILON
                        and monotonic() - previous_direct[1] < refresh_s
                    ):
                        diagnostic.commanded_target_kw = previous_direct[2]
                        continue
                command = await async_apply_target(
                    self.hass,
                    load_data,
                    diagnostic.calculated_target_kw,
                )
                if transport != OUTPUT_TRANSPORT_ENTITY:
                    self._direct_last_command[subentry_id] = (
                        diagnostic.calculated_target_kw,
                        monotonic(),
                        command.effective_target_kw
                        if command.effective_target_kw is not None
                        else diagnostic.calculated_target_kw,
                    )
                self._apply_command_diagnostic(
                    diagnostic,
                    command,
                    commanded_target_kw=diagnostic.calculated_target_kw,
                )
            except (ActuatorError, HomeAssistantError, ValueError) as err:
                diagnostic.command_error = str(err)
                errors.append(f"{diagnostic.name}: {err}")

        return " | ".join(errors) if errors else None

    async def _async_fail_safe_data(
        self,
        *,
        reason: str,
        grid_kw: float | None,
        age_s: float | None,
        diagnostics: dict[str, LoadDiagnostic],
        inputs: ControllerInputs | None = None,
        result: ControllerResult | None = None,
        grid_measurement_healthy: bool = False,
    ) -> PowerManagerCoordinatorData:
        """Create fail-safe state and, when armed, command all loads safe."""

        _LOGGER.warning("Power Manager Fail-Safe aktiv: %s", reason)

        output_error: str | None = None
        was_live = self.live_control_enabled
        if was_live:
            output_error = await self._async_apply_safe_outputs(diagnostics)

            # A fail-safe changes the physical loads to their safe state. Any
            # previously stored target estimate is no longer a valid proxy for
            # an unknown actual-power measurement. Disarm and clear runtime
            # state so recovery can never reuse a stale pre-fail-safe target.
            self.live_control_enabled = False
            self.controller_state = ControllerState()
            self._direct_last_command.clear()

        combined_reason = reason
        if output_error:
            combined_reason = f"{reason} | Sichere Ausgänge teilweise fehlgeschlagen: {output_error}"

        self._last_output_error = output_error

        return PowerManagerCoordinatorData(
            inputs=inputs,
            result=result,
            grid_power_kw=grid_kw,
            grid_measurement_age_s=age_s,
            grid_measurement_healthy=grid_measurement_healthy,
            fail_safe_active=True,
            fail_safe_reason=combined_reason,
            live_control_enabled=self.live_control_enabled,
            operating_mode=self.operating_mode,
            output_healthy=output_error is None,
            last_output_error=output_error,
            loads=diagnostics,
        )

    async def _async_update_data(self) -> PowerManagerCoordinatorData:
        """Read HA values, execute the pure core and optionally command outputs."""

        try:
            loads, diagnostics = self._build_loads()
        except (KeyError, TypeError, ValueError) as err:
            return await self._async_fail_safe_data(
                reason=f"Verbraucherkonfiguration ungültig: {err}",
                grid_kw=None,
                age_s=None,
                diagnostics={},
            )

        grid_kw, grid_age_s, grid_error = self._read_grid_measurement()
        if grid_error is not None:
            return await self._async_fail_safe_data(
                reason=grid_error,
                grid_kw=grid_kw,
                age_s=grid_age_s,
                diagnostics=diagnostics,
            )

        assert grid_kw is not None
        values = self.settings

        try:
            pv_kw = self._read_optional_power_kw(
                entity_key=CONF_PV_POWER_ENTITY,
                invert_key=CONF_INVERT_PV_POWER,
                label="PV-Leistung",
                require_fresh=(self.operating_mode == OperatingMode.SURPLUS),
                timeout_key=CONF_PV_SENSOR_TIMEOUT_S,
                default_timeout_s=DEFAULT_PV_SENSOR_TIMEOUT_S,
            )
        except MeasurementError as err:
            _LOGGER.warning("PV-Messwert ungültig; verwende 0 kW: %s", err)
            pv_kw = 0.0

        # A separate meter of NON-controllable house consumption allows
        # PV priority even when zero power is exported. Missing/unavailable
        # house measurements fall back to confirmed grid-export allocation.
        house_kw: float | None = None
        if values.get(CONF_HOUSE_POWER_ENTITY):
            try:
                measured_house = self._read_optional_power_kw(
                    entity_key=CONF_HOUSE_POWER_ENTITY,
                    invert_key=None,
                    label="Hausgrundverbrauch",
                    require_fresh=(self.operating_mode == OperatingMode.SURPLUS),
                    timeout_key=CONF_PV_SENSOR_TIMEOUT_S,
                    default_timeout_s=DEFAULT_PV_SENSOR_TIMEOUT_S,
                )
                if measured_house < 0:
                    raise MeasurementError("Hausgrundverbrauch darf nicht negativ sein.")
                house_kw = measured_house
            except MeasurementError as err:
                _LOGGER.warning("Hausgrundverbrauch ungültig; PV-Regelung nur über Netzeinspeisung: %s", err)

        # Monotonic timestamp corresponding to the last actual grid report.
        # A 5 s timer alone must never authorize a second load based on a
        # pre-switch grid measurement.
        cycle_now_s = monotonic()
        grid_sample_s = (
            cycle_now_s - max(0.0, grid_age_s)
            if grid_age_s is not None else None
        )
        try:
            inputs = ControllerInputs(
                grid_kw=grid_kw,
                grid_limit_kw=float(values[CONF_GRID_LIMIT_KW]),
                grid_reserve_kw=float(values.get(CONF_GRID_RESERVE_KW, 0.0)),
                grid_growth_margin_kw=float(values.get(
                    CONF_GRID_GROWTH_MARGIN_KW, DEFAULT_GRID_GROWTH_MARGIN_KW,
                )),
                pv_kw=pv_kw,
                house_kw=house_kw,
                mode=self.operating_mode,
                now_s=cycle_now_s,
                switch_interval_s=SEQUENTIAL_SWITCH_INTERVAL_SECONDS,
                grid_sample_s=grid_sample_s,
            )

            result = run_controller(
                inputs=inputs,
                loads=loads,
                state=self.controller_state,
            )
        except (KeyError, TypeError, ValueError) as err:
            return await self._async_fail_safe_data(
                reason=f"Reglerkonfiguration ungültig: {err}",
                grid_kw=grid_kw,
                age_s=grid_age_s,
                diagnostics=diagnostics,
                grid_measurement_healthy=True,
            )

        self._set_calculated_targets(diagnostics, result)

        output_error: str | None = None
        if self.live_control_enabled:
            output_error = await self._async_apply_targets(diagnostics)
            if output_error:
                # If even one actuator did not accept its target, the controller
                # can no longer claim physical PMAX control. Shed everything to
                # the configured safe state immediately.
                safe_error = await self._async_apply_safe_outputs(diagnostics)
                reason = f"Ausgangsfehler: {output_error}"
                if safe_error:
                    reason += f" | Sichere Ausgänge teilweise fehlgeschlagen: {safe_error}"
                self._last_output_error = output_error
                # An actuator mismatch means the physical output path is no
                # longer trustworthy. Disarm live control after the best-effort
                # safe command so automatic cycles cannot repeatedly alternate
                # between a failing target and the safe state. The safe command
                # also invalidates any previous-target estimate used for loads
                # without actual-power feedback.
                self.live_control_enabled = False
                self.controller_state = ControllerState()
                self._direct_last_command.clear()
                return PowerManagerCoordinatorData(
                    inputs=inputs,
                    result=result,
                    grid_power_kw=grid_kw,
                    grid_measurement_age_s=grid_age_s,
                    grid_measurement_healthy=True,
                    fail_safe_active=True,
                    fail_safe_reason=reason,
                    live_control_enabled=False,
                    operating_mode=self.operating_mode,
                    output_healthy=False,
                    last_output_error=output_error,
                    loads=diagnostics,
                )

        # For devices lacking an Istleistung sensor, use the PHYSICAL command
        # accepted by the output adapter (after W/kW/A step rounding) as the
        # next-cycle estimate. Keep it distinct from the calculated request.
        # A command is not an actual-power measurement; only the grid meter
        # confirms the net effect in the following cycles.
        if self.live_control_enabled:
            for diagnostic in diagnostics.values():
                actual_command_kw = diagnostic.commanded_target_kw
                if actual_command_kw is None:
                    continue
                result.state.last_targets_kw[diagnostic.name] = actual_command_kw
                runtime = result.state.load_states.get(diagnostic.name)
                if runtime is not None:
                    physical_on = actual_command_kw > EPSILON
                    if runtime.is_on != physical_on:
                        runtime.last_switch_s = inputs.now_s
                    runtime.is_on = physical_on
                    runtime.last_target_kw = actual_command_kw

        # Controller state advances only after all measurements and calculations
        # were valid. In live mode it also requires successful output commands.
        self.controller_state = result.state
        self._last_output_error = None

        return PowerManagerCoordinatorData(
            inputs=inputs,
            result=result,
            grid_power_kw=grid_kw,
            grid_measurement_age_s=grid_age_s,
            grid_measurement_healthy=True,
            fail_safe_active=False,
            fail_safe_reason=None,
            live_control_enabled=self.live_control_enabled,
            operating_mode=self.operating_mode,
            output_healthy=True,
            last_output_error=None,
            loads=diagnostics,
        )

    async def async_enable_live_control(self) -> None:
        """Validate every actuator, arm live control and immediately recalculate."""

        data = self.data
        if data is None or not data.grid_measurement_healthy or data.fail_safe_active:
            raise HomeAssistantError(
                "Live-Regelung kann nur mit gültiger Netzmessung und ohne Fail-Safe aktiviert werden."
            )

        try:
            load_subentries = self._load_subentries()
        except (KeyError, TypeError, ValueError, OverflowError) as err:
            raise HomeAssistantError(
                f"Verbraucherkonfiguration ist ungültig: {err}"
            ) from err

        if not load_subentries:
            raise HomeAssistantError("Es ist noch kein regelbarer Verbraucher konfiguriert.")

        errors: list[str] = []
        for subentry_id, load_data in load_subentries:
            # Actual-power sensors are optional. Grid measurement is mandatory.
            # Actuator validation still protects all configured outputs.
            try:
                validate_actuator(self.hass, load_data)
            except ActuatorError as err:
                errors.append(f"{name}: {err}")

        if errors:
            raise HomeAssistantError("Live-Regelung nicht freigegeben: " + " | ".join(errors))

        # Dry-run cycles may have accumulated previous targets although no
        # physical commands were sent. Never use those values as estimates on
        # the first live cycle; start from a clean controller state.
        self.controller_state = ControllerState()
        self._direct_last_command.clear()
        self.live_control_enabled = True
        await self.async_refresh()

    async def async_disable_live_control(self) -> None:
        """Command safe outputs once and disarm live control."""

        if self.live_control_enabled:
            try:
                _loads, diagnostics = self._build_loads()
                error = await self._async_apply_safe_outputs(diagnostics)
                if error:
                    _LOGGER.error(
                        "Fehler beim sicheren Abschalten der Live-Regelung: %s",
                        error,
                    )
            except Exception:  # pragma: no cover - last-resort shutdown protection
                _LOGGER.exception("Unerwarteter Fehler beim sicheren Abschalten")

        self.live_control_enabled = False
        # Safe/off outputs no longer match the previous live target vector.
        # Clear state before entering dry-run so unknown actual-power values are
        # never inferred from commands that were deliberately withdrawn.
        self.controller_state = ControllerState()
        self._direct_last_command.clear()
        await self.async_refresh()

    async def async_set_operating_mode(self, mode: OperatingMode) -> None:
        """Change runtime operating mode and recalculate immediately."""

        self.operating_mode = mode
        await self.async_refresh()

    async def async_shutdown(self) -> None:
        """Best-effort safe shutdown during a controlled integration unload."""

        if not self.live_control_enabled:
            return

        try:
            _loads, diagnostics = self._build_loads()
            error = await self._async_apply_safe_outputs(diagnostics)
            if error:
                _LOGGER.error("Sicheres Entladen teilweise fehlgeschlagen: %s", error)
        except Exception:  # pragma: no cover - shutdown must never block unload
            _LOGGER.exception("Unerwarteter Fehler beim sicheren Integration-Unload")
        finally:
            self.live_control_enabled = False
