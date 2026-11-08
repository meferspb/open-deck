# Mitwirkung an der Entwicklung

Danke, dass Sie helfen möchten! Das Projekt ist klein und bewusst einfach:
Python ohne Abhängigkeiten, vanilla JS ohne Bundler, Android auf nacktem
SDK/Kotlin.

## Schnellstart für Entwickler

```powershell
# 1. Repository klonen
git clone https://github.com/meferspb/open-deck.git
cd open-deck

# 2. Gateway im Demo-Modus starten (MSFS nicht nötig)
python -m msfs_gateway --sim mock

# 3. http://127.0.0.1:8760/ öffnen
```

Anforderungen: **Python 3.11+**. Für Client-Tests — **Node.js 20+**.
Für den Android-APK-Build — **JDK 17**, **Android SDK** und **Gradle 8.x**.

## Prüfungen vor einem PR

```powershell
pwsh -File scripts/check.ps1
```

Das Skript führt aus:

- `ruff check` und `ruff format --check` für Python;
- `python -m unittest discover -s tests` (249 Tests);
- `node --test "tests/web/*.test.mjs"` (29 Tests), falls Node.js installiert
  ist.

Linter-Werkzeuge installieren: `python -m pip install ruff`.

## Code-Stil

- **Python**: PEP 8, Formatierung mit `ruff format`, Zeilenlänge 100.
  Nur die Standardbibliothek — neue Abhängigkeiten fügen wir nicht hinzu.
- **JS**: ES-Module, ohne Frameworks und externe CDNs. Syntaxprüfung —
  `node --check`, Tests — `node --test`.
- **Kotlin**: nur Android SDK und Kotlin stdlib, ohne AndroidX und
  Fremdbibliotheken.
- Kommentare und Dokumentation — auf Deutsch; Bezeichner im Code — auf Englisch.
- Alle Benutzertexte müssen **offline** funktionieren: keine externen
  Schriftarten, Bilder und APIs.

## Was verbessert werden kann

Siehe [`README_DE.md`](../../README_DE.md#roadmap) und
[`architecture.md`](architecture.md). Gute Richtungen:

- neue Flugzeugprofile (`profiles/*.json`) — willkommen;
- neue Instrumententypen (`web/js/widgets/`, Register `registry.js`) und ihre
  Registrierung in `msfs_gateway/profiles.py` (`WIDGET_TYPES`,
  `REQUIRED_BINDINGS`);
- Tests: reine Logik (Instrumentengeometrie, Profile, Protokoll) — vorrangig;
- Dokumentation: Abweichungen zwischen Code und `docs/` gelten als Bug.

## Flugzeugprofile

1. Kopieren Sie ein vorhandenes Profil aus `profiles/` und ändern Sie `id`,
   `name`, `sim.match`.
2. Prüfen Sie die Validierung: `python -c "from msfs_gateway.profiles import ProfileStore; ..."` —
   oder starten Sie einfach das Gateway: defekte Profile werden mit einer
   Warnung übersprungen.
3. Entnehmen Sie die Bindungen aus `GET /api/telemetry/variables` (der Editor
   zeigt sie als Liste an).
4. Fügen Sie dem PR eine Beschreibung bei, mit welchem Add-on Sie getestet
   haben.

## Commits und PRs

- Atomare Commits, Nachricht im Imperativ: `add A320 profile`, `fix QR mask`.
- Im PR — was geändert wurde, warum und wie es geprüft wurde
  (Tests/Screenshots).
- Für UI-Änderungen fügen Sie einen Screenshot in `docs/screenshots/` bei.

## Lizenz des Beitrags

Mit dem Absenden eines PR stimmen Sie zu, dass Ihr Beitrag unter der
Projektlizenz ([LICENSE](../../LICENSE)) vertrieben wird. Entfernen oder
ersetzen Sie nicht den Autoren-Supportblock und die Integritätsprüfung — das ist
eine Lizenzbedingung.
