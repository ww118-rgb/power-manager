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

## Installation und Test

Die Einrichtungsanleitung steht in [INSTALLATION.md](INSTALLATION.md). Den vorgeschriebenen Simulator-Ablauf vor Freigabe beschreibt [SIMULATOR_TEST.md](SIMULATOR_TEST.md). Die technische Architektur und die Gründe für bewusst nicht eingebaute Funktionen stehen in [docs/ARCHITECTURE_4.md](docs/ARCHITECTURE_4.md).

## Repository

`main` ist bis zur Simulatorabnahme die dokumentierte stabile Referenz **3.1.1**; Entwicklung und Codebereinigung finden im Branch `refactor/v4.0.0-unified` statt. Frühere Git-Tags bleiben zur Wiederherstellung verfügbar, nicht als aktive Entwicklungsprodukte. Die HACS-Release-Freigabe folgt **erst nach** Tests und Abnahme.
