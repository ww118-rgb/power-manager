# Changelog

## 3.3.6 – Konsolidierte einfache Regelung und verständliche Einrichtung (HACS-Simulator-Vorabversion)

- Identische Netz-/PV-Regelalgorithmen wie V3.3.5, einschließlich Batterieunabhängigkeit, fairer PV-Verteilung, Wegfall globaler Freigabesperren und optionaler Verbraucher-Istwerte.
- Dialogtexte deutsch/englisch vereinheitlicht: Batterie kann optional nur als Diagnose angezeigt werden; keine SOC-/Hybrid-Regelung. Grunddialog auf Netz, PMAX und optional PV reduziert.
- Installationshinweise: `docs/RELEASE_NOTES_V3_3_6.md`. Tests und Simulator-Abnahme erforderlich; keine Freigabe für produktive Netzgrenzgarantien.


## 3.3.5 – Einfaches PMAX und PV-Überschuss ohne Batterie-Regelung (Simulator-Testkandidat)

- NORMAL: Regelgröße ist ausschließlich der frische Netzmesswert am Anschlusspunkt; PMAX, konfigurierbare Netzreserve, tatsächlich gemessene/bei Bedarf geschätzte flexible Verbraucherleistung, Min/Max und Priorität. Keine Batterie-Korrektur, SOC-Hysterese oder Hybridfreigabe.
- PV-ÜBERSCHUSS: zusätzliche Leistung nur aus **tatsächlicher Netzeinspeisung**, bereits laufende flexible PV-Lasten werden berücksichtigt, um Schalten bei Netzeinspeisung 0 kW zu vermeiden. Geeignete PV-Verbraucher werden gleichmäßig innerhalb ihrer Min/Max begrenzt, technische Mindestleistungen gelten weiterhin.
- Keine globale 15-s-Wiederanlaufsperre, keine Erhöhungssperre durch optionale Verbraucher-Istsensoren und keine aktiven Batterieversuche. Erhöhungen sind weiterhin auf aktuelle freie Netzleistung bzw. tatsächliche Netzeinspeisung begrenzt; angeordnete, aber noch nicht vom Netzsensor bestätigte Reduktionen sind nicht sofort neu verteilbar.
- Netzleistungsmessung bleibt Pflicht; Verbraucher-Istwerte bleiben optional. Nach Geräte-Stufen abgerundete kW-Befehle werden für Schätzwerte verwendet.
- Einrichtung zeigt im Grunddialog nur Netzsensor, PMAX und optionalen PV-Sensor; Batterie-Messwerte nur optional als **reine Diagnose** in Experteneinstellungen. Alte Batterie-/Hybrid-Parameter werden für Bestandskonfigurationen toleriert, aber von der Regelung ignoriert.
- Python-Regressionen für 140-kW-Betrieb, andere PMAX-Werte, Batterieunabhängigkeit, Modulation, faire PV-Zuteilung, Startgrenzen und sensorlosen Betrieb.
- **Wichtig:** Ohne physische Quellenmessung lässt sich bei bereits laufenden Lasten nicht beweisen, ob Energie aus PV oder unbemerkt aus der autonomen Batterie stammt; echte Netzeinspeisung ist das einzige sichere Signal für **zusätzliche** PV-Freigabe. Ein plötzlicher Batterieausfall kann vor der nächsten Reaktion PMAX überschreiten. Hardwareseitige Anschlussgrenzsicherung bleibt erforderlich, wenn eine harte Garantie benötigt wird.
- Änderungen nur im Entwicklungszweig; Simulator-/Geräteabnahme weiterhin offen.


## 3.3.4 – Netzorientiertes PMAX und stabile Verbraucherfreigabe ohne Istleistungspflicht (Simulator-Testkandidat)

- NORMAL / Peakshaving regelt nach dem **gemessenen Netzbezug** und der konfigurierten Netzgrenze; die aktuelle Batterieentladung wird nicht mehr pauschal vom verfügbaren Budget abgezogen (Fehlpendeln aus V3.3.3).
- Zusätzliche Verbraucherfreigaben sind durch den **aktuell gemessenen** freien Netzspielraum begrenzt; eine bloß angeordnete Reduzierung anderer Verbraucher gilt nicht sofort als verfügbare Leistung.
- Konfigurierbare Netz-Freigabereserve (Default 0,3 kW) und Beruhigungszeit nach jedem Stellbefehl (Default 15 s) über globale Expertenwerte; nötige Sicherheitsreduktionen bleiben sofort erlaubt.
- Verbraucher-Istleistung ist wieder **optional**; ein frischer Netzsensor bleibt Pflicht. Ein gültiger Istsensor kann die Schätzung und Rückmeldung verbessern, aber fehlende Werte sperren nicht mehr automatisch Live.
- Der Rückkopplungszustand merkt sich bei fehlendem Istsensor den **physikalisch ausgegebenen, auf Geräte-/HA-Stufen abgerundeten** kW-Befehlswert statt des ungerundeten Reglerwunsches. Hersteller-Sondercodes werden nicht als physikalische Leistung geraten.
- Zusätzliche Tests für den 140-kW-Simulatorfall, unterschiedliche Grenzwerte, fluktuierende Netzsensorwerte, PMAX-Sofortreduktion, EVSE-Mindestleistung, Verteilungsverhalten und Ausgangsstufen. Prüfprotokoll: `docs/GRID_FIRST_PMAX_FIX.md`.
- **Grenze:** Ein plötzliches Wegfallen autonomer Batterieentladung kann das reale PMAX vor der nächsten Software-Reaktion überschreiten; harte Netzschutzgarantien brauchen geeignete Hardware-/Anlagengrenzen beziehungsweise eine explizite Netzreserve. Physische Simulatorabnahme weiter offen.


## 3.3.3 – Interne kW-Normalform und korrekte HA-Ausgabeeinheiten (HACS-Vorabversion)

- Einheitenkorrektur für **alle** modulierenden Verbraucher und EVSE: interne kW, Geräteprofil, HA-Entity-eigene W/kW/MW-Einheit, native Grenz- und Schrittweitenprüfung.
- Beispiel Wärmepumpe 5.000 W auf HA-Entity kW → 5; Heizstab 1.000 W → 1; Wallbox 11.000 W → 11.
- Zwischenwert 9,6685 kW auf HA-Entity mit 0,1-Schritten → konservative 9,6 kW, keine unzulässigen Nachkommastellen und keine Aufrundung über PMAX.
- Nach Geräte-Rundung physikalische Mindestleistung (insbesondere EVSE-Minimalstrom) prüfen; sonst sicher pausieren.
- Hersteller-Sondercodes und nicht-nullige sichere Pausenwerte **niemals** eigenmächtig konvertieren oder runden; unsichere Fälle ablehnen.
- Unbekannte Ausgangseinheiten werden nicht aus dem Zahlenbereich geraten. Direkter MQTT-/Modbus-Ausgang folgt weiterhin dem bestätigten Herstellerprofil.
- Regressionen für W/kW/MW und Steps als reine Python-Tests sowie HA-Core-Tests 2026.8 und 2026.10. Physische Simulator-Abnahme bleibt offen.


## 3.3.2 – Eindeutige EVSE-Ausgabe und sichere Rundung (HACS-Testkandidat)

- Wallbox-Energiezuteilung bleibt in kW, Ausgabeformat pro Gerät als A, W, kW oder (bei HA-Zahlen-Entities) automatische Metadaten-Erkennung wählbar.
- Ampere-Schrittweite individuell einstellbar (typisch 1 A), Leistungs-Schrittweite in W einstellbar (typisch 1.000 W); jeweils abwärts begrenzt, niemals unbegründete Leistungsfreigabe oberhalb PMAX.
- Getrennte AUS-/Pausenwerte für Ampere und Watt/kW; Schutz vor 0-A-Vollfreigabe, 0 W nur bei bestätigter Gerätewirkung.
- EVSE-Assistent zeigt nur die für das gewählte Kommandoformat relevanten Felder. Anschlussprotokoll und Einheitenwahl bleiben unabhängig.
- Vorschau im Abschlussdialog prüft HA-Entity-Wertebereich und Schrittweite lesbar, ohne Befehle zu senden.
- Bestehende Konfigurationen ohne neues Formatfeld behalten ihre Ampere-Bedeutung.
- Tests für typische Mennekes 6–16 A und MQTT 0–11.000 W, 1.000-W-Stufen, untere Ladegrenze und sichere PMAX-Rundung.



## 3.3.1 – Einfache Einrichtung (HACS-Testkandidat)

- Globale Grundeinrichtung auf Netz, PMAX, PV, Batterie, SOC und Reserve reduziert; Sensor-Timeouts, Vorzeichen-Sonderfälle und Hybridprüfung über optionalen Expertenweg.
- Verbraucherassistent statt eines 60-Felder-Formulars: Grunddaten, expliziter Bedarf, Anbindung, passende Gerätebefehle, optionale Expertenwerte und Sicherheitsabschluss.
- Verbindungsspezifische Felder: HA-Entity, Modbus-TCP-Registerdaten oder MQTT-Topic statt aller Protokolle gleichzeitig.
- Gerätespezifische Eingaben nur für passende Profile: EVSE-Ladestrom und sichere Pause, lineare Gerätecodes, Schaltcodes oder diskrete Stufen ohne JSON-Handarbeit.
- Eindeutige Bedarfsarten `always`, `sensor`, `disabled`. Keine versteckte 0-kW-Auslegung mehr in der neuen Bedienung; Bestandsinstallationen bleiben kompatibel.
- Physische EVSE-Mindestleistung aus Phasenzahl, Phasenspannung und Mindeststrom berechnet.
- Neuer Gerätebefehls-Vorschautext auf der Abschlussseite (rein rechnerisch; keine Hardwarewirkung bewiesen).
- Bei Neukonfiguration direkter Ausgänge erneute ausdrückliche Sicherheitsbestätigung; Speicherung startet keine Live-Regelung.
- Fehlende Übersetzungsvariable in MQTT-Texten korrigiert und alle Assistentenseiten deutsch/englisch beschriftet.
- CI: Python-Regressionen sowie reale HA-Core-Import-/Einrichtungswege für unterstützte Prüfstände; Simulator-Abnahme steht aus.



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
