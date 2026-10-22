# Power Manager 4.0.0-rc.3 – PV-Überschuss bei 0 kW Netzeinspeisung

**Simulator-Vorabversion, nicht als produktiver Netzanschlussschutz freigegeben.**

## Korrektur

Auslöser: Simulation mit PV 38,60 kW, Hausgrundverbrauch 0,05 kW, Netzaustausch 0,00 kW. Bisher blieb PV-Budget 0 kW, weil keine echte Einspeisung ins Netz sichtbar war.

Ein neuer **optionaler Hausgrundverbrauchssensor** meldet den eigenständigen **nicht-regelbaren** Hausverbrauch. Dieser Sensor darf **keine** vom Power Manager bereits gesteuerten Verbraucher enthalten. Bei frischen Messwerten:

`PV-Budget = max(0, PV-Erzeugungsleistung − Hausgrundverbrauch)`

Im Beispiel ergibt sich ein PV-Budget von **38,55 kW**. Verbraucher werden **gemäß der RC2-5-Sekunden-Regel nacheinander** zugeschaltet, nie alle gleichzeitig. Ein weiterer Start verlangt mindestens 5 Sekunden und eine *neue Netzsensor-Rückmeldung* seit dem letzten Befehl.

Ohne diesen Haus-Sensor bleibt die **konservative bisherige Regelung**: Zusätzliche Leistung nur aus echt gemessener Netzeinspeisung. Es wird nie ohne Messung Hausverbrauch geraten.

**Sicherheitsausnahme:** Entsteht tatsächlich Netzbezug, wird das PV-Budget anhand des Netzbezugs sofort verringert und die notwendige Reduzierung umgeht die 5-Sekunden-Wartezeit. Frischer Netzsensor bleibt Pflicht; eine eigenständige Stromflussänderung kann vor dem nächsten Messwert nicht zuverlässig vorausgesehen werden.

## Bereinigung

- Alle Batterie-, SOC- und Hybridabfragen aus dem aktiven Regelungs-, HA-Koordinator-, Einrichtungs-, Sensor- und Dashboard-Code entfernt.
- Lediglich die alten *Schlüsselnamen* bleiben in der **Konfigurationsmigration auf Schema v6**, um vorhandene Speicher-Parameter zu entfernen, ohne Verbraucher-/Aktorprofile zu verlieren.
- Einheitliche PV-/Hausverbrauch-Anzeige statt alter Hybrid-/SOC-Kacheln.
- Automatische Regressionen für Originalfall, stale Haus-Messung, PV kleiner Hauslast, Netzimport-Sicherheitsreduktion und 5-Sekunden-Sequenz.

## Installation: nur Simulator

1. HA-Konfiguration sichern und Live-Regelung **AUS**.
2. HACS → Power Manager → erneut herunterladen → Vorabversion `v4.0.0-rc.3`; Home Assistant neu starten.
3. In der Power-Manager-Einrichtung **Netzsensor**, **PV-Leistungssensor** sowie unter den Grunddaten optional **Hausgrundverbrauch** auswählen. Erfasst werden nur nicht steuerbare Hausverbraucher.
4. Trockenlauf, danach Simulator-Live: PV 38,60, Haus 0,05, Netz 0,00; zuerst Priorität 1, frühestens nach 5 Sekunden und neuer Netzmessung der nächste Verbraucher.
5. PV-Regler bei positivem Netzbezug auf unverzügliche Leistungsreduzierung prüfen. Mit fehlendem Hausmesswert muss die konservative Einspeisungsregel greifen.

**Offene Abnahme:** Langzeit-Simulatorlauf, verifizierte korrekte Zusammensetzung des Hausgrundverbrauchssensors, keine unerklärten Stellbefehle. `main`, V3.1.1 und frühere RC-Tags bleiben unverändert.

Änderungen: [PR #12](https://github.com/ww118-rgb/power-manager/pull/12).
