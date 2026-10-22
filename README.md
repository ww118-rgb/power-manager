# Power Manager 4.0

**Ein Home-Assistant-Energiemanager mit zwei überschaubaren Betriebsarten:** Netz-Peakshaving und echter PV-Überschuss. Dies ist der **Entwicklungsstand 4.0.0 zur Simulatorabnahme**, keine physisch abgenommene Produktionsfreigabe.

## Grundprinzip

| | NORMAL (Peakshaving) | PV-ÜBERSCHUSS |
|---|---|---|
| Maßgebliches Signal | Aktueller Netzbezug | PV-Erzeugung minus unabhängig gemessener Hausgrundverbrauch; ohne Hausmessung echte Netzeinspeisung |
| Ziel | PMAX möglichst gut ausnutzen, nicht überschreiten | Tatsächlichen Überschuss nutzen, Netzbezug vermeiden |
| Zuteilung | Nach konfigurierter Priorität | Gleichmäßig unter geeigneten PV-Verbrauchern |
| Grenzen | Verbraucher-Min/Max, Anforderung, sichere Ausgangswerte | Dieselben Grenzen; kein Start unter Mindestleistung |
| Batterie | Nicht beteiligt | Nicht beteiligt |

Eine Speichersteuerung, SOC-Abfrage oder Batterie-Konfiguration ist nicht Teil dieser Integration. Nur Netzleistung, PV-Produktion, optionaler **Hausgrundverbrauch** und Verbrauchergrenzen beeinflussen die Regelung.

**Pflicht:** frische, gültige Netzleistungsmessung. Eine Istleistungsmessung für einzelne Verbraucher ist **optional**. Ohne Istwert verwendet der Regler den zuletzt tatsächlich gesendeten/quantisierten Leistungsbefehl als *Schätzung*, nicht als bestätigten Istwert. Die Netzleistung kontrolliert den Gesamteffekt.

## Rechenweg

**Normal:** `Basislast = Netzbezug − derzeit bekannte geregelte Last`; `PMAX-Budget = PMAX − Netzreserve − Basislast`. Bestehende Verbraucher werden nach Priorität und nach ihren technischen Grenzen berücksichtigt. Eine positive Zuteilungsänderung darf den **bereits gemessenen Netzspielraum** (abzüglich einstellbarem Messrausch-Puffer) nicht überschreiten. Reduktionen sind unmittelbar erlaubt.

**PV bei separat gemessenem Hausgrundverbrauch:** `PV-Budget = max(0, PV-Erzeugung − nicht regelbarer Hausgrundverbrauch)`. Das funktioniert **auch bei 0 kW Netzeinspeisung**, weil eine externe automatische Verbrauchsquelle die Einspeisung bereits auf null halten kann. Sobald realer Netzbezug entsteht, gilt die strengere Messkorrektur `Budget ≤ max(0, bisherige geregelte Leistung − Netzbezug)` und es wird ohne Timer verzögertes Abregeln sofort reduziert. Bei fehlendem, ungültigem oder veraltetem Hausverbrauchssensor bleibt die bisherige konservative Regelung aus bestätigter Netzeinspeisung und bereits laufenden PV-Verbrauchern aktiv. Nie frei geschätzten Hausverbrauch annehmen. **Der Hausgrundverbrauchssensor darf keine vom Power Manager gesteuerten Verbraucher enthalten.**

**Wichtig:** Die Netzmessung überwacht die reale Reaktion. Eine eigenständige Anlage kann Energieflüsse ändern, ehe die nächste Messung vorliegt. Eine physikalisch harte PMAX-Garantie benötigt unabhängigen Netz-/Anlagenschutz.

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
