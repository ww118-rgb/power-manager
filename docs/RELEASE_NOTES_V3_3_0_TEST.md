# Power Manager v3.3.0 — HACS-Testversion (Pre-Release)

**TESTVERSION / NICHT FÜR UNBEAUFSICHTIGTEN PRODUKTIVBETRIEB FREIGEGEBEN.**

Diese GitHub-Version wird vom Entwicklungsbranch `feature/v3.3.0-rc` gebaut, **nicht** aus `main`. Der offizielle Stand `main` bleibt V3.1.1. Dies ist ausdrücklich ein Pre-Release, kein stabiler allgemeiner Updatehinweis.

## Enthaltene Funktionen

- PMAX-Regelung und PV-Überschussmodus mit priorisierten Lasten.
- Batterie bleibt autonom; SOC-Reserve, Wiedereinschalthysterese und PV-Lastversuche sind konfigurierbar.
- Verbraucherkonfiguration mit HA-Entity-, direktem Modbus-TCP- und MQTT-Schreibweg.
- Gerätespezifische numerische Codes, Stufenprofile, Pausenwerte, verbotene Werte, EVSE-Sonderwertschutz und MQTT-Textbefehle für Schaltlasten.
- Frische Messwerte und Überwachung der tatsächlichen Verbraucher-Reduktion, Live-Regelung nur nach bewusster Freigabe.
- Eigene Logos/Icons und angeglichene Versionsnummer 3.3.0.

## Getestet und Grenzen

Die GitHub-CI hat Python-Tests, HACS-Validierung und Hassfest bestanden. **Nicht** als abgeschlossen gelten die Simulator-Abnahme, die gesamte Home-Assistant-Versionsmatrix, das physische Reaktionsverhalten unterschiedlicher Wechselrichter, Wallboxen und Wärmepumpen sowie die vollständige praktische Prüfung aller Testfälle des Pflichtenhefts.

**Vor dem Test:**
1. Vollständiges HA-Backup erstellen.
2. Nur auf separater Testinstallation oder mit entsprechend isoliertem Simulator testen.
3. Nach Installation Home Assistant neu starten.
4. Zuerst nur Konfiguration und Dry-Run; Live-Ausgänge nicht aktivieren, bis alle sicheren Gerätewerte und Istleistungssensoren geprüft wurden.
5. Bei Problemen Logs und genaue HA-Core-Version dokumentieren; Fixes folgen in V3.3.x.

**Installation via HACS:** In HACS beim Power-Manager-Repository `Download` oder `Redownload` auswählen, unter **Need a different version? / Andere Version wählen** die Beta-/Vorabversionen aktivieren und `v3.3.0` wählen. Solange kein solcher GitHub-Pre-Release verfügbar ist, wird der Entwicklungsbranch von HACS nicht als auswählbare Version angeboten.

**Anforderungen:** [Statusübersicht](https://github.com/ww118-rgb/power-manager/blob/feature/v3.3.0-rc/docs/anforderungen_v0_8_traceability.md)
