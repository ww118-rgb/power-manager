# Changelog

## 3.3.0 – Physische Rückmeldeüberwachung (Teststand)

- Frische Verbraucher-Istleistungsmessung für jeden Lastkanal als Voraussetzung der Live-Aktivierung.
- Reduzierung wird erst nach gemessener tatsächlicher Abnahme als bestätigt angesehen.
- Nicht bestätigte Reduzierung nach gerätespezifischer Einschwingzeit führt zu Fail-Safe und deaktiviert Live.
- Während unbestätigter Reduzierung keine erneuten Erhöhungen; gerätebezogene kW-Toleranz konfigurierbar.
- In einer bestehenden V3.1.1-Konfiguration ohne gültige Last-Istwertsensoren ist Live deshalb zunächst gesperrt. Dies ist nur auf Test-Branch und noch nicht released.

## 3.3.0 – Nachtrag Sicherheit und Nachweisführung

- PMAX konservativ gegenüber wegfallender Batterieentladung auch im NORMAL-Modus.
- Batteriebonus-Wiedereinschalthysterese separat konfigurierbar; PV-only unabhängig vom SOC.
- Unabhängige Timeouts für PV, Batterieleistung und SOC; bei veraltetem SOC nur Batteriebonus sperren.
- Traceability von REQ-01 bis REQ-86 aus Dokument v0.8 mit expliziten offenen Abnahmen und CI-Vollständigkeitsprüfung.

## 3.3.0 (Testkandidat; noch kein öffentlicher Release)

- Konfigurierbare numerische Gerätebefehle mit Skalierung, Offset, sicherer Pause und verbotenen Sonderwerten; bestehender Standard-Ausgang unverändert.
- EVSE-Option `0 = keine Begrenzung` mit sicherer Nullwertprüfung.
- Verfügbaren PV-Überschuss bei laufender autonomer Batterieladung auch bei SOC 0 % über begrenzte Lastversuche nutzen; mindestens erforderliche Verbraucherleistung berücksichtigen.
- Begrenzung eines laufenden Versuchs wird als fester Wert gespeichert, statt bei steigendem Netzbezug dynamisch mitzuwachsen.
- Kompatibler HA-Konfigurationsimport (`voluptuous as probatio`).
- Eigene `brand/`-Icons und Logos zur Integration in Home Assistant 2026.3+.
- Weiterentwicklung ausschließlich im Feature-Branch, ohne Veröffentlichung von `main`.



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
