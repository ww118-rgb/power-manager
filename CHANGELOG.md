# Changelog

## 4.0.0 – in Entwicklung / Simulatorabnahme offen

- Einheitlicher Regler auf Basis des priorisierten 3.1.1-Allocators.
- Netz-PMAX in NORMAL; PV-Einspeisung plus laufende PV-Verbraucher in SURPLUS.
- Gleichverteilung nur bei technisch vergleichbaren Lasten und ohne unbestätigte Netzentlastung vorwegzunehmen.
- Keine Batterie-/SOC-Steuerung, keine Hybrid-Experimente, keine globalen Freigabe-Timer.
- Einzelne Istleistung optional, Netzsensor verpflichtend.
- Gerätesicherheits- und Einheitenkorrekturen sowie neues Home-Assistant-Design aus 3.3.x übernommen.
- Entfernte alte versionsspezifische GitHub-Workflows, veraltete Release-Notizen und Feedback-Sperrklassen.
- Frühere Versionen sind über **Git-Tags/Git-Historie** weiterhin nachvollziehbar.

**Status:** noch keine produktive Freigabe; automatische CI und Simulator-Abnahme erforderlich.
