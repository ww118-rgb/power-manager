# Power Manager – Anforderungsverfolgung v0.8 (V3.3.0 RC)

Quellstand: `Power_Manager_Konzept_Anforderungen_Testplan_v0_8.docx` (86 Anforderungen, 106 Prüffälle). Diese Kurzbezeichnungen dienen der Verfolgung; **der genaue Wortlaut in v0.8 bleibt verbindlich**. Jede Codeänderung ist gegen ihn zu prüfen.

**Status:** `Code` = per Quellcode implementierter Aspekt (nicht HA-Live-abgenommen); `Teilweise` = nur Unterfunktion vorhanden; `Offen` = noch nicht umgesetzt; `Extern` = benötigt Release/Hardware/HA-Test.

| ID | Kurzthema | Stand | Nachweis/Lücke |
|---|---|---|---|
| REQ-01 | Anlagengrenzen universell konfigurierbar | Teilweise | Grundgrenzen konfigurierbar; weitere Geräteprofile ausstehend |
| REQ-02 | Batterie standardmäßig autonom | Code | Kein Batterie-Aktor vorhanden |
| REQ-03 | PV-only bei SOC-Reserve | Code | SOC schaltet nur Bonus ab |
| REQ-04 | Batterieladung unter Reserve bleibt möglich | Code | Kein Eingriff in Batterieladung |
| REQ-05 | PMAX inkl. Batterieausfall alle Modi | Teilweise | Konservative Projektion NORMAL/SURPLUS; reale Dynamik ungetestet |
| REQ-06 | Nicht erreichbare Netz-/SOC-Grenzen melden | Teilweise | Netzbudget-Diagnose vorhanden; SOC-Restentladung fehlt |
| REQ-07 | Synchronisierte frische Hybridmesswerte | Teilweise | Timeouts und Istwertpflicht vorhanden, Zeitversatzprüfung fehlt |
| REQ-08 | Echte Gerätelimits bei Testschritten | Teilweise | Min/Max und Startprobe, Stellschritte und Phasenwechsel unvollständig |
| REQ-09 | Keine Batterie-Nennleistungsannahme | Code | Nur Istleistung |
| REQ-10 | Fehlende Sensoren erzeugen kein fiktives Budget | Teilweise | Stale SOC degradiert; Batterie-Power-Sensorfehler führt Fail-safe |
| REQ-11 | Batterie-Aktor optional, separate BMS-Untergrenze | Teilweise | Dokumentiert, keine BMS-Konfiguration im Manager |
| REQ-12 | Sicherer Normalbetrieb ohne Batteriesensor | Code | NORMAL basiert auf Netzsensor und Lastdaten |
| REQ-13 | PV-only unabhängig von SOC | Code | Keine SOC-Sperre des Basisbudgets |
| REQ-14 | PMAX unabhängig von zukünftigem Batteriebonus | Teilweise | Konservative Sollwertprojektion; reale Regellatenz |
| REQ-15 | Bei SOC 0 oder fehlerhaft kein Bonus, PV-only weiter | Code | Entfallender SOC deaktiviert Bonus |
| REQ-16 | Leere Reserve diagnostizieren statt blockieren | Teilweise | Keine separate SOC-Restverletzungsdiagnose |
| REQ-17 | Ladeumverteilung nur mit Rückmeldung | Teilweise | PV-Prüflogik; kein durchgängiger Hardware-Wirknachweis |
| REQ-18 | Bei fehlender Batteriemessung Bilanzlücke kennzeichnen | Teilweise | Fail-safe bei Stale; Diagnose der Bilanzqualität ausbaufähig |
| REQ-19 | Stabile Geräte-Minimum-Proben | Teilweise | Mindestlastprobe; Geräteantwortzeiten unvollständig |
| REQ-20 | SOC-Reserve als variable Bonus-Policy | Code | Hysterese neu konfigurierbar |
| REQ-21 | PV-Lasten vor Batterieladung | Teilweise | Opt-in Umverteilungsprobe, nicht garantiert |
| REQ-22 | PV-only darf SOC nicht voraussetzen | Code | SOC nur Bonus |
| REQ-23 | Batterieladung weder garantiert umleitbar noch Sperre | Teilweise | Messbasierte Versuche; Opt-in und startbedingte Grenzen |
| REQ-24 | Geräte-Minimum, Phasen, Schritt, Antwortzeit | Teilweise | Nicht alle Gerätetypen dynamisch abgedeckt |
| REQ-25 | Erfolg über Verbrauch+Batterie+Netz | Teilweise | Core prüft Leistung und Netz; HA-Physik fehlt |
| REQ-26 | PMAX/Sensorfehler abbrechen und begrenzen | Teilweise | Controller/Fail-safe, externe Aktorwirkung unbestätigt |
| REQ-27 | Prioritäten vor Batterieladung | Teilweise | Allocator priorisiert Lasten; Batterie autonom |
| REQ-28 | Nicht erzwingbare Batterievorränge diagnostizieren | Offen | Fehlerstatus beim Ladeumverteilungsversuch ergänzen |
| REQ-29 | Kein zyklisches Pendeln bei Messrauschen | Teilweise | Hysterese, Zeiten; Langzeittest fehlt |
| REQ-30 | PMAX-Shedding vor Komfortzeiten | Code | Prioritäts-Allocator unverändert |
| REQ-31 | Totzone und stabile Messphase für Zuwachs | Teilweise | Schritte und Wartezeiten; globale Totzone fehlt |
| REQ-32 | Rate/Antwortzeit gerätespezifisch | Teilweise | Last-Settling, Hybridsettling nicht voll gekoppelt |
| REQ-33 | Nur ein koordinierter Ausgangsschreiber | Teilweise | Ein PM-Coordinator; externe HA-Automationen unbekannt |
| REQ-34 | Keine überlappenden Hybrid-Proben | Code | Ein aktiver Probezustand |
| REQ-35 | Retry-Sperre nach misslungener Probe | Code | Konfigurierbarer Cooldown |
| REQ-36 | SOC-Wiedereinschalthysterese nur Bonus | Code | In v3.3.0 ergänzt |
| REQ-37 | Messzeitbezug vor zusätzlichem Budget | Teilweise | Frische; Synchronisationsfenster fehlt |
| REQ-38 | Neustart/Moduswechsel Probe zurücksetzen | Teilweise | Initialisierung; Moduswechsel detailliert testen |
| REQ-39 | Keine Prüfungs-Kennwerte in Reglerkonstanten | Code | PMAX/Leistung und Testparameter sind Variablen |
| REQ-40 | Controller physikalische kW, Adapter getrennt | Code | Outputs-Profil getrennt |
| REQ-41 | Wertbedeutung pro Last konfigurierbar | Teilweise | Gerätesemantik für lineare Werte, Stufen und EVSE konfiguriert; praxisnahe Hardware-Tests fehlen |
| REQ-42 | Pausenbefehl unabhängig von 0 | Code | Konfigurierbarer sicherer Wert |
| REQ-43 | AMTRON-Sonderwerte korrekt | Teilweise | EVSE Pause/0-Guard; Simulator noch nicht getestet |
| REQ-44 | Protokoll und Befehlssemantik unabhängig | Code | Transport (HA-Entity, direkter Modbus TCP, HA-MQTT-Publish) von Wertkodierung getrennt; Geräteprüfung offen |
| REQ-45 | Modbus-TCP Kodierungsparameter | Code | FC06/FC16, Float32/Integer, Register, Unit-ID, Byte-/Wortfolge einstellbar; Simulator-Test offen |
| REQ-46 | Befehlswerte vor Live kontrollieren | Teilweise | Limits/Step/Forbidden; semantisches Hardwareprofil fehlt |
| REQ-47 | Schreibaufruf nicht als Hardware-Beweis | Teilweise | Frischer Istwert nach Reduzierung mit Deadline geprüft; HA-Laufzeitnachweis fehlt |
| REQ-48 | Einheitenrichtige Ausgabe und Rückmeldetoleranz | Teilweise | Ausgabe angepasst; Istwerttoleranz fehlt |
| REQ-49 | Fehlkodierung/Kommunikationsausfall Fail-safe | Teilweise | HA-Servicefehler; Wirkung/Fehlreaktion fehlt |
| REQ-50 | Herstellerneutrale Profile | Teilweise | Linear; keine universellen Code-Tabelle und Protokolle |
| REQ-51 | Getrennte EIN-/AUS-/Freigabe-Codes | Code | Separate numerische EIN/AUS- und MQTT-Textbefehle, optionale Freigabe-Entity; Gerätereaktion prüfen |
| REQ-52 | Transport/Kodierung unabhängig konfigurierbar | Code | Direktes Modbus TCP, MQTT Publish und HA-Entity pro Verbraucher wählbar; laufende Hardwaretests offen |
| REQ-53 | Integrationserkennung nur Vorschlag | Offen | Kein Protokolldetektor / Bestätigungsmaske |
| REQ-54 | Controller ohne vendor-spezifische Register | Code | Regler nutzt physikalische kW |
| REQ-55 | Schalter, stufenlos, Stufen, extra Freigabe | Code | Schaltlast, lineare Modulation, Gerätestufentabelle, EVSE sowie Freigabe-Entity vorhanden |
| REQ-56 | Aus/Pause/Sonderwerte validiert | Teilweise | Ein verbotener Wert; alle Sonderzustände offen |
| REQ-57 | Keine unbeabsichtigte Vollfreigabe | Teilweise | EVSE-Nullschutz; andere Profile brauchen Geräteprüfung |
| REQ-58 | Auflösung/Rundung sicher | Teilweise | HA-Entity Schritt validiert; diskrete Profile fehlen |
| REQ-59 | Modbus-/MQTT-Verbindungsprofile | Teilweise | Modbus/MQTT-Verbindungsprofile programmiert, Encoding getestet, echter Busnachweis offen |
| REQ-60 | Gerätewirkung tatsächlich rückgemeldet | Teilweise | Frischer Verbraucher-Istwert nach Leistungsreduzierung, keine umfassende Freigabe-Bestätigung |
| REQ-61 | Kommunikationsfehler und nicht reagierende Lasten | Teilweise | Servicefehler und nicht bestätigte Reduzierung erzeugen Fail-safe; reale Hardwareprüfung fehlt |
| REQ-62 | Geräteprofile über alle Modi getestet | Teilweise | Konvertierungstests; vollständige Matrix fehlt |
| REQ-63 | Dokumentierte HA-Mindestversion und Testmatrix | Teilweise | CI-Importmatrix für ausgewählte HA-Core-Releases angelegt; Mindestversion noch nicht nachgewiesen |
| REQ-64 | Installation in jeder beworbenen HA-Version | Offen | Nur statische HACS/Hassfest-Prüfung |
| REQ-65 | Importfehler vermeiden | Teilweise | Voluptuous-Fallback; weitere APIs testen |
| REQ-66 | ConfigSubentryFlow Versionen abfangen | Offen | Keine geprüfte API-Kompatibilitätsschicht |
| REQ-67 | Python/HA-Syntax entsprechend Mindestversion | Teilweise | CI Python 3.13; HA-Laufzeiten nicht getestet |
| REQ-68 | HACS/Manifest/Version konsistent | Teilweise | Branch 3.3.0, kein offizieller Release |
| REQ-69 | Neue und bestehende HA-Konfigurationen prüfen | Offen | Mehrere reale HA-Installationen fehlen |
| REQ-70 | Nicht unterstützte HA-Versionen ausweisen | Offen | Mindestversion nach HA-Matrix zu bestimmen |
| REQ-71 | Invalid-handler Traceback nachvollziehen | Offen | Reales Traceback einer betroffenen HA-Instanz benötigt |
| REQ-72 | Upgrade ohne Sicherheitsregression | Teilweise | CI, keine Simulator-Abnahme |
| REQ-73 | Echte HA-Versionstestmatrix | Teilweise | Zusätzlicher HA-Core-Importworkflow vorhanden, echte Test-/Installationsresultate noch offen |
| REQ-74 | HACS-Update nach validiertem Release | Extern | Erst nach GitHub-Release nachweisbar |
| REQ-75 | GitHub-Tag/Manifest/Karte konsistent | Extern | Kein offizieller v3.3.0-Tag oder Release |
| REQ-76 | V3.1.1 main bleibt erhalten | Code | V3.3.0 nur Draft-Branch |
| REQ-77 | Eigene HA-Branding-Assets | Teilweise | Dateien vorhanden, UI-Laufzeittest fehlt |
| REQ-78 | HACS-/HA-Altversionen Fallback | Teilweise | Branding darf Start nicht blockieren, UI nicht getestet |
| REQ-79 | Versions-/Projektmetadaten auffindbar | Teilweise | README/Manifest, Release-Notes noch nicht |
| REQ-80 | Sicherheitsbefehl physisch bestätigen | Teilweise | Tatsächliche Lastreduzierung nach Einschwingzeit geprüft; Geräte-Schaltzustandsbestätigung fehlt |
| REQ-81 | Mehrdeutiger 0-Wert ohne Warnung verhindern | Teilweise | EVSE-Guard/Forbidden; generisches Gerät nicht beweissicher |
| REQ-82 | Winter-SOC 0 mit echtem PV | Teilweise | Core-Tests, realer HA-Prozess fehlt |
| REQ-83 | Fehlversuch erzeugt keine Oszillation | Teilweise | Cooldown, Langzeittest fehlt |
| REQ-84 | PMAX auch ohne Batterie effektiv | Teilweise | Controllerbudget, physische Aktorwirkung nicht garantiert |
| REQ-85 | Sicheres V3.1.1-Upgrade und Rollback | Teilweise | Live default AUS, Rollback-Prozedur offen |
| REQ-86 | Implementierungs-/Test-/Simulator-Statusliste | Code | Dieses Traceability-Dokument |

## Freigabegates und nicht automatisierbare Nachweise

- **Keine automatische Freigabe:** Kein Release, Merge nach `main` oder produktives Einschalten wird durch dieses Dokument ausgelöst.
- **Hardware-/Simulator-Tests:** REQ-43, 47–49, 60–61, 80–81 sowie alle Testfälle mit realen Aktoren benötigen nachweisbare Geräteantworten. Die GitHub-CI kann nur Python- und statische Prüfungen leisten.
- **Protokolle:** Direkte MQTT- und Modbus-Befehle, Registerkodierung und diskrete Gerätecode-Profile bleiben offen. Keine Hardwarefunktion darf ohne verifizierten Aus-/Pausebefehl als PMAX-sicher gelten.
- **HA-Matrix:** Eine Mindest-HA-Version wird erst nach echten Einrichtungstests zugesichert. Die Aussage „alle Home-Assistant-Versionen“ ist nicht erfüllbar.
- **Batterie:** Der Speicher bleibt autonom. Ohne Aktor ist seine gesamte Entladung und das Halten einer SOC-Untergrenze nicht garantierbar. PMAX-Prognosen dürfen die Batterie nicht voraussetzen.
- **Langzeitstabilität:** Unter wechselnder Last, PV, SOC und Kommunikation sind Stellwert- und Schaltzahlen zu protokollieren, bevor V4.0.0 veröffentlicht wird.
- **Release-HACS:** HACS-Updateanzeige, Versions-Tags, Icon-Anzeige im UI und Migration/Upgrade können erst bei kontrollierter Freigabe und HA-Laufzeittests als geprüft gelten.

## Prüffälle aus v0.8

Das Original definiert **T01–T106**. Eine separate Ausführung eines namensähnlichen Python-Tests beweist nicht automatisch den Abnahmefall. Der prüfpflichtige Testfall bleibt offen, bis Testaufbau, erwartete und beobachtete Werte sowie Protokoll dokumentiert wurden.
