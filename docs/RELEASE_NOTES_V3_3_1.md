# Power Manager v3.3.1 — Einfacher Einrichtungsassistent (HACS-Pre-Release)

**TESTVERSION. Nicht für unbeaufsichtigte sicherheitskritische Anlagen freigegeben.**

V3.3.1 verbessert die Einrichtung gegenüber V3.3.0, ohne den bestehenden PMAX-Regler durch vereinfachte unsichere Näherungen zu ersetzen.

## Neuer einfacher Einstieg

- Globale Basiseinrichtung mit Netzsensor, PMAX, PV-/Batterie-/SOC-Werten; Sensor-Timeouts und Hybridparameter stehen nur unter **Experteneinstellungen**.
- Schrittweise Verbraucheranlage: **Gerätetyp/Leistung/Priorität → Bedarf und Istleistung → Anschlussart → passende Befehle → Vorschau und Sicherheitsbestätigung**.
- Wählbarer Bedarf: **immer bereit**, **nur bei Bedarfssensor**, oder **deaktiviert**. Keine versteckte Bedeutung des alten Standard-Anforderungswerts 0 im neuen Assistenten.
- HA-Entity, Modbus TCP und MQTT zeigen nur jeweils relevante Einstellungen. Komplexe Zeit-/Hysterese-Werte bleiben optional.
- Wallbox-Konfiguration zeigt nur EVSE-Parameter einschließlich Phasen, Ladestromgrenzen und Pausenbefehl.
- Gerätestufen können als einzelne kW-/Code-Feldpaare eingegeben werden; keine JSON-Handarbeit nötig.
- Gerätebefehls-Vorschau zeigt rein rechnerische Übersetzung für AUS/Mindest-/Maximalleistung. Diese Vorschau bestätigt **keine** reale Gerätewirkung.
- Textbasierte MQTT-EIN/AUS-Kommandos benötigen keine überflüssigen numerischen Schaltcodes.
- Konfigurationsänderungen an direkten Geräteausgängen verlangen eine neue Sicherheitsbestätigung. Eine bloße Bestätigung ersetzt nicht die Prüfung nach Gerätehandbuch.
- Der bisher sichtbare MQTT-Übersetzungsfehler mit fehlender Platzhaltervariable wurde behoben.
- V3.3.0-Konfigurationen behalten ihre vorherige Anforderungslogik, sofern noch kein Bedarfsmodus gewählt wurde.

## Sicherheit und bekannte Grenzen

- **Live wird nach Installation, Neustart und Verbrauchereinrichtung nicht automatisch aktiviert.**
- Für Live ist weiterhin pro Verbraucher ein frischer Istleistungssensor erforderlich, um Leistungsreduzierungen physisch zu bestätigen.
- Direkte Modbus-/MQTT-Gerätebefehle sind nur mit dokumentiertem, überprüftem Pausen-/AUS-Wert und anschließender Prüfung am Simulator zu verwenden.
- Home-Assistant-Smoke-Tests prüfen ausgewählte Versionen 2026.8 und 2026.10; vollständige Prüfung aller alten und zukünftigen HA-Versionen ist unmöglich.
- Automatische Erkennung von Messwert-Aktualisierungszeiten und Gerätefähigkeiten aus Drittanbieter-Sensoren sowie echte Simulator-Abnahmetests sind nicht abgeschlossen.
- Nach Möglichkeit **auf einer Testinstallation** verwenden. Vor Update vollständiges Home-Assistant-Backup erstellen. Erst nur Dry-Run testen.

## Installation via HACS

HACS → Power Manager → Menü (⋮) → **Erneut herunterladen / Redownload** → bei Bedarf **Vorabversionen anzeigen** → `v3.3.1` auswählen → herunterladen → Home Assistant neu starten.

Der GitHub-Release ist als **Pre-Release** markiert. V3.1.1 bleibt auf `main`; V3.3.0 wird nicht rückwirkend ersetzt.

**Quellstand:** [V3.3.1-Draft-PR #3](https://github.com/ww118-rgb/power-manager/pull/3)

**Dokumentation:** Power Manager Konzept/Anforderungen/Testplan v1.2; REQ-113–120, T139–152 zur UI-Neustrukturierung.
