# Power Manager v3.3.2 – EVSE-Schreibwerte A/W/kW (HACS-Testversion)

**Pre-Release – nur für kontrollierte Tests. Keine automatische Freigabe für unbeaufsichtigten Produktivbetrieb.**

## Neu in V3.3.2

- **Wallbox bleibt EVSE**: Regler arbeitet intern in kW, aber der Gerätebefehl ist unabhängig vom Protokoll in **A, W oder kW** konfigurierbar. Bei vorhandenen HA-Number-Entities ist Erkennung aus `unit_of_measurement` (A/W/kW) möglich; bei direktem Modbus/MQTT muss die Einheit explizit angegeben werden.
- **Ganzer Ladestrom**: Schrittweite pro Gerät einstellbar, Voreinstellung 1 A. Beispielsweise 6,90 kW → 10 A, 11,00 kW → 15 A, 11,04 kW → 16 A (bei 3×230 V).
- **Leistungsstufen für MQTT oder HA-Entities**: Voreinstellung 1.000 W, individuell änderbar; 6,90 kW → 6.000 W, 11,00 kW → 11.000 W.
- **PMAX-Schutz**: immer abwärts auf den nächstzulässigen Schritt; nie höher als rechnerisch freigegebene Leistung. Wenn die gerundete Stufe die physikalische Mindestladung (6 A/3×230 V = 4,14 kW) nicht erreicht, wird die Wallbox pausiert; bei 1.000-W-Stufen sind deshalb 4,14–4,99 kW keine zulässige aktive Ladestufe, 5.000 W erst ab 5 kW.
- **Pause getrennt**: 0 A kann bei einem Mennekes-Strombegrenzungsregister *unbegrenzt* bedeuten; die bestätigte 0,01-A-Pause bleibt erhalten. 0 W ist nur auf einem entsprechend bestätigten Power-Ausgang ein Pausenbefehl.
- **Einfacherer Assistent**: separate Seite „Was erwartet der Wallbox-Ausgang?“ und anschließend nur passende Einstellfelder. Die Abschlussvorschau zeigt die ausgegebenen Werte und prüft bei HA-Zahlen-Entities nach Möglichkeit Wertebereich und Schrittweite ohne Schreibversuch.
- **Abwärtskompatibilität**: bestehende V3.3.1-Geräteprofile ohne `evse_output_format` werden nicht stillschweigend umgestellt – sie behalten die bisherige A-Interpretation.

## Vor dem Test

1. Home-Assistant-Backup anfertigen.
2. HACS → Power Manager → ⋮ → Erneut herunterladen → Vorabversion `v3.3.2` auswählen → Home Assistant neu starten.
3. **Live ausgeschaltet lassen** und jede Wallbox einmal öffnen: Ausgabeformat A/W/kW, aktuelle Wertebereiche und Schrittweite prüfen.
4. Bei HA-Entity „Energysim Wallbox X Sollleistung“ prüfen, ob sie `kW` oder `W` meldet und z. B. 0–11 kW annimmt. Nur bei bestätigter Gerätewirkung sichere Pausenbefehle freigeben.
5. Bei direktem Mennekes-Modbus-Stromregister ausschließlich nach dokumentiertem Register, Datenformat und Pausenwert vorgehen.
6. Nach Konfiguration zuerst Dry-Run, dann kontrollierte Simulatorprüfung mit Istleistungsrückmeldung.

**Wichtig:** 0-A-/0-W-Verhalten und MQTT/Modbus-Transportsemantik müssen im Simulator bestätigt werden. Statische Tests ersetzen keine tatsächliche Geräte-Abnahme. Besonders bei der HA-Oberfläche prüfen wir gemeinsam, ob alle deutschen Beschriftungen tatsächlich korrekt angezeigt werden.

**Pflichtenheft:** Power_Manager_Konzept_Anforderungen_Testplan_v1_2_5.docx/PDF (REQ-137 bis REQ-142, T179 bis T190 zusätzlich zu allen bisherigen Anforderungen).

[Entwicklungs-Pull-Request #4](https://github.com/ww118-rgb/power-manager/pull/4).
