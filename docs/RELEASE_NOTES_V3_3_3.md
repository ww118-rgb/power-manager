# Power Manager v3.3.3 – einheitliche interne kW und korrekte HA-Ausgabewerte

**HACS-Vorabversion, nur für kontrollierte Tests. Keine produktive Freigabe ohne Simulatorabnahme.**

## Wichtigste Fehlerkorrektur

Die tatsächlichen V3.3.2-Fehler aus der Home-Assistant-Inbetriebnahme waren:
- Wärmepumpe: 5.000 W sollte fälschlich in eine HA-Zahlen-Entity mit Bereich 0–20 geschrieben werden, die kW annimmt.
- Wallbox: 11.000 W sollte fälschlich in eine HA-Zahlen-Entity mit Bereich 0–11 geschrieben werden, die kW annimmt.
- Heizstab: 1.000 W sollte fälschlich in eine HA-Zahlen-Entity mit Bereich 0–10 geschrieben werden, die kW annimmt.
- Während des Betriebs wurde ein Wert 9,6685 auf eine 0,1-stufige HA-Zahlen-Entity geschrieben, woraufhin der globale Fail-Safe ansprang.

Die Software hält im Regler nun alle **physikalischen Leistungen konsequent in kW**. Für jeden HA-Zahlen-Ausgang folgt die Übersetzung:

1. kW-Zuteilung durch PMAX, PV, Prioritäten und Gerätegrenzen
2. Geräteprofil (A, W, kW, MW oder dokumentierter Hersteller-Code)
3. Bei einem **physikalischen Leistungswert** Anpassung an das tatsächliche `unit_of_measurement` (W/kW/MW) der HA-Entity – z. B. 11.000 W → 11 kW
4. Native `min`, `max`, `step` prüfen und positive physikalische Stellwerte **ausschließlich abwärts** runden; z. B. 9,6685 kW bei 0,1-kW-Schritten → 9,6 kW
5. Wird die physikalische Mindestleistung unterschritten, sicheren Pausenbefehl statt unzulässiger Aufrundung verwenden.

**Herstellerspezifische Codes und Pausenwerte werden niemals geraten, gerundet oder als physikalische kW-Werte umgedeutet.** Beispielsweise bleibt `0 A` für bestimmte Mennekes-Geräte ein potenziell gefährlicher Freigabecode.

Bei unbekannter HA-Ausgabeeinheit kann die Integration nicht aus `min/max` erraten, ob die Entity W oder kW erwartet; sie lehnt unsichere Fälle ab. **Direkte MQTT-/Modbus-Schreibwege** arbeiten weiterhin mit der explizit konfigurierten Geräte-Einheit (nicht mit HA-Entity-Attributen).

## Tests und Grenzen

- Pure Unit-Tests der Leistungskonversion und sicheren Schrittquantisierung
- HA-Core-Integrationstests für Wärmepumpe, Heizstab und Wallbox mit realitätsnahen Entity-Attributen unter HA 2026.8 und HA 2026.10
- Weitere PMAX-, HACS- und Hassfest-Tests wie zuvor
- **Noch offen:** reale Geräte-/Simulatorprüfung, Vorzeichen- und Sensor-Zeitversatz, Praxisnachweis der sicheren Pause, lange stabilitätsorientierte Lastverläufe.
- **Bewusst noch nicht enthalten:** freie Eingabe der physischen min/max-Leistung in W/MW im Einrichtungsformular; derzeit werden diese Werte verständlich in kW angegeben. Ein entsprechender Bedienwunsch ist in Dokumentation v1.2.8 aufgenommen.

## Update auf die Testversion

1. Home-Assistant-Sicherung erstellen; **Live-Regelung AUS lassen**.
2. HACS → Power Manager → ⋮ → Erneut herunterladen → Vorabversion **v3.3.3** wählen → HA vollständig neu starten.
3. Bei jedem Verbraucher die HA-Ausgangs-Entity im Entwicklerwerkzeug lesen: `unit_of_measurement`, `min`, `max`, `step` und sicherer Pausenwert.
4. Prüfen, ob ein frei gewählter Gerätecode versehentlich als Leistungswert konfiguriert wurde.
5. Erst Dry-Run, danach die Reaktionen am Simulator einzeln mit tatsächlichem Verbraucher-Istwert überprüfen.
6. Beim Fail-Safe keine Grenzen hochsetzen oder Pausencodes raten; Fehlermeldung und Entity-Attribute sichern.

Die V3.3.2 und V3.3.1 bleiben als unveränderte GitHub-Versionen erhalten. `main` bleibt weiterhin stabil auf V3.1.1.

[Entwicklungs-PR #6](https://github.com/ww118-rgb/power-manager/pull/6)
