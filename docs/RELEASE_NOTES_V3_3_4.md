# Power Manager v3.3.4 – netzorientiertes PMAX und stabile Wiederfreigabe

**HACS-Vorabversion für den Energiesimulator. Nicht produktiv freigegeben.** Basis: v3.3.3, V3.1.1 auf `main` unverändert.

## Korrigiertes Verhalten

Bei 140 kW konfigurierter Netzgrenze, 129,56 kW aktuellem Bezug und 10,42 kW autonomer Batterieentladung hatte V3.3.3 nahezu 140 kW als Worst-Case-Projektion angesetzt. Dadurch wurde Verbraucherleistung unnötig eingeschränkt, und bei geringen Änderungen pendelte der Regler. V3.3.4 verwendet im **NORMAL-Modus den aktuellen gemessenen Netzbezug** als entscheidende Regelgröße.

- Die aktuelle Batterieentladung wird nicht mehr generell als verlorene Netzreserve behandelt.
- **Jede Erhöhung** muss in den jetzt gemessenen Netzspielraum abzüglich Puffer passen; nicht bestätigte Lastreduzierungen werden nicht sofort für andere Verbraucher freigegeben.
- Nach einer Stellwertänderung wird eine konfigurierbare Wartezeit bis zur nächsten Erhöhung eingehalten. Reduzieren bei PMAX-Gefahr bleibt jederzeit möglich.
- **Verbraucher-Istleistungssensoren sind optional.** Ohne sie wird der ausgegebene (ggf. auf HA-Stufen abgerundete) Gerätebefehl als vorsichtige interne Schätzung genutzt. Ein solcher Befehl ist kein physischer Istwert. Der Netzleistungssensor bleibt verpflichtend, frisch und gültig.
- Bei gültigen Verbraucher-Istwerten wird die reale Last für die Bilanz benutzt, und eine tatsächliche Reduktion kann kontrolliert werden.

## Konfigurierbare Parameter

Die globalen Experteneinstellungen enthalten:

- `grid_growth_margin_kw`: bei **zusätzlicher** Last freizuhaltender Netz-Puffer. Default 0,3 kW; unabhängig vom 140-kW-Beispiel und für jede Anlage konfigurierbar.
- `grid_recovery_hold_s`: Beruhigungs-/Wartezeit nach jedem Stellbefehl, bevor zusätzliche Leistung erlaubt wird. Default 15 s; für träge Verbraucher gegebenenfalls länger.

PMAX und die bereits existierende separate Netzreserve bleiben weiterhin explizit konfigurierbar. Der neue Freigabepuffer verhindert keine Sicherheitsreduzierung.

## Grenze der Sicherheit

Eine reine Software-Regelung nach dem Netzsensor **kann einen plötzlichen Batteriestrom-Ausfall vor der nächsten Messung nicht abfangen**. Wenn der Speicher beispielsweise 10,42 kW entlädt, kann dieser Anteil beim Ausfall zunächst zusätzlich vom Netz benötigt werden. Für einen physisch garantierten Netzanschlussgrenzwert ist eine geeignete Wechselrichter-/Anlagen-/Hardwareabsicherung oder ein passend eingestellter Netzreservepuffer erforderlich. Auch ohne Istsensor kann ein Gerät auf einen Stellbefehl verzögert oder gar nicht reagieren; den nächsten Netzsensorwert beobachten.

## Installation ausschließlich im Simulator

1. HA-Konfiguration sichern. **Live-Regelung AUS**, reale Verbraucher von der Testanlage trennen.
2. HACS → Power Manager → Menü → Erneut herunterladen → Vorabversion **v3.3.4** auswählen, HA neu starten.
3. Betriebsmodus **NORMAL**, PMAX und separate Netzreserve prüfen. Globale Expertenwerte 0,3 kW Freigabe-Puffer und 15 s Beruhigungszeit sind anpassbar.
4. Erst Dry-Run, danach schrittweiser Simulatorbetrieb. Für mindestens einen Verbraucher die Istleistungs-Entity weglassen und die netzbasierte Zuteilung beobachten.
5. Testdaten: 140 kW Grenze, Netzbezug 129,56 kW, Batterieentladung 10,42 kW, Wärmepumpe 9,6 kW, PV 19,58 kW. Keine periodischen EIN/AUS-Zyklen und sofortige Reduktion bei überschrittener Netzgrenze erwarten.
6. Zusätzlich Batterieentladung abrupt wegfallen lassen und die Netzreaktion einschließlich eines eventuellen kurzzeitigen PMAX-Überlaufs protokollieren.
7. Wiederholt mit wechselnden Netzlasten, langsamen Geräten und anderen Grenzwerten testen. Anleitung: [GRID_FIRST_PMAX_FIX.md](GRID_FIRST_PMAX_FIX.md).

**GitHub-Draft [PR #7](https://github.com/ww118-rgb/power-manager/pull/7); kein Merge nach main vor Abnahme.**
