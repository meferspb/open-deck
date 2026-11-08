# 📚 Open Deck for MSFS Dokumentation

**Languages:** [English](../README.md) · [Русский](../ru/README.md) · [Deutsch](README.md) · [中文](../zh/README.md) · [Español](../es/README.md) · [日本語](../ja/README.md)


<img src="../pic1.jpg" alt="Open Deck for MSFS" width="180" />

Hier sind alle Projektdokumente versammelt. Beginnen Sie mit dem README im
Repository-Stammverzeichnis — es vermittelt das Gesamtbild und einen
Schnellstart; dieser Index hilft Ihnen, die Details zu finden.

## Wo anfangen

| Wenn Sie… | In dieser Reihenfolge lesen |
| --- | --- |
| Pilot sind und das Panel „für sich selbst" einrichten | [README](../../README_DE.md) → [service.md](service.md) |
| verstehen wollen, wie es funktioniert | [architecture.md](architecture.md) → [protocol.md](protocol.md) |
| einen Client oder eine Integration schreiben | [protocol.md](protocol.md) → [telemetry.md](telemetry.md) |
| den Code ändern | [development.md](development.md) → [architecture.md](architecture.md) |
| ein Flugzeugprofil erstellen | [profile-schema.md](profile-schema.md) → [widgets.md](widgets.md) |
| Installer/APK bauen | [packaging.md](packaging.md) → [android.md](android.md) |
| die Sicherheit prüfen | [security.md](security.md) |

## Dokumente

| Dokument | Inhalt | Zielgruppe |
| --- | --- | --- |
| [service.md](service.md) | Vollständige Dienstbeschreibung: Zweck, Betriebsmodell, Telemetrie, Profile, Clients, Netzwerk, Authentifizierung, Assistent, API, Installation, Diagnose, Sicherheit, Lizenz | alle |
| [architecture.md](architecture.md) | Interner Aufbau: Module, Datenflüsse, WASM-Bridge, zentrale Entscheidungen und MVP-Grenzen | Entwickler |
| [protocol.md](protocol.md) | HTTP REST, WebSocket, Passwort- und QR-Anmeldung, Autoerkennung, Fehlercodes und Beispiele | Integratoren |
| [telemetry.md](telemetry.md) | Katalog aller Variablen: Typen, Einheiten, SimVar, Ereignisse, `custom.*` — aus dem Code generiert | Client- und Profilentwickler |
| [widgets.md](widgets.md) | Instrumentenkatalog: erforderliche Bindungen, `command`, Optionen, JSON-Beispiele — aus dem Code generiert | Profilautoren |
| [profile-schema.md](profile-schema.md) | JSON-Profil-Schema: Felder, Layouts, Validierung, Kompatibilität, vollständiges Beispiel | Profilautoren |
| [development.md](development.md) | Wie man den Code ändert: Modulkarte, Hinzufügen von Variable/Instrument/Profil/Provider/Seite, Tests, Release | Mitwirkende |
| [pricing.md](pricing.md) | Vergleich „verbundene Dienste vs. lokale Entsprechungen" für ein air-gapped Szenario | diejenigen, die den Stack wählen |
| [android.md](android.md) | Android-Client: Build, Architektur, Anmeldung, Debugging | Android-Entwickler |
| [packaging.md](packaging.md) | Installer: Inhalt, Build, Verknüpfungen, Deinstallation, stille Flags | Release-Ingenieure |
| [contributing.md](contributing.md) | Wie man mitwirkt: Stil, Tests, Profile, PRs | Mitwirkende |
| [security.md](security.md) | Bedrohungsmodell, was geschützt ist, wie man eine Schwachstelle meldet | alle |
| [changelog.md](changelog.md) | Versionshistorie | alle |

## Screenshots

`docs/screenshots/` — das Panel auf Smartphone und Tablet, Six-Pack, Editor,
Anmeldeseite und Assistent. Wird im README und in der Dienstbeschreibung
verwendet.

## Dokumentation aktuell halten

Zwei Dokumente werden **aus dem Code generiert** und durch einen Test geprüft:

```powershell
python -m msfs_gateway.docsgen --check   # telemetry.md und widgets.md
python -m msfs_gateway.docsgen --write   # nach Änderungen an den Registern aktualisieren
```

Wenn Sie `telemetry.py`, `profiles.py` oder Web-Instrumente geändert haben —
aktualisieren Sie die Dokumentation und führen Sie `pwsh -File scripts/check.ps1`
aus.

## Wie man Dokumentation schreibt

- Schreiben Sie auf Deutsch, in kurzen Absätzen, mit JSON-/Befehlsbeispielen.
- Links sind relativ, damit sie sowohl auf GitHub als auch lokal funktionieren.
- Duplizieren Sie das Schema nicht: Profil — in `profile-schema.md`, Variablen —
  in `telemetry.md`, Instrumente — in `widgets.md`, Netzwerk — in `protocol.md`.
- Wenn Sie das Verhalten ändern, aktualisieren Sie das README/die
  Dienstbeschreibung und `CHANGELOG.md`.
