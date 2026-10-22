# Power Manager 4.0

**Ein Home-Assistant-Energiemanager mit zwei überschaubaren Betriebsarten:** Netz-Peakshaving und echter PV-Überschuss. Dies ist der **Entwicklungsstand 4.0.0 zur Simulatorabnahme**, keine physisch abgenommene Produktionsfreigabe.

## Grundprinzip

| | NORMAL (Peakshaving) | PV-ÜBERSCHUSS |
|---|---|---|
| Maßgebliches Signal | Aktueller Netzbezug | Aktuelle Netzeinspeisung |
| Ziel | PMAX möglichst gut ausnutzen, nicht überschreiten | Tatsächlichen Überschuss nutzen, Netzbezug vermeiden |
| Zuteilung | Nach konfigurierter Priorität | Gleichmäßig unter geeigneten PV-Verbrauchern |
| Grenzen | Verbraucher-Min/Max, Anforderung, sichere Ausgangswerte | Dieselben Grenzen; kein Start unter Mindestleistung |
| Batterie | Nicht beteiligt | Nicht beteiligt |

Die Batterie läuft **immer eigenständig in der vom Hersteller gewählten Automatik**. Batterie-Leistung und SOC können optional angezeigt werden; sie sind **keine Regler-Eingangsgrößen**.

**Pflicht:** frische, gültige Netzleistungsmessung. Eine Istleistungsmessung für einzelne Verbraucher ist **optional**. Ohne Istwert verwendet der Regler den zuletzt tatsächlich gesendeten/quantisierten Leistungsbefehl als *Schätzung*, nicht als bestätigten Istwert. Die Netzleistung kontrolliert den Gesamteffekt.

## Rechenweg

**Normal:** `Basislast = Netzbezug − derzeit bekannte geregelte Last`; `PMAX-Budget = PMAX − Netzreserve − Basislast`. Bestehende Verbraucher werden nach Priorität und nach ihren technischen Grenzen berücksichtigt. Eine positive Zuteilungsänderung darf den **bereits gemessenen Netzspielraum** (abzüglich einstellbarem Messrausch-Puffer) nicht überschreiten. Reduktionen sind unmittelbar erlaubt.

**PV:** `PV-Budget = max(0, bereits laufende PV-Verbraucherleistung − Netzbezug)`, **aber nur bei vorhandenem PV-Messwert > 0**. Für **neue** zusätzliche Verbraucherleistung ist echte, gemessene Netzeinspeisung erforderlich. Laufende Verbraucher werden mitgerechnet, damit Netzeinspeisung 0 kW nicht unweigerlich ein AUS/EIN-Pendeln auslöst. Gleich konfigurierte Verbraucher teilen ihre freigegebene Mehrleistung fair; Reduzierungen anderer Verbraucher werden **nicht vor der nächsten Netzmessung** als verfügbare Leistung ausgegeben.

**Wichtig:** Ohne Kontrolle des Batteriespeichers lässt sich nicht garantieren, dass bereits laufende Lasten ausschließlich aus PV stammen. Ein plötzliches Ende autonomer Batterieentladung oder schnelle Hauslastsprünge können vor der nächsten Reaktion kurzzeitig PMAX überschreiten. Wer eine physikalisch harte Grenze benötigt, muss eine unabhängige Netz-/Wechselrichterabsicherung nutzen.

## Was aus früheren Versionen erhalten bleibt

- Der bewährte Prioritäts- und Min/Max-Allocator aus **3.1.1**, keine künstliche Round-Robin-Umschaltung.
- Die verständlichere Einrichtung und das Home-Assistant-Dashboard aus **3.3.x**.
- Unterstützte Home-Assistant-Zahlen-/Schalt-Entities, optionale MQTT-/Modbus-Kommandowege und sichere Pausenbefehle.
- Geräteausgaben in A/W/kW/MW, Abwärts-Rundung auf tatsächlich zulässige Geräteschritte, elektrische EVSE-Mindestströme und verbotene Sondercodes.
- Live bleibt nach einem Neustart **aus** und muss nach Prüfung aktiv eingeschaltet werden. Ein ungültiger Netzsensor oder fehlerhafte Ausgänge lösen den sicheren Zustand aus.

## 5-Sekunden-Schrittregelung (V4.0 RC2)

In der Home-Assistant-Integration wird **maximal eine nicht sicherheitsbedingte Verbraucheränderung pro 5-Sekunden-Schritt** freigegeben:

1. Zuerst wird nach der bewährten Prioritäts-/Min-Max-Verteilung ein vollständiger Zielplan berechnet.
2. Es wird nur der höchstpriorisierte noch ausstehende Verbraucher zugeschaltet oder erhöht. Bei geplanter, nicht dringender Abschaltung gibt zuerst die niedrigste Priorität Leistung ab.
3. Nach **5 Sekunden** und einem **neuen Netzsensorbericht nach der letzten Änderung** wird erneut gerechnet und erst dann der nächste Verbraucher geändert.
4. Die tatsächlich ausgegebenen, auf Geräte-Schrittweiten begrenzten Werte bleiben die Schätzbasis. Geräte-Istsensoren sind optional.
5. **PMAX-Überschreitung, unerwünschter PV-Netzbezug und notwendige Sicherheitssenkungen warten nicht auf den Timer:** Mehrere Verbraucher können in einer Sicherheitsreaktion gleichzeitig abgeregelt werden.

Die 5 Sekunden sind eine feste *Mindestzeit zwischen normalen Geräteänderungen*, kein garantierter Höchstwert bei fehlender frischer Netzmessung oder längeren gerätespezifischen Mindestpausen. Ein nicht antwortender Sensor wird niemals dadurch übergangen, dass die Uhr abgelaufen ist.

## Installation und Test

Die Einrichtungsanleitung steht in [INSTALLATION.md](INSTALLATION.md). Den vorgeschriebenen Simulator-Ablauf vor Freigabe beschreibt [SIMULATOR_TEST.md](SIMULATOR_TEST.md). Die technische Architektur und die Gründe für bewusst nicht eingebaute Funktionen stehen in [docs/ARCHITECTURE_4.md](docs/ARCHITECTURE_4.md).

## Repository

`main` ist bis zur Simulatorabnahme die dokumentierte stabile Referenz **3.1.1**; Entwicklung und Codebereinigung finden im Branch `refactor/v4.0.0-unified` statt. Frühere Git-Tags bleiben zur Wiederherstellung verfügbar, nicht als aktive Entwicklungsprodukte. Die HACS-Release-Freigabe folgt **erst nach** Tests und Abnahme.
