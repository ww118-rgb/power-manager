# Architekturentscheidung 4.0

## Eine Regelung statt paralleler Strategien

1. **Inputs:** Netzmessung als Pflicht, PV-Erzeugung für Überschuss, optionaler individueller Verbraucher-Istwert.
2. **Bilanz:** `base = grid - controlled`. Wenn kein Istwert existiert, steht `controlled` für die Schätzung aus dem letzten tatsächlich gesendeten Stellbefehl, nicht für eine Garantie.
3. **Budget:** NORMAL `limit - base`; PV `max(0, controlled - grid)` nur bei aktiver PV, auf PMAX begrenzt. Für zusätzliche Last im PV-Modus muss echter Netzexport vorhanden sein.
4. **Allocator:** seit 3.1.1 unveränderte technische Min/Max-Zuteilung und Priorisierung, gleiche Priorität teilt Leistung fair. Im PV-Modus wird Priorität für die Zuteilung vereinheitlicht.
5. **Admission:** einmalige Sicherheitsprüfung gegen aktuellen freien Netzspielraum bzw. Netzexport. Noch nicht gemessene Reduktionen eines Gerätes werden nicht an ein anderes vergeben. Gleiche aktive Verbraucher teilen die genehmigte Zusatzleistung möglichst gleichmäßig.
6. **Output:** separates HA-Geräteprofil, sichere AUS-Codes, W/kW/A-Mapping und abwärts gerichtete Schrittweiten. Diagnose unterscheidet Sollwert, physikalisch gesendeten Befehl und optionalen Istwert.

## Was ausdrücklich NICHT zum Controller gehört

- Batterie-/SOC-Gates, Hybridunterstützung, Inverter-Probing.
- Ein globaler 15-Sekunden-Wiederanlauf-Timer oder eine generelle Pflicht zur Istleistung jedes Verbrauchers.
- Release-spezifische unterschiedliche Rechenwege; alle Betriebsarten durchlaufen denselben Controller.

## Eine überprüfbare Quelle

Canonical HACS-Code: `custom_components/power_manager/{controller,allocator,models}.py`. Für reine Python-Tests ohne installierten Home Assistant stehen die drei absichtlich synchron gehaltenen Test-Spiegeldateien im Repository-Wurzelverzeichnis. Ein Paritätstest kontrolliert Inhalt und Ergebnis. Die Geräteadapter und die Oberfläche sind **nicht** Teil dieser reinen Berechnungslogik.

## Sicherheitsgrenzen

Netzsensorzyklen, Geräteantwort und autonome Batterieregelung haben reale Verzögerungen. Softwarebasierte Begrenzung ist kein nullzeitiger Schutz gegen harte Netzanschlussüberlastung. Für harte PMAX-Garantien ist eine unabhängige Netz-/Anlagensicherung notwendig.
