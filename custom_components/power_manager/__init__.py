"""Power Manager integration for Home Assistant."""

from __future__ import annotations

from contextlib import suppress
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from .coordinator import PowerManagerCoordinator

    type PowerManagerConfigEntry = ConfigEntry[PowerManagerCoordinator]

_LOGGER = logging.getLogger(__name__)

_FRONTEND_URL_BASE = "/power_manager_frontend"
_FRONTEND_STATIC_REGISTERED = "frontend_static_registered"


async def _async_update_listener(
    hass: HomeAssistant,
    entry: PowerManagerConfigEntry,
) -> None:
    """Reload after global options or load subentries change."""

    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PowerManagerConfigEntry,
) -> bool:
    """Set up Power Manager from a config entry."""

    from homeassistant.components import frontend
    from homeassistant.components.http import StaticPathConfig
    from homeassistant.const import Platform

    from .const import DOMAIN, VERSION
    from .coordinator import PowerManagerCoordinator

    domain_data = hass.data.setdefault(DOMAIN, {})
    frontend_dir = Path(__file__).parent / "frontend"
    module_url = f"{_FRONTEND_URL_BASE}/power-manager-card.js?v={VERSION}"

    if not domain_data.get(_FRONTEND_STATIC_REGISTERED):
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    _FRONTEND_URL_BASE,
                    str(frontend_dir),
                    cache_headers=True,
                )
            ]
        )
        domain_data[_FRONTEND_STATIC_REGISTERED] = True

    frontend.add_extra_js_url(hass, module_url)

    coordinator = PowerManagerCoordinator(hass=hass, config_entry=entry)

    # Load the integration even if a critical source is currently unavailable.
    # The coordinator exposes that condition as fail-safe instead of preventing
    # the user from opening the integration and fixing its configuration.
    await coordinator.async_refresh()
    entry.runtime_data = coordinator

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(
        entry,
        [
            Platform.SENSOR,
            Platform.BINARY_SENSOR,
            Platform.SELECT,
            Platform.SWITCH,
        ],
    )

    coordinator.async_start_tracking()
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: PowerManagerConfigEntry,
) -> bool:
    """Unload Power Manager and best-effort put live outputs into safe state."""

    from homeassistant.components import frontend
    from homeassistant.const import Platform

    from .const import VERSION

    coordinator = entry.runtime_data
    await coordinator.async_shutdown()

    with suppress(KeyError):
        frontend.remove_extra_js_url(
            hass,
            f"{_FRONTEND_URL_BASE}/power-manager-card.js?v={VERSION}",
        )

    return await hass.config_entries.async_unload_platforms(
        entry,
        [
            Platform.SENSOR,
            Platform.BINARY_SENSOR,
            Platform.SELECT,
            Platform.SWITCH,
        ],
    )


async def async_migrate_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Upgrade to the single V4.0 policy without discarding device settings.

    Old device-storage fields are removed; consumer and device settings survive.
    """
    if entry.version > 6:
        _LOGGER.error(
            "Cannot migrate Power Manager configuration from version %s",
            entry.version,
        )
        return False
    if entry.version == 6:
        return True

    retired = {
        "surplus_min_battery_soc",
        "battery_resume_hysteresis_soc",
        "hybrid_probe_step_kw",
        "hybrid_probe_settle_s",
        "hybrid_probe_retry_s",
        "hybrid_grid_tolerance_kw",
        "grid_recovery_hold_s",
        "feedback_tolerance_kw",
        "battery_power_entity",
        "battery_soc_entity",
        "battery_soc_scale",
        "battery_sensor_timeout_s",
        "battery_soc_sensor_timeout_s",
        "invert_battery_power",
    }
    new_data = {key: val for key, val in entry.data.items() if key not in retired}
    new_options = {key: val for key, val in entry.options.items() if key not in retired}
    hass.config_entries.async_update_entry(
        entry,
        data=new_data,
        options=new_options,
        version=6,
        minor_version=0,
    )
    _LOGGER.info("Migrated Power Manager to storage-free configuration schema v6")
    return True
