# Power Manager v3.3.5 – Einfache Netz- und PV-Regelung

**Vorabversion ausschließlich für den Simulator. Nicht für unbeaufsichtigte produktive Anlagen freigegeben.** `main` bleibt unverändert.

## Was ist jetzt einfacher?

**NORMAL / Peakshaving**
- Der Netzsensor und PMAX sind die entscheidenden Eingänge.
- Der Regler rechnet: `Basislast = Netzbezug − aktuell steuerbare Last`; `Budget = PMAX − Netzreserve − Basislast`.
- Regelbare Verbraucher werden nach Priorität innerhalb Mindest-/Maximalleistung zugeteilt.
- Zusätzliche Leistung darf den **aktuell gemessenen** Netzspielraum nicht überschreiten. Ein kleiner, einstellbarer Freigabepuffer (Standard 0,3 kW) fängt Messrauschen ab.
- Wenn der Netzbezug die Grenze überschreitet, wird sofort reduziert. Die zusätzliche globale 15-Sekunden-Wartezeit von V3.3.4 wird nicht mehr angewendet.

**PV-Überschuss**
- Neue Lasten werden nur mit **tatsächlich gemessener Netzeinspeisung** freigegeben, nicht mit der gesamten PV-Erzeugung (darin steckt auch Hausverbrauch).
- Bereits laufende PV-Verbraucher bleiben bei Netzeinspeisung 0 kW grundsätzlich berücksichtigt: `PV-Budget = max(0, bisherige PV-Verbraucherleistung − Netzbezug)`. Ohne diese Rückrechnung würde jede PV-Last sofort ein-/ausschalten, sobald sie den Export auf null bringt.
- Geeignete PV-Verbraucher teilen das Budget **gleichmäßig**, unter Beachtung ihrer Mindest-/Höchstleistungen. Reicht das Budget nicht für alle Mindestleistungen, wird keine unzulässige Teilleistung ausgegeben.
- PV-Messwert = 0 oder unbekannt bedeutet vorsichtshalber kein neuer PV-Betrieb.

**Batterie**
- Läuft vollständig autonom entsprechend der Herstellerkonfiguration.
- Kein SOC-Limit, keine Batteriefreigabe, keine Hybridprobe, keine Berücksichtigung von Entladung/Ladung bei der Zuteilung.
- Batterie-Entities können optional rein informativ in den Experteneinstellungen bleiben; alte Konfigurationsparameter werden nicht mehr als Reglerbedingungen verwendet.

## Technische Sicherheitsgrenzen

Ein Verbraucher-Istsensor ist **nicht notwendig**. Wenn vorhanden, verbessert er die interne Schätzung; ansonsten wird der ausgegebene, auf HA-Schrittweiten abgerundete Gerätesollwert als Schätzwert verwendet. Ein Befehl ist keine physische Leistungsmessung: Die Netzsensor-Rückmeldung bleibt entscheidend.

Das Netzgerät kann kurzzeitig über PMAX liegen, wenn sich nicht regelbare Hauslasten oder die autonome Batterie abrupt ändern oder ein Gerät verzögert reagiert. Die Software ist **keine hardwareseitige Anschlussbegrenzung**. Eine absolute PV-Herkunft bereits laufender Lasten ist ohne Batteriespeicher-/Quellenmessung ebenfalls nicht beweisbar. Netzeinspeisung ist ein belastbares Freigabesignal für **zusätzliche** Lasten.

## Test im Simulator

1. Sicherung der HA-Konfiguration erstellen. Live AUS, keine realen Aktoren anschließen.
2. HACS → Power Manager → erneut herunterladen → Vorabversion `v3.3.5` auswählen, HA neu starten.
3. NORMAL, PMAX 140 kW und gültigen Netzsensor konfigurieren. Die Wärmepumpe bei Netzbezug 122,08 kW mit Last 8,3 kW schrittweise erhöhen lassen, abhängig von ihren min/max-Einstellungen.
4. Einen Test ohne Verbraucher-Istleistungs-Entity durchführen, sowohl mit Batterieentladung als auch bei Batterie 0 kW. Bei identischem Netz-/PV-Zustand muss die Zielverteilung gleich sein.
5. Bei Überschreiten von PMAX sofortige Reduktion prüfen, bei erneuter tatsächlicher Netzreserve zügige Wiederfreigabe. Netzrauschen und Lastsprünge protokollieren.
6. PV-ÜBERSCHUSS: Exporte von 0, 3, 9 und 20 kW, unterschiedliche Verbraucher-Mindestleistungen und mehrere gleichzeitige Verbraucher testen. Bei 0 Export ohne laufende Last darf keine neue Last starten.
7. Auf längeren Simulationsverläufen kontrollieren, dass keine regelmäßigen AUS/EIN-Zyklen auftreten und die 3.3.3-W/kW/A-Geräteausgabe korrekt bleibt.

**GitHub-Draft [PR #8](https://github.com/ww118-rgb/power-manager/pull/8).** Vollständige Simulatorabnahme ist weiterhin erforderlich.
