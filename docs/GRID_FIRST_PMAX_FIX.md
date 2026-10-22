# Grid-first PMAX regulation – corrective test branch

Status: **development / simulator validation pending**, based on V3.3.3. This is not a released or field-certified build.

## Problem captured on 22 October 2026

Observed on a 140-kW test site: grid +129.56 kW, autonomous battery discharge +10.42 kW, heat pump 9.60 kW, PV 19.58 kW. The previous NORMAL controller added active battery discharge to the projected grid import, obtaining ~139.98 kW before the plant reached the physical net limit. With unconfigured/zero hysteresis and settling, the setpoint could cycle between increasing, reducing and switching off.

The site has no guarantee of individual actual-power sensors for every controllable device. **The site net power meter is mandatory, and individual device feedback is optional.**

## Changed decision: NORMAL is based on measured grid import

For NORMAL, `base_kw = measured_grid_kw - (measured_controlled_kw + estimated_controlled_kw)`; this no longer adds positive battery discharge as an *unconditional* deduction of usable grid headroom. The battery sensor can still be present for other modes. The configured `PMAX - grid_reserve_kw` remains the operating limit.

The adapter estimates a consumer's current power from its previous target if no fresh, valid actual-power measurement is available. **A previous target is never proof that a device responded.** Thus positive changes must also fit the *current observed grid headroom* before they are sent. An expected reduction of another consumer is never spent in the same controller cycle.

A global settling hold starts after each NORMAL target change (increase OR decrease), and new positive load is blocked until it expires. Net reductions are never delayed. The default values for existing installations without new settings are:
- `grid_growth_margin_kw = 0.3` kW (noise/uncertainty margin **only for new increases**, not part of PMAX itself)
- `grid_recovery_hold_s = 15` s

Both settings are editable from advanced global settings. They are **site-tunable defaults, not 140-kW-specific constants**. Change them based on network meter resolution, real actuator settling, and plant size.

Device actual-power measurements remain useful: fresh values improve the baseline estimate and can independently confirm reductions. A missing or stale optional sensor must not prevent enabling live mode or trigger fail-safe by itself. The mandatory grid measurement must remain healthy; existing actuator-output validation and fail-safe still apply.

## Limitations – do not describe as a hard physical guarantee

If the autonomous battery suddenly stops discharging (e.g., at +10.42 kW), **physical grid import can instantly rise by that amount before the software receives a new measurement.** No software-only controller using this strategy can guarantee a hard 140-kW limit against that event. For an absolute hard bound, use hardware protections, an adequately configured independent grid reserve, and/or a battery/inverter limit compatible with the site. A stale/invalid grid measurement continues to disable live mode.

No guarantee is made about unmeasured or unresponsive device actuation. PMAX reduction on new measurements is required, but meters, inverter and actuators have finite delays. When the actuation cannot be trusted, use a hardware safety layer.

## Simulator test checklist

1. Back up the HA instance, keep Live OFF. Run tests with no actual-power entity on at least one heat pump or heater.
2. Verify with NORMAL, net import 129.56 kW, battery discharge 10.42 kW, previous 9.6-kW heat-pump target: new budget/target reflects **current net headroom**, not `grid+battery`.
3. Confirm that new additional commands never exceed observed grid room minus the configurable margin, even when a consumer has been told to reduce but no net reduction has yet occurred.
4. Apply +/−0.05 kW grid-meter jitter around steady conditions for several hundred cycles. No repeated ON/OFF cycling.
5. Simulate grid import rising above configured PMAX while a settling hold is in effect; require an immediate reduction.
6. Simulate sudden loss of battery discharge; log the transient net overrun, next measurement and the commands used to shed the flexible loads.
7. Run with no SOC sensor, no battery sensor and no device actual-power sensors in NORMAL. Grid meter freshness and actuator configuration remain mandatory.
8. Test EVSE technical minima/phase-current limits and safe off codes; ensure all 3.3.3 output-unit tests remain successful.
9. Repeat with a slow/delayed actuator and different PMAX values (not just 140 kW). Capture net, calculated target, actual optional load power, physically written device command, `grid_growth_block_until_s`, and control mode.

**Do not merge this branch into main or ship as an unconditional production release until simulation and physical acceptance are completed.**
