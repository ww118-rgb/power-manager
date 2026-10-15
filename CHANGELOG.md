# Changelog

## 3.2.0 (ungetestete Hybrid-Funktion vor Live-Abnahme)

- Eigenen PV-Überschuss aus Netz-, Batterie- und Verbraucher-Istleistungen statt pauschal aus PV-Erzeugung berechnen.
- SOC-Reserve sperrt nur Batterieunterstützung, nicht den PV-Überschussmodus.
- Beobachtete Batterieentladung berücksichtigen; unbekannte maximal mögliche Entladeleistung nicht voraussetzen.
- Laufende Batterieladung nicht ungeprüft als sofort für flexible Lasten verfügbar betrachten.
- Optional schrittweise Erhöhung mit Messwertbestätigung, Rücknahme bei Netzbezug und konfigurierbarer Wartezeit; aktive Tests standardmäßig AUS.
- Konservative PMAX-Projektion für den unerwarteten Wegfall der Batterieentladung.
- Frischeprüfung für konfigurierte Batterie-, SOC- und PV-Messwerte im Überschussmodus.
- NORMAL und Prioritätsverteilung bleiben unangetastet.
- Reine Controller-Regressionstests für wechselnde Leistungsbilanzen und konfigurierbare Grenzwerte.


## 3.0.0

- vollständige Home-Assistant-Regelstrecke vom Entity-Eingang bis zum optionalen Live-Ausgang
- beliebig viele Verbraucher über Config Subentries
- modulierbare Lasten, Schaltlasten und EVSE-kW→A-Adapter
- Laufzeitumschaltung Normal / Überschuss
- sicherheitsgesperrte Live-Regelung; nach Neustart standardmäßig AUS
- Validierung aller Aktoren vor Live-Freigabe
- Fail-Safe bei fehlendem, ungültigem oder veraltetem kritischem Netzmesswert
- Aktualitätsüberwachung optionaler Verbraucher-Istleistungsmessungen
- sichere Ausgangszustände bei Fail-Safe oder Aktorfehler
- automatische Live-Deaktivierung und Zustandsreset nach Fail-Safe/Aktorfehler
- Zustandsreset beim Wechsel von Dry-Run zu Live zur Vermeidung alter Schätzwerte
- Lastreduzierungen werden vor Laststeigerungen gesendet
- Diagnose-Entities und Verbraucher-Sollwertsensoren
- Batterie-SOC-Quellskalierung 0…100 % oder 0…1
- strengere EVSE- und Ausgangsvalidierung; keine stille Sollwertbegrenzung
- V1.5-Reglerkern unverändert als getestete kW-Regelbasis eingebettet

## 2.4.0

- kritischer Netzsensor-Timeout und Fail-Safe

## 2.3.0

- Home-Assistant-Diagnose-Sensoren und Binary Sensors

## 2.2.0

- Home-Assistant-Messwert-/Coordinator-Schicht

## 2.0.0

- Home-Assistant-/HACS-Grundgerüst und eingebetteter getesteter Reglerkern
