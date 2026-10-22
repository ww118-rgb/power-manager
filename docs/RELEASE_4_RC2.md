# Power Manager 4.0.0-rc.2 – Priorisierte 5-Sekunden-Schrittregelung

**Nur Simulator-Vorabversion. Nicht für den unbeaufsichtigten Anlagenbetrieb oder als garantierter Netzanschlussschutz freigegeben.** `main` (3.1.1) und die vorherige RC1 bleiben unverändert.

## Verhalten

- Priorisierter Start: Pro normalem Schritt wird nur **ein** Verbraucher zugeschaltet oder erhöht. Mit PMAX 140 kW und 30 kW freiem Netzspielraum schaltet z. B. zuerst die Wärmepumpe (Priorität 1, maximal 20 kW), erst nach 5 Sekunden und einem neu gemeldeten Netzwert erhält die Wallbox (Priorität 2) die verbleibenden 10 kW.
- Nicht sicherheitskritisches Abschalten ebenfalls schrittweise: niedrigste Priorität zuerst, danach nach weiteren 5 Sekunden der nächste Verbraucher.
- Die bisherige `HEARTBEAT_INTERVAL_SECONDS = 5.0`-Aktualisierung wird benutzt; es ist **kein zweiter Hintergrundtimer** nötig.
- **Sicherheitsausnahme:** Überschreitet der gemessene Netzbezug PMAX oder würde eine gestaffelte Reduktion das zulässige Budget verletzen, werden die erforderlichen Geräte sofort heruntergeregelt. Im PV-Modus wird unerwünschter Netzbezug ebenfalls sofort reduziert.
- Die nächste Freigabe benötigt eine **echte neue Netzsensor-Meldung nach dem letzten Schaltbefehl**. Fehlt dieser Messwert, kann die Wartezeit länger als fünf Sekunden sein. Geräte-Mindestlaufzeiten bleiben ebenfalls maßgeblich.
- Verfügbare Verbraucher-Istleistung kann unterstützend genutzt werden; sie ist weiterhin **keine Pflicht**. Batterie und SOC steuern weiterhin nichts.
- Die priorisierte Originalverteilung aus 3.1.1 und die sicheren W/kW/A-Ausgaben aus 3.3.x bleiben erhalten.

## Tests

Die automatisierte Python-Suite auf dem Entwicklungszweig: **284 bestanden, 1 übersprungen**. HACS, Hassfest und die realen HA-Core-Kompatibilitätstests (2026.8 und 2026.10) sind erfolgreich. Die Veröffentlichung führt die Python- und Frontendprüfungen erneut aus.

## Simulator-Prüfung

1. Home-Assistant-Sicherung erstellen, isolierte Simulatorinstanz verwenden.
2. Über HACS Vorabversion `v4.0.0-rc.2` auswählen, Home Assistant neu starten, zunächst Dry-Run.
3. Nach Einschalten der simulierten Live-Regelung folgende Szenarien mit Zeitstempeln prüfen: 30-kW-Freigabe mit WP-P1 und WB-P2; unterschiedliche Mindestleistungen; staler Netzsensor nach t=5s; sofortige Abregelung über PMAX; freiwillige Abschaltung in umgekehrter Priorität; zwei PV-Wallboxen bei 10 kW realem Export.
4. Stellbefehl, optionaler Istwert und Netzbezug gemeinsam prüfen. Zusätzliche Freigabe darf nicht aus noch nicht gemessener Lastreduktion stammen.

**Sicherheitsgrenze:** Ein plötzliches Nachlassen der autonomen Batterieentladung oder ein schneller Hauslastsprung kann vor der nächsten Messung kurzzeitig eine physische Netzgrenze verletzen. Dafür ist ein unabhängiger Schutz nötig, wenn die Grenze absolut eingehalten werden muss.

Änderungen: [PR #11](https://github.com/ww118-rgb/power-manager/pull/11). Technische [Simulator-Testmatrix](https://github.com/ww118-rgb/power-manager/blob/feature/v4-sequential-5s/SIMULATOR_TEST.md).
