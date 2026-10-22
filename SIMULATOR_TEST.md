# Power Manager 4.0 – verpflichtende Simulator-Abnahme

**Vorbereitung:** Alle Tests zuerst im Dry-Run; anschließend nur mit Simulator-Entities Live schalten. Keine realen Leistungsschalter oder Wallboxen ansteuern. Netzsensor muss frisch sein. Für jede Taktfolge Netzbezug, PV, Soll je Verbraucher, tatsächlich ausgegebener Stellwert (inkl. Rundung), optionale Istleistung, Einschaltzustand und PMAX-Projektion aufzeichnen.

| Test | Erwartung |
|---|---|
| NORMAL, 140-kW-PMAX, Netz 122,08 kW, Wärmepumpe bisher 8,3 kW | Zügige kontrollierte Erhöhung innerhalb aktuell gemessener Netzreserve |
| NORMAL, 139,17 kW Netz, WB1 6 und WB2 6,5 kW | Technisch identische Wallboxen können sich annähern, ohne vorzeitig Leistung aus ungeprüfter Reduktion zu „leihen“ |
| NORMAL über 140 kW | Sofortige Reduzierung bis zu technischen Minima; wenn nicht möglich, sichere Pause; nicht vorgegeben, dass unregelbare Grundlast unter PMAX sinkt |
| NORMAL ohne Verbraucher-Istsensor | Regelung arbeitet mit zuletzt gesendetem physikalischem Ausgangsbefehl als Schätzung, Netzsensor als Rückmeldung |
| Gleiche Lasten, verschiedene Prioritäten | Priorisierte Verteilung aus 3.1.1 |
| PV mit 10 kW echter Einspeisung, 2 gleiche Wallboxen und je 4,14 kW Minimum | Gleichmäßiger Sollwert 5/5 kW, sofern Ausgangsschritte dies erlauben |
| PV mit 3 kW Einspeisung, Mindeststart 4,14 kW | Kein illegaler Teilstart |
| PV mit 0 kW Export und bereits laufenden PV-Lasten | Keine automatische AUS/EIN-Schleife nur durch den Export null; bestehende Leistung wird budgetiert |
| PV mit +5 kW Netzbezug statt Export | Lasten reduzieren; keine zusätzliche Freigabe aus bloßer PV-Produktion |
| Batterie lädt / entlädt / SOC 0 / Sensor fehlt | Gleiche Regelentscheidung bei identischen Netz-/PV-Daten – Speicher wird nicht gesteuert |
| W/kW/A-Ausgabe und gültige Gerätetakte | Werte ausschließlich auf zulässige Stufen abwärts runden, niemals verbotenen AUS-/Unbegrenzt-Code senden |
| Netzsensor veraltet oder ungültig | Live aus, sichere Ausgänge / Fail-Safe |
| 100+ Regelzyklen mit Netzrauschen und sprunghafter Last | Keine dauerhafte EIN/AUS-Oszillation, keine unerklärten Leistungsfreigaben |

**Abnahme:** Erst wenn CI grün, alle relevanten Simulatorfälle erfolgreich, kein Oszillieren und sichere Pausen- und Rückrollmechanismen nachgewiesen sind, kann 4.0.0 produktiv freigegeben werden.

## Neu: 5-Sekunden-Schrittfolge ab RC2

**Beispiel 30 kW Netzspielraum:** Wärmepumpe Priorität 1 (Max 20 kW) und Wallbox Priorität 2 (Max 11 kW) starten ausgeschaltet. Im ersten Durchlauf nur Wärmepumpe auf höchstens 20 kW. Nach 5 Sekunden und einem **neuen** Netzbericht darf die Wallbox den verbliebenen Netzspielraum (bis 10 kW) erhalten. Vor Ablauf der fünf Sekunden darf kein zweiter Verbraucher zusätzlich starten.

**Abschalten:** Wenn mehrere Verbraucher regulär nicht mehr gebraucht werden, wird niedrigere Priorität zuerst reduziert/abgeschaltet und nach jeweils 5 Sekunden der nächste. Falls der Netzsensor Überschreitung von PMAX oder PV-Import meldet, müssen alle nötigen Senkungen **sofort** erfolgen, auch wenn die letzte Änderung erst eine Sekunde alt ist.

**Staler Sensor:** Bei abgelaufenem Timer, aber ohne Netzreport seit dem letzten Stellbefehl: keine zweite Erhöhung; nach dem nächsten frischen Netzreport weiterregeln. Fehlende Verbraucher-Istsensoren dürfen diese Schrittkette nicht verhindern.

**PV:** Zwei technisch identische Wallboxen mit 10 kW realem Export: zuerst nur eine mit 5 kW, nach 5 Sekunden und neu gemeldeten 5 kW Export die zweite mit 5 kW. Danach möglichst ausgeglichen; keine dauernde EIN/AUS-Schleife.

