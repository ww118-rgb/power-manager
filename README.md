# Power Manager for Home Assistant

Power Manager ist eine generische Home-Assistant-Integration für ein zentrales Energiemanagement. Sie verbindet vorhandene Home-Assistant-Entities mit einem getesteten Reglerkern und kann damit Peakshaving, PV-Überschussbetrieb und priorisierte Verbrauchersteuerung abbilden.

**Aktueller offizieller Stand: V3.1.1 (main) – V3.3.0 ist ein nicht freigegebener Testkandidat im Feature-Branch.**

## Offene Anforderungen und Abnahme

Der aktuelle Status **aller 86 Anforderungen aus dem gemeinsamen Pflichtenheft v0.8**
ist unter [docs/anforderungen_v0_8_traceability.md](docs/anforderungen_v0_8_traceability.md)
nachverfolgbar. Der Branch bleibt bis zu tatsächlichen HA- und Simulatorprüfungen ein **Draft**.

**Aktuelle Sicherheitsnachträge:**

- **Physische Reduktionsbestätigung:** Live-Regelung lässt sich im neuen Teststand nur mit einer gültigen eigenen Istleistungs-Entity für jeden Verbraucher aktivieren. Nach einer Leistungsreduzierung wird die gemessene Leistung innerhalb einer gerätespezifischen Einschwingzeit mit dem neuen Sollwert (plus konfigurierbarer Rückmeldetoleranz) verglichen. Fehlt die Bestätigung, erfolgt Fail-Safe und Live wird deaktiviert. Solange eine Reduktion unbestätigt ist, werden keine neuen Leistungssteigerungen freigegeben. Ein bloßer `number.set_value`-Erfolg gilt nicht als Wirknachweis.
- **Bestehende V3.1.1-Anlagen:** Diese Live-Voraussetzung kann bisherige Konfigurationen ohne Verbraucher-Istwertsensor absichtlich blockieren. Vor einem Testlauf müssen entsprechende Sensoren korrekt eingebunden und auf Frische geprüft werden. Das ist ein bewusster Sicherheitsstopp, keine automatische Änderung am installierten System.
- Die PMAX-Sollwertprognose rechnet nun auch im NORMAL-Modus konservativ mit einem möglichen Wegfall der Batterieentladung.
- Die Batterie-Bonusfreigabe besitzt eine eigene konfigurierbare SOC-Wiedereinschalthysterese.
- PV-, Batterie-Leistungs- und SOC-Messwerte haben getrennte konfigurierbare Frischegrenzen.
- Ein veralteter SOC-Sensor schaltet nur den Batteriebonus ab, **nicht** den reinen PV-Überschussbetrieb. Ein ungültiger konfigurierter Batterie-Leistungssensor verhindert weiterhin eine unsichere PV-Bilanz.

**Noch offen für die vollständige Abnahme:** reale Geräte-Wirkbestätigung, echte Modbus-/MQTT-Simulatorläufe, vollständige HA-Core-Versionstests und lange Anlagen-Stabilitätstests. Die Transportprofile, Geräte-Stufentabellen und ersten Stabilitätsregressionen sind inzwischen programmiert.

## Neu im V3.3.0-Testkandidaten

- **Sichere Gerätecode-Übersetzung:** Neben gewöhnlichen W/kW/MW-Ausgängen kann ein modulierender Verbraucher jetzt eine lineare kW-zu-Gerätewert-Umrechnung (Skalierung/Offset) und einen frei definierbaren gefährlichen/verbotenen Gerätewert erhalten. Aus/Pause wird über den separat konfigurierten sicheren Ausgangswert definiert.
- **EVSE-Sonderwertschutz:** Ein Wallbox-Profil kann explizit angeben, dass 0 A die Begrenzung aufhebt. Dann wird ein 0-A-Pausenbefehl vor dem Livebetrieb abgewiesen. Für Geräte mit tatsächlich sicherem 0-A-Aus-Kommando lässt sich diese Eigenschaft abwählen.
- **Batterie-Ladungsumverteilung:** Wenn eine Batterie autonom PV-Überschuss lädt, darf der Regler mit aktiviertem Hybrid-Prüfschritt eine begrenzte, messwertgeprüfte Lastfreigabe auch bei 0 % SOC versuchen – unter Beachtung von Geräte-Mindestleistung und PMAX. Eine tatsächlich verringerte Ladung ist nicht garantiert.
- **HA-Kompatibilitätsverbesserung:** Der Einrichtungsdialog nutzt jetzt den mit älteren und neuen Home-Assistant-Versionen kompatiblen Import `voluptuous as probatio`.
- **Professionelles Branding:** Lokale Icons und Logo in `custom_components/power_manager/brand/` (ab HA 2026.3). HACS-Ansicht älterer Versionen kann abweichen.
- **Versionsstrategie:** HACS stellt Update-Entitäten bereit. Ein Update für allgemeine Nutzer erscheint erst nach einem kontrollierten GitHub-Release bzw. bei unversionierter Branch-Installation nach einer Änderung des Default-Branches.

**Funktionen dieser Testversion:** Home-Assistant-Entity, direktes Modbus TCP (FC06/FC16, Float32/Integer, Wort-/Bytefolge), MQTT-Publish (numerisch sowie separate Textbefehle für Schaltlasten), positive lineare Skalierung, diskrete Gerätestufen und konfigurierbarer Pausenwert. Für direkte Gerätebefehle ist eine explizite Bestätigung der Werte erforderlich. Leistungsreduzierungen erfordern frische physische Istleistungsrückmeldungen. Ein erfolgreicher Modbus-Schreib-ACK oder MQTT-Publish ist keine garantierte physische Wirkung.

**Noch nicht nachgewiesen:** reale Home-Assistant-Laufzeit über eine breite Core-Matrix und Simulator-Abnahme. Aktive Hybrid-Lastproben sind opt-in (Standard-Prüfschritt 0 kW). Bitte nicht ungeprüft an produktiven Netzanschlüssen einsetzen.

## Warum neue Updates nicht automatisch sofort angezeigt werden

Ohne GitHub-Release nutzt HACS den Default-Branch. Für reguläre, verständliche Versionsupdates sollen nach bestandener Freigabe GitHub-Releases mit Tag `vX.Y.Z`, derselben `manifest.json`-Version und vollständigen Release Notes veröffentlicht werden. HACS/HA zeigt danach die neue Version in der vorhandenen Update-Entität; eine automatische Installation wird nicht erzwungen. Test-Branches werden nicht automatisch verteilt.

## Neu in V3.2.0: rückgekoppelter Hybrid-Überschuss

Im Überschussmodus wird die tatsächlich nach der ungeregelten Hauslast verfügbare PV-Leistung aus der Bilanz der Netz-, Batterie- und geregelten Verbraucher-Istwerte bestimmt. Die Batterie kann oberhalb der konfigurierten SOC-Reserve unterstützen, aber nur soweit ihre Entladung beobachtbar ist; bei Erreichen der Reserve bleibt reiner PV-Überschussbetrieb aktiv. Die Batterie wird nicht selbst angesteuert.

**Sicherheitsverhalten:** Zusätzlich zu PMAX wird im Überschussmodus konservativ mit einem möglichen Wegfall der aktuellen Batterieentladung gerechnet. Vorübergehender Netzbezug durch unerwartete Anlagenänderungen oder Kommunikationsverzögerung kann softwareseitig nicht vollständig ausgeschlossen werden. Der NORMAL-Modus und der bestehende Prioritäts-Allocator werden nicht verändert.

**Aktives Austesten ist zunächst standardmäßig AUS (Prüfschritt = 0 kW).** Nur nach bewusster Konfiguration eines positiven Prüfschritts und Aktivierung der Live-Regelung darf der Regler zusätzliche Verbraucherleistung testen. Er wertet nach der einstellbaren Einschwingzeit die tatsächlich gemessene Verbraucherleistung und den Netzbezug aus; fehlgeschlagene Schritte werden zurückgenommen und vor weiteren Versuchen gewartet. Prüfschritt, Einschwingzeit, Wiederholverzögerung und zulässiger kurzzeitiger Netzbezug sind frei einstellbar. Eine Batterie-Nennleistung wird nicht angenommen.

Benötigt für Batterieunterstützung: Batterieleistungssensor, SOC-Sensor und konfigurierbare Reserve-SOC-Grenze. Für aktive Tests müssen die geregelten Verbraucher eigene aktuelle Istleistungsmessungen besitzen. Die zyklischen MQTT-Sensoren benötigen korrekt erneuerte Zeitstempel (`force_update: true` bei entsprechenden MQTT-Sensoren).

**Vor Live-Test:** Zuerst neue Version installieren, Config-Flow-Werte kontrollieren und mit abgeschalteter Live-Regelung prüfen. Tests mit begrenzten Stellwerten beginnen und den Netzbezug unabhängig überwachen. Ein direkter Batterie-Aktor ist weiterhin nicht Bestandteil dieser Änderung.



## Neu in V3.1.1: responsive Power Manager Dashboard Card

V3.1.1 verbessert die in V3.1.0 eingeführte Home-Assistant-Dashboard-Karte. Das Layout richtet sich jetzt nach der tatsächlichen Kartenbreite statt nach der Browserbreite und bleibt damit auch in schmalen Sections lesbar. Zusätzlich werden Summenwerte bei Bedarf aus den Verbraucher-Sollwerten abgeleitet, falls ein globaler Aggregat-Sensor kurzfristig nicht verfügbar ist. Die Regellogik bleibt unverändert.

Die Karte wird zusammen mit der HACS-Integration installiert und von Power Manager automatisch als Frontend-Modul bereitgestellt. Sie erkennt die Power-Manager-Entities über die Home-Assistant-Entity-Registry und benötigt deshalb keine fest codierten Entity-IDs.

Angezeigt werden unter anderem:

- Betriebsart **Normal / Überschuss**
- sichere Live-Regelungs-Freigabe
- Netzleistung, PV-Leistung, Batterieleistung und Batterie-SOC
- effektives PMAX und verbleibender Headroom
- Basislast und verfügbares Regelbudget
- Energieflussübersicht
- alle konfigurierten regelbaren Verbraucher
- je Verbraucher: Priorität, Istleistung, Sollleistung, Anforderung, Verfügbarkeit sowie Peak-/PV-Freigabe
- aktive und begrenzte Verbraucher
- Netzmessungsstatus, Messwertalter, Ausgangspfad und Fail-Safe

Beim Aktivieren der Live-Regelung sowie bei einem Betriebsartwechsel während aktiver Live-Regelung fordert die Karte eine zusätzliche Bestätigung an.


## Grundprinzip

Der Reglerkern rechnet ausschließlich in kW. Messdaten kommen weiterhin aus Home-Assistant-Entities. Für Schreibbefehle an Verbraucher unterstützt der Teststand sowohl vorhandene HA-Ausgangs-Entities als auch direkt konfiguriertes Modbus TCP und MQTT Publish. Die Bedeutung der Codes wird durch das Verbraucher-Geräteprofil festgelegt, nicht durch das Übertragungsprotokoll. Bei direkter Geräteansteuerung muss die physikalische Wirksamkeit vor dem Livebetrieb nachgewiesen werden.

```text
Messgeräte / Geräte
        │
        │ MQTT / Modbus / Herstellerintegration
        ▼
Home-Assistant-Entities
        │
        ▼
Power Manager
  ├─ Messwertadapter
  ├─ zentraler Reglerkern
  └─ Ausgangsadapter
        │
        ▼
number / input_number / switch / input_boolean
```

Dadurch bleibt die Regelstrategie unabhängig von einem bestimmten Hersteller, Protokoll, Leistungsbereich oder einer bestimmten Anlage.

## Funktionen von V3.0

- konfigurierbares PMAX und zusätzliche Netz-Sicherheitsreserve
- positive Netzleistung = Bezug, negative Netzleistung = Einspeisung
- Normalbetrieb mit Peakshaving
- PV-Überschussbetrieb mit PV-Leistung als priorisiertem Verbraucherbudget
- Batterie-Reserve-SOC mit automatischer Rückkehr von Überschuss auf Normal
- beliebig viele Verbraucher als Home-Assistant-Config-Subentries
- Prioritäten; `1` ist die höchste Priorität
- dynamische Mindest- und Maximalleistung
- dynamische Start-/Stop-Margen
- Mindest-Ein-/Ausschaltzeit und Einschwingzeit
- Lasttypen:
  - modulierbare Leistung
  - Schaltlast
  - EVSE/Wallbox mit Umrechnung kW → A
- optionaler Istleistungssensor je Verbraucher
- optionaler Anforderungs- und Verfügbarkeitseingang
- frei konfigurierbare Home-Assistant-Ausgänge
- Dry-Run und explizite Live-Freigabe
- Diagnose-Sensoren für Budgets, PMAX, Sollwerte, Fail-Safe und Ausgangszustand
- kritische Aktualitätsüberwachung des Netzleistungsmesswerts
- Aktualitätsüberwachung optionaler Istleistungsmesswerte
- Fail-Safe mit sicherem Ausgangszustand
- automatische Deaktivierung der Live-Regelung nach einem Fail-Safe oder Ausgangsfehler
- Ausgangsbefehle werden nur bei tatsächlicher Wertänderung gesendet
- Lastreduzierungen werden vor Laststeigerungen ausgeführt

## Überschussbetrieb ab V3.0.6

Im Modus **Überschuss** bildet die gemessene PV-Leistung das Rohbudget für die als Überschussverbraucher freigegebenen Lasten. Die Leistung wird anschließend nach den konfigurierten Prioritäten verteilt; `1` ist die höchste Priorität. Batterieentladung erweitert dieses PV-Budget nicht.

Eine bereits laufende Batterieladung wird im Überschussbetrieb nicht mehr als zu erhaltende Last reserviert. Dadurch können priorisierte Verbraucher diese PV-Leistung übernehmen. Für die PMAX-Projektion wird die aktuell gemessene Batterieleistung im Überschussbetrieb aus der Basislast herausgerechnet, sodass weder eine laufende Ladung künstlich festgehalten noch eine aktuelle Entladung als dauerhafte PMAX-Stütze vorausgesetzt wird.

Ist ein Batterie-Reserve-SOC konfiguriert, bleibt Überschuss nur aktiv, solange der SOC **oberhalb** dieser Grenze liegt. Bei Erreichen oder Unterschreiten der Grenze wechselt die Home-Assistant-Integration automatisch auf **Normal** zurück. Das ist kein Fail-Safe, sondern die konfigurierte Betriebsstrategie.

Wichtig: Seit V3.0.6 steuert Power Manager keinen Batterie-Wechselrichter direkt. Sie reserviert im Überschussbetrieb keine Batterieladung und weist vorhandene PV-Leistung zuerst den freigegebenen Verbrauchern zu. Reicht deren Anforderung nicht aus, kann eine externe/automatische Batterieregelung verbleibende PV-Leistung weiterhin laden. Ein hartes Ladeverbot benötigt einen separat regelbaren Batterieaktor.

## Sicherheitsprinzip

Die konfigurierte Netzgrenze hat höchste Priorität.

```text
1. kritischer Messwert / Fail-Safe
2. PMAX minus Sicherheitsreserve
3. technische Min-/Max-Grenzen
4. Prioritäten
5. Hysterese, Mindestzeiten und Komfort
```

Hysterese, Mindestlaufzeit, Mindestauszeit und Einschwingzeit dürfen den Regler nicht dazu veranlassen, absichtlich ein Leistungsbudget oberhalb von PMAX freizugeben. Wenn bereits die nicht regelbare Basislast oberhalb der Netzgrenze liegt, meldet der Regler `grid_limit_unachievable`.

### Fail-Safe

Der Netzleistungsmesswert ist kritisch. Ist er `unknown`, `unavailable`, ungültig oder älter als der konfigurierte Timeout, wird kein normaler Regelzyklus ausgeführt. War Live-Regelung aktiv, werden die konfigurierten sicheren Ausgangszustände bestmöglich gesetzt, die Live-Regelung wird deaktiviert und der interne Laufzeitzustand verworfen. Eine erneute Live-Freigabe muss danach bewusst erfolgen.

Auch bei einem Ausgangsfehler werden alle Ausgänge bestmöglich in ihren sicheren Zustand gefahren und Live-Regelung wird deaktiviert.

### Physikalische Grenze der Softwaregarantie

Power Manager kann garantieren, dass seine **berechneten und angeforderten** Sollwerte das verfügbare PMAX-Budget nicht absichtlich überschreiten. Reale Geräte und Netzwerke können Befehle jedoch verzögert, fehlerhaft oder gar nicht umsetzen. Für belastbares Peakshaving wird deshalb für jeden live geregelten Verbraucher ein echter Istleistungssensor dringend empfohlen. Ohne Istwert muss der Regler den vorherigen Sollwert als Schätzung verwenden.

## Dry-Run und Live-Regelung

Nach jedem Neustart bzw. Reload ist die Live-Regelung **AUS**. Der Regler berechnet trotzdem alle Sollwerte und Diagnosewerte, schreibt aber nichts auf Geräte.

Vor dem Einschalten der Live-Regelung validiert die Integration alle konfigurierten Ausgänge. Dry-Run-Zielwerte werden beim Übergang zu Live nicht als physisch bereits umgesetzte Leistungen übernommen; der Laufzeitzustand wird für den ersten Live-Zyklus zurückgesetzt.

Empfohlene Inbetriebnahme:

1. Messwerte prüfen.
2. Verbraucher hinzufügen.
3. Dry-Run beobachten.
4. Ist-Netzleistung, berechnete Sollwerte und PMAX vergleichen.
5. Zunächst nur einen Verbraucher live testen.
6. Erst danach weitere Verbraucher freigeben.

## Verbraucherarten

### Modulierbare Leistung

Für Verbraucher mit einem numerischen Sollwert. Unterstützte Ausgangs-Entities sind `number` und `input_number`. Die Einheit kann automatisch aus der Entity gelesen oder explizit auf W, kW oder MW festgelegt werden.

### Schaltlast

Für reine Ein/Aus-Verbraucher. Unterstützte Ausgänge sind `switch` und `input_boolean`. Die konfigurierte Maximalleistung ist gleichzeitig die technische Mindestleistung.

### EVSE / Wallbox

Der Regler arbeitet weiter in kW. Der Adapter rechnet den kW-Sollwert mit konfigurierbarer Phasenzahl und Spannung in Ampere um.

```text
I = P * 1000 / (Phasen * Spannung)
```

Mindeststrom, Maximalstrom und Pausenstrom sind frei konfigurierbar. Ein Ziel unterhalb des technischen Mindeststroms wird **nicht nach oben gerundet**, sondern als Pause ausgegeben. Ein Ziel oberhalb der konfigurierten Stromgrenze führt zu einem Fehler und damit zum Fail-Safe statt zu einer stillen Begrenzung.

Hinweis für Simulatoren: Wenn deren MQTT-Schnittstelle direkt einen Leistungs-Sollwert in kW erwartet, sollte die Wallbox dort als **modulierbare Leistung** konfiguriert werden. Der EVSE-Modus ist für eine HA-Entity gedacht, die tatsächlich einen Stromwert in A erwartet.

## Messwerte und Vorzeichen

Intern gelten:

- Netz: positiv = Bezug, negativ = Einspeisung
- Batterie: positiv = Entladen, negativ = Laden
- Verbraucher-Istleistung: nichtnegativ
- Batterie-SOC intern: 0…100 %

Vorzeichen von Netz, PV, Batterie und Verbraucher-Istwert können bei Bedarf über die Konfiguration angepasst werden. Für den Batterie-SOC kann gewählt werden, ob die Quell-Entity Prozent (`0…100`) oder einen Bruchteil (`0…1`) liefert.

## Keine anlagenspezifischen Konstanten im Reglerkern

PMAX, Netzreserve, Leistungen, Prioritäten, Hysterese, Zeitparameter, Wallbox-Spannung/-Phasen/-Ströme und Sensor-Timeouts sind Konfigurationswerte. Der Reglerkern enthält keine Leistungswerte einer konkreten Prüfungs- oder Simulatoranlage.


## Installation über HACS als Custom Repository

Dieses Repository ist für die Installation als HACS Custom Repository vorbereitet.

Nach dem Veröffentlichen auf GitHub:

1. In HACS oben rechts das Menü öffnen.
2. **Custom repositories** wählen.
3. `https://github.com/ww118-rgb/power-manager` eintragen.
4. Kategorie **Integration** wählen.
5. Repository hinzufügen und **Power Manager** installieren.
6. Home Assistant vollständig neu starten.
7. Unter **Einstellungen → Geräte & Dienste → Integration hinzufügen** den **Power Manager** einrichten.

Vor dem ersten Push muss einmal `prepare_hacs_repo.py` ausgeführt werden, damit GitHub-Benutzername und Repository-URL korrekt in `manifest.json` eingetragen werden.

## Dashboard Card verwenden

Nach Installation bzw. Update auf V3.1.0 und einem vollständigen Home-Assistant-Neustart:

1. Dashboard öffnen und **Bearbeiten** wählen.
2. **Karte hinzufügen** wählen.
3. Nach **Power Manager** suchen.
4. Die Community-Karte **Power Manager** auswählen.
5. Speichern.

Alternativ kann sie im YAML-Modus mit folgendem Minimalblock verwendet werden:

```yaml
type: custom:power-manager-card
```

Die Karte benötigt keine manuelle Zuordnung der Power-Manager-Entities. Sie liest die zur Integration gehörenden Entities automatisch aus der Entity Registry.

## Installation

Siehe [INSTALLATION.md](INSTALLATION.md).

Für den vorhandenen Energiedaten-Simulator siehe [SIMULATOR_TEST.md](SIMULATOR_TEST.md).

## Tests

Die reine Regelungs-, Konvertierungs- und Paketlogik wird mit `pytest` getestet.

```powershell
pytest -v
```

Der V3.0-Stand enthält außerdem Paritätstests zwischen dem Referenz-Reglerkern und der im Home-Assistant-Paket eingebetteten Version.

## Projektstatus

V3.0 ist als vollständiger Test- und Inbetriebnahmestand für Home Assistant aufgebaut. Die reinen Python-Tests prüfen den Reglerkern und die protokollunabhängigen Adapter. Die endgültige Home-Assistant-Laufzeitprüfung der Config-Subentries, Entities und Service-Aufrufe erfolgt auf einer realen Home-Assistant-Instanz, bevor Live-Regelung an einer realen Anlage verwendet wird.
