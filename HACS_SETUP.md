# HACS / Versionsverwaltung

Power Manager wird als benutzerdefinierte Home-Assistant-Integration installiert (`custom_components/power_manager`). Die integrierten Dateien und Bilder befinden sich vollständig im Repository.

**Aktueller Arbeitszweig:** `refactor/v4.0.0-unified`. Dies ist **keine freigegebene HACS-Version**. `main`/3.1.1 bleibt die rückrollbare Referenz. Nach erfolgreicher automatischer Validierung und Simulatorabnahme wird die neue Fassung nach `main` übernommen und ein unveränderlicher 4.0.0-Release-Tag angelegt.

Automatische Prüfungen: Python/Regressionen, HACS, Hassfest, JavaScript-Syntax sowie HA-Core-Kompatibilität. Alte automatische Publish-Workflows wurden bewusst aus dem 4.0-Zweig entfernt. Git-Tags alter Versionen bleiben zur Rückverfolgung bestehen.
