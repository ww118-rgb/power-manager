# Changelog

## 4.0.0-rc.3 – PV-Vorrang ohne Speicher-Daten

- PV-Erzeugung minus unabhängiger Hausgrundverbrauch als **optionaler**, überprüfbarer PV-Freigabeweg; Netzeinspeisung bleibt sicherer Fallback.
- Behebt den Simulatorfall PV 38,60 kW, Hausgrundverbrauch 0,05 kW, Netz 0,00 kW: 38,55 kW vorläufig verfügbare PV-Leistung statt irrtümlich 0 kW.
- Konfigurationsschema V6 räumt die bisherigen Batterie-/SOC-Entities, Skalierungen und Timeoutwerte aus dem aktiven Code und der UI auf. Historische Konfigurationen werden migriert; Geräteprofile bleiben erhalten.
- Unverändert: 5-Sekunden-Prioritätsfolge, frischer Netzsensor vor weiterer Erhöhung und unverzügliche Abregelung bei tatsächlichem Netzbezug.
- **Nur Simulator-Testkandidat**, noch keine physikalische Anlagenabnahme.


## 4.0.0-rc.2 – priorisierte, rückgemeldete 5-Sekunden-Schrittregelung

- Pro fünf Sekunden eine nicht sicherheitsbedingte Verbraucheränderung: Start/Erhöhung nach aufsteigender Priorität, freiwilliges Absenken/Abschalten nach absteigender Priorität.
- Die nächste Leistungsfreigabe setzt eine neue **Netzsensor-Rückmeldung nach der vorherigen Änderung** voraus. Verbraucher-Istleistung bleibt optional; letzter tatsächlich gesendeter Befehl wird weiterhin als Schätzung genutzt.
- Bei drohendem/aktuellem PMAX-Überzug und PV-Netzbezug erfolgen notwendige Reduktionen ohne Verzögerung.
- Keine Batterieansteuerung, keine Hybrid-Probe und keine Rückkehr der alten globalen 15-Sekunden-Wartezeit.
- Regressionen für 30-kW-Beispiel mit WP vor WB, zwei PV-Wallboxen, stalen Netzsensor, 5-Sekunden-Pausen und sofortige Sicherheitsabschaltungen.
- **Nur für Simulation**; reale Anlagenschutzfunktionen weiterhin nicht abgenommen.


## 4.0.0 – in Entwicklung / Simulatorabnahme offen

- Einheitlicher Regler auf Basis des priorisierten 3.1.1-Allocators.
- Netz-PMAX in NORMAL; PV-Einspeisung plus laufende PV-Verbraucher in SURPLUS.
- Gleichverteilung nur bei technisch vergleichbaren Lasten und ohne unbestätigte Netzentlastung vorwegzunehmen.
- Keine Batterie-/SOC-Steuerung, keine Hybrid-Experimente, keine globalen Freigabe-Timer.
- Einzelne Istleistung optional, Netzsensor verpflichtend.
- Gerätesicherheits- und Einheitenkorrekturen sowie neues Home-Assistant-Design aus 3.3.x übernommen.
- Entfernte alte versionsspezifische GitHub-Workflows, veraltete Release-Notizen und Feedback-Sperrklassen.
- Frühere Versionen sind über **Git-Tags/Git-Historie** weiterhin nachvollziehbar.

**Status:** noch keine produktive Freigabe; automatische CI und Simulator-Abnahme erforderlich.
