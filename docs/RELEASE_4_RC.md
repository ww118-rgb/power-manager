# Power Manager 4.0.0-rc.1 – konsolidierte Simulator-Vorabversion

**Nicht produktiv abgenommen.** Diese Version dient ausschließlich dem kontrollierten Simulator-Test. Aktueller Code aus dem konsolidierten V4-Zweig, Gegenüberstellung mit dem stabilen 3.1.1-Grundalgorithmus und moderner Einrichtung/Geräteausgabe.

## Änderungen
- Nur **NORMAL/Peakshaving** und **PV-Überschuss** als aktive Regelstrategien.
- Bewährter 3.1.1-Allocator: Prioritäten, Min/Max, optionale Geräte-Schutzzeiten.
- Netzsensor als Pflicht; Istleistung jedes Verbrauchers optional.
- PMAX-Budget aus Netzwert und bisher geregelter Last, keine globale Freigabesperre.
- PV-Budget nur aus echter Netzeinspeisung plus bereits laufenden PV-Verbrauchern, faire Lastgruppen und keine doppelt verplante Lastreduktion.
- Batterie vollständig autonom; optional nur SOC und Leistung als **Diagnose**.
- Verbesserte W/kW/A-Ausgabe, sichere Pausecodes und Home-Assistant-Assistent aus 3.3.x erhalten.
- Bereinigte Konfiguration (Migration auf Schema V5), Dateien, Doku und GitHub-Workflows.

## Testinstallation
Home Assistant sichern. **Nur auf einer getrennten Simulatorinstanz** über HACS unter Vorabversion `v4.0.0-rc.1` herunterladen und HA neu starten. Die Live-Regelung bleibt bis zur bewussten Aktivierung aus. Zuerst Dry-Run prüfen; dann die Szenarien in [SIMULATOR_TEST.md](https://github.com/ww118-rgb/power-manager/blob/refactor/v4.0.0-unified/SIMULATOR_TEST.md).

## Wichtige Grenzen
Kein Software-Regler auf Basis von zeitversetzten Netz-/Aktordaten kann ein kurzzeitiges physisches Überziehen von PMAX durch plötzliche autonome Batterieänderung oder Hauslastsprünge absolut verhindern. Ein unabhängiger, korrekt parametrierter Anlagenschutz ist Voraussetzung, falls PMAX **hart** garantiert sein muss. Für bereits laufende Last ist ohne Batteriemessung keine sichere PV-Herkunftszuordnung möglich.

**Status:** automatische CI-/HA-Core-Prüfungen sind erforderlich; praktischer Simulator-Langzeitlauf und Geräteabnahme stehen aus. **Keine Freigabe für echte Netzanschlussschutzfunktionen.**
