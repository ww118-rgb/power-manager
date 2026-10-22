# Installation – Power Manager 4.0 (Teststand)

1. Home-Assistant-Konfiguration **sichern**. Vor einem Upgrade Konfiguration, Verbraucher-Entitäten und letzte funktionierende Version dokumentieren.
2. Nur in einer **isolierten Simulator-Instanz** den Entwicklungszweig `refactor/v4.0.0-unified` testen. Dies ist noch keine finale HACS-Freigabe.
3. Home Assistant nach Aktualisierung neu starten. Die Live-Regelung ist aus Sicherheitsgründen zunächst **AUS**.
4. Netzsensor (positiv = Bezug), PMAX und ggf. separate Anschluss-Netzreserve konfigurieren. Beispiel-Simulator: 140 kW. Für den PV-Modus einen **frischen PV-Erzeugungssensor** konfigurieren.
5. Verbraucher einzeln einrichten: Typ, Min/Max, Priorität, Anforderung, optional Istleistungs-Entity und einen **korrekten, bestätigten Geräteausgang**. Bei Wallboxen Phasen/Spannung, erlaubte A/W/kW-Ausgabe, Mindeststrom, Pausecode und Schrittraster prüfen. 0 A kann bei manchen Geräten „unbegrenzt“ bedeuten.
6. Im **Dry-Run** berechnete Ziele, Netzprojektion und alle Geräte-Sicherheitswerte ansehen. Erst danach Live im **Simulator** bewusst aktivieren.
7. Die Szenarien aus [SIMULATOR_TEST.md](SIMULATOR_TEST.md) einschließlich Kurzlastspitzen, PV-Wechsel und sensorlosem Verbraucher abnehmen.

Batterie-Leistung und SOC sind allenfalls optionale Anzeige-Sensoren. Die Batterie bleibt in ihrer Herstellerautomatik. Alte Batterie-Hybrid-Reglereinstellungen sind im neuen 4.0-Dialog nicht mehr verfügbar.

**Sicherheitsgrenze:** Reagiert ein Gerät verzögert oder die Batterie/Haushaltslast schlagartig, kann Software mit 5-s-Netztakten ein **kurzes physikalisches Überziehen** der PMAX-Grenze nicht unmöglich machen. Für eine harte Zusicherung ist zusätzlicher Hardware-/Anlagenschutz nötig.
