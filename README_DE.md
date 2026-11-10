# ✈️ Open Deck for MSFS

**Languages:** [English](README.md) · [Русский](README_RU.md) · [Deutsch](README_DE.md) · [中文](README_ZH.md) · [Español](README_ES.md) · [日本語](README_JA.md)


<img src="docs/pic1.jpg" alt="Open Deck for MSFS" width="220" />

**MSFS-2020/2024-Instrumententafeln auf Smartphone und Tablet — über das lokale
Netzwerk, ohne Internet.**

Ein Windows-Gateway liest Telemetrie aus Microsoft Flight Simulator über
SimConnect (einschließlich LVAR/RPN über ein WASM-Modul) und stellt sie
Web-Clients und einer Android-App über HTTP + WebSocket bereit. Panels werden
durch JSON-Profile pro Flugzeug beschrieben und für drei Formfaktoren gerendert.

Das Projekt ist vollständig eigenständig: **kein externes CDN, keine externen
Schriftarten, kein externer Dienst** — alles funktioniert in einem isolierten
Netzwerk und auf einem Rechner ohne Internetzugang.

| | |
| --- | --- |
| Version | 0.1.0 |
| Tests | 252 Python + 41 Node.js |
| Host-Plattform | Windows 10/11 (Python 3.11+ oder Installer) |
| Clients | Browser (jeder moderne), Android 8+ |
| Autor | Viktor Krasnikov — [github.com/meferspb/open-deck](https://github.com/meferspb/open-deck) |
| Donat | [https://taps.uz/open_deck_fs](https://taps.uz/open_deck_fs) |
| Lizenz | [GNU AGPL-3.0](LICENSE) — freie Software mit verpflichtendem Autoren-Supportblock (Abschnitt 7) |

## Screenshots

| Smartphone | Großes Tablet |
| --- | --- |
| ![Panel auf einem Smartphone](docs/screenshots/phone.png) | ![Panel auf einem Tablet](docs/screenshots/tablet-lg.png) |

| Klassischer C172 Six-Pack | Panel-Editor |
| --- | --- |
| ![Six-Pack](docs/screenshots/sixpack-phone.png) | ![Editor](docs/screenshots/editor.png) |

![Passwortanmeldung vom Smartphone](docs/screenshots/login.png)

![Lande- und Roll-Assistent](docs/screenshots/assist.png)

## Funktionen

### Gateway

- **Ein Port** für statische Dateien, REST und WebSocket — eine einzige
  Firewall-Regel genügt; nur Python-Standardbibliothek, kein `pip install`.
- **Austauschbare Telemetriequelle**:
  - `simconnect` — natives SimConnect über `ctypes`;
  - `mock` — ein prozeduraler „Flug" ohne Simulator (Demo und Tests);
  - `auto` — SimConnect mit Rückfall auf Mock bei Fehlschlag.
- **Automatische Flugzeugerkennung**: Das Profil deklariert `sim.match.title`
  und `atcModel`, das Gateway liest `TITLE`/`ATC MODEL` und wechselt das Panel
  automatisch.
- **LVAR/RPN über WASM** (MobiFlight/SimBridge): Client Data Area, ein
  synchroner Kanal mit Timeouts, LVAR-Schreibzugriffe über RPN.
- **Host-Autoerkennung** über UDP-Beacon (für native Clients), ein integrierter
  HTTP-Server, JSON-API und strikte Validierung von Profilen und Befehlen.

### Profile und Instrumente

- **6 Profile**: Cessna 172S, Cessna 172 Classic Six-Pack, Daher TBM 930,
  Airbus A320, Piper PA-28-181, LVAR-Demo.
- **Instrumente**: Künstlicher Horizont, Rundskalen, Digitalanzeigen,
  Kippschalter, Drehschalter (Gesten/Mausrad), Warnleuchten, Variometer,
  Dreizeiger-Höhenmesser, Kursanzeiger mit „Bug".
- Layout in Panel-Bruchteilen + Überschreibungen `layout.phone`,
  `layout.tablet-sm`, `layout.tablet-lg`; Schema und Validierung —
  [`docs/de/profile-schema.md`](docs/de/profile-schema.md).

### Clients

- **Web-Client** auf reinen ES-Modulen: flüssige Animation (rAF), Glättung,
  Gesten, Befehls-Widgets, Wiederverbindung.
- **Drei Formfaktoren** mit automatischer Auswahl nach Bildschirmbreite.
- **Cockpit-Komfort**: Panel-Helligkeit 100/72/45 % (Taste `B`) und ein
  Kiosk-Modus ohne UI (`F`, Beenden mit `Esc`).
- **Telefonverbindung per QR**: Die Panel-Seite zeigt einen QR-Code für die
  Host-Adresse und eine Liste der Netzwerkadressen.
- **Android-Client**: WebView-Panel, UDP-Host-Erkennung, Integritätsprüfung,
  ein Verbindungsbildschirm mit manueller Adresseingabe.

### Sicherheit

- **Passwortanmeldung** (mindestens 6 Zeichen): PBKDF2-Hash, Sitzungen in einem
  `HttpOnly`-Cookie, Bearer-Token für native Clients, Versuchsbegrenzung,
  QR-Anmeldung vom Smartphone ohne Passworteingabe. Ein einmaliges QR-Token ist
  nur über `/?pair=` gültig und wird nicht als reguläre Sitzung akzeptiert.
- **Same-Origin- und Host-Schutz**: Browser-POST/PUT- und WebSocket-Anfragen
  mit fremdem `Origin` sowie Anfragen mit unbekanntem `Host` werden abgewiesen
  (`403`). Das schließt CSRF, Cross-Site-WebSocket-Hijacking und DNS-Rebinding;
  Clients ohne `Origin` (Android, curl) funktionieren wie bisher.
- Nur die Anmeldeseite, Health-/Integritätsprüfungen und der Autoren-Supportblock
  sind öffentlich zugänglich — alles andere (Profile, Telemetrie, Befehle,
  APK-Build) ist geschlossen.

### Lande- und Roll-Assistent

- **Roll-Assistent**: Halten einer Zielgeschwindigkeit (3–25 kt) und eines
  Kurses — das Gateway berechnet Schub und Seitenruder; „STOP" liefert
  Nullschub und die Parkbremse.
- **Lande-Assistent**: ARM aktiviert AP und APR, bei 60–15 ft reduziert der
  Assistent den Schub sanft, und bei der Landung koppelt er den Autopiloten ab;
  TOGA — Durchstarten.
- Seite `/assist.html` (die Schaltfläche „Assistent" in der Panel-Kopfzeile);
  sie funktioniert auch auf dem Smartphone. Der Assistent ist eine Hilfsregelung;
  die Kontrolle über den Flug behält der Pilot.

### Werkzeuge

- **Panel-Editor** `/editor.html`: Drag-and-drop, Größenänderung, 1-%-Raster-
  Einrasten, Rückgängig/Wiederholen (`Ctrl+Z` / `Ctrl+Y`), Kopieren von Layouts
  zwischen Formfaktoren, Speichern des Profils auf dem Host.
- **Android-APK-Builder** direkt in der Distribution: Seite `/android.html`
  ändert App-Namen, Package-ID, Version und Gateway-Adresse, baut die APK und
  bietet sie zum Download an; außerdem gibt es eine CLI `--build-apk`.
- **Windows-Installer** (NSIS, pro Benutzer, keine Administratorrechte) mit
  fertiger APK und Android-Quellen im Paket.

### Lizenz und Integrität

- Der Autoren-Supportblock **kann nicht entfernt werden**; der SHA-256-Wert
  kritischer Dateien wird beim Host-Start und im Browser geprüft, und bei
  Abweichung wird die UI blockiert.

## Installation (Windows, ohne Python)

Laden Sie `OpenDeck-Setup-<version>.exe` aus den Releases herunter, führen Sie
sie aus und klicken Sie auf „Weiter" — Administratorrechte sind nicht
erforderlich, und weder Python noch das Internet wird benötigt. Die Installation
erfolgt nach `%LOCALAPPDATA%\OpenDeck`, Verknüpfungen und ein Eintrag in
„Programme und Funktionen" werden erstellt.

1. Starten Sie **Open Deck for MSFS** — eine Konsole mit den Panel-Adressen
   öffnet sich.
2. Erlauben Sie der App im Firewall-Dialog den Zugriff auf das private Netzwerk.
3. Öffnen Sie das Panel auf diesem PC oder geben Sie die angezeigte Adresse auf
   Ihrem Smartphone ein, oder scannen Sie den QR-Code vom Panel (die
   Smartphone-Schaltfläche).

Details zum Installer-Build — [`docs/de/packaging.md`](docs/de/packaging.md).

## Passwortanmeldung

Die Anmeldung wird auf eine der folgenden Weisen aktiviert:

```powershell
# Passwort (PBKDF2-Hash) in config/auth.json speichern
OpenDeck.exe --set-password            # fragt das Passwort in der Konsole ab
OpenDeck.exe --set-password "my-password"

# oder nur für diesen Lauf
OpenDeck.exe --password "my-password"
```

Mindestens **6 Zeichen**. Die Datei `config/auth.json` speichert nur den Hash;
löschen Sie sie, um den Zugriff wieder ohne Passwort zu erlauben. Im Startmenü
erstellt der Installer eine Verknüpfung „Passwort festlegen". Details — in der
[Dienstbeschreibung](docs/de/service.md#8-passwortauthentifizierung).

Verbundene Clients:

- Browser — Seite `/login.html`, danach das Panel (Cookie für 12 Stunden);
- Smartphone — scannen Sie den QR-Code auf dem Panel: Ein einmaliges Token
  meldet ohne Passwort an (10 Minuten gültig);
- Android — das Panel zeigt den Anmeldebildschirm selbst an; die Sitzung wird
  in der WebView gespeichert.

## Aus dem Quellcode ausführen

**Python 3.11+** ist erforderlich; Node.js — nur für Client-Tests.

```powershell
git clone https://github.com/meferspb/open-deck.git
cd open-deck

# Demo-Modus ohne Simulator: http://127.0.0.1:8760/
python -m msfs_gateway --sim mock

# echter Flug: SimConnect mit Rückfall auf Mock bei Fehlschlag
python -m msfs_gateway --sim auto

# expliziter DLL-Pfad und 60 Hz
python -m msfs_gateway --sim simconnect --simconnect-dll C:\SDK\SimConnect.dll --telemetry-hz 60
```

Nützliche Parameter:

| Parameter | Standard | Zweck |
| --- | --- | --- |
| `--host` | `0.0.0.0` | Listen-Adresse |
| `--allow-host NAME` | — | zusätzlicher DNS-Name für den Host-Header (wiederholbar) |
| `--port` | `8760` | HTTP- und WebSocket-Port |
| `--sim` | `auto` | `auto` / `mock` / `simconnect` |
| `--telemetry-hz` | `30` | Broadcast-Rate, 1..60 Hz |
| `--simconnect-host` / `--simconnect-port` | `127.0.0.1` / `19999` | SimConnect-Adresse (auch für einen entfernten Simulator) |
| `--profile-dir` | `profiles/` | JSON-Profilverzeichnis |
| `--password` / `--set-password` | — | Passwort für den Lauf / Hash speichern und beenden |
| `--auth-file` / `--no-auth` | `config/auth.json` | Hash-Datei / Anmeldung deaktivieren |
| `--no-wasm` | — | WASM-Bridge deaktivieren |
| `--no-discovery` | — | UDP-Autoerkennung deaktivieren |
| `--build-apk [CONFIG]` | — | Android-APK bauen und beenden |

## Android-APK aus der Distribution

Die installierte App enthält die Android-Quellen (`android/`); die fertige APK
wird nach `android/dist/OpenDeck-Android-<version>.apk` gebaut, und im Startmenü
gibt es „Android-APK bauen" (`http://127.0.0.1:8760/android.html`).

Auf der Seite legen Sie App-Namen, Package-ID, Version und standardmäßige
Gateway-Adresse fest; die Schaltfläche „APK bauen" führt `gradle assembleDebug`
auf demselben Rechner aus. Erforderlich sind **JDK 17**, **Android SDK** und
**Gradle 8.x** (Pfade können auf der Seite angegeben oder über `JAVA_HOME` /
`ANDROID_HOME` / `gradle` in `PATH` gesetzt werden). In der Release-Distribution
liegt die fertige APK bereits in `android/dist`.

```powershell
OpenDeck.exe --build-apk                        # Einstellungen aus config/android-build.json
OpenDeck.exe --build-apk C:\path\settings.json
```

## Dokumentation

Der vollständige Index ist [docs/de/README.md](docs/de/README.md). Wichtigste
Dokumente:

- [Dienstbeschreibung: Zweck, API, Authentifizierung, Assistent, Betrieb](docs/de/service.md)
- [Architektur und Zuständigkeiten](docs/de/architecture.md)
- [Netzwerkprotokoll: REST, WebSocket, Anmeldung, QR, Autoerkennung](docs/de/protocol.md)
- [Telemetrie-Variablenkatalog](docs/de/telemetry.md) *(aus dem Code generiert)*
- [Instrumenten- und Optionskatalog](docs/de/widgets.md) *(aus dem Code generiert)*
- [Flugzeugprofil-Schema](docs/de/profile-schema.md)
- [Android-Client: Build, Anmeldung, Debugging](docs/de/android.md)
- [Installer bauen](docs/de/packaging.md)
- [Kosten verbundener Dienste im Vergleich zu lokalen Entsprechungen](docs/de/pricing.md)
- [Changelog](docs/de/changelog.md)

## Repository-Struktur

```
msfs_gateway/            # Python-Gateway (stdlib)
  sim/                   # Provider: mock, simconnect, client_data, wasm_bridge
  qr.py                  # integrierter QR-Generator (SVG)
  assist.py              # Lande- und Roll-Assistent
  android_build.py       # APK-Build aus der Distribution
  http_api.py, hub.py, profiles.py, integrity.py, discovery.py, websocket.py
web/                     # Web-Client und Editor (vanilla JS, kein Build-Schritt)
profiles/                # JSON-Profile der Flugzeuge
android/                 # Android-Client (Kotlin, ohne AndroidX)
packaging/               # PyInstaller + NSIS: Windows-Installer
scripts/                 # build-installer.ps1, check.ps1, verify_qr.py
tests/                   # unittest (Python) und node:test (JS)
docs/                    # Architektur, Protokoll, Schema, Screenshots
config/                  # Autorendaten, APK-Build-Einstellungen
integrity/               # SHA-256-Manifest kritischer Dateien
```

## Tests

```powershell
python -m unittest discover -s tests        # 252 Tests
node --test "tests/web/*.test.mjs"          # 29 Tests
python -m ruff check msfs_gateway tests scripts
```

Alle Prüfungen auf einmal ausführen:

```powershell
pwsh -File scripts/check.ps1
```

Abgedeckt: Telemetrie und Profile, WebSocket (RFC 6455), Bus und Befehle,
Mock-Provider, WASM/Client Data, QR (Struktur + Referenzmatrix),
APK-Builder, Integrität, Instrumentengeometrie und Layouts.

## Entwicklung

Siehe [`docs/de/contributing.md`](docs/de/contributing.md): Stil, Tests, wie man
ein Profil oder ein Instrument hinzufügt. Sicherheitsfragen —
[`docs/de/security.md`](docs/de/security.md).

## Roadmap

1. **Live-Lauf der WASM-Bridge** mit MSFS + MobiFlight/SimBridge (Logik und
   Emulation sind durch Tests abgedeckt).
2. **Release-Signierung der APK**: Keystore/Alias in den Builder-Einstellungen.
3. **mDNS (Bonjour)** als Alternative zum UDP-Beacon.
4. **Editor**: Ausrichtungslinien, Mehrfachauswahl.
5. **Android**: natives Compose-Rendering, Vordergrunddienst für den Kiosk-Modus.
6. **Telemetrie-Aufzeichnung/Wiedergabe** für Demos und Profiling.

## Sicherheit

Das Projekt ist für ein **vertrauenswürdiges lokales Netzwerk** ausgelegt: HTTP
ohne TLS und Authentifizierung sowie ein unsignierter UDP-Beacon. Setzen Sie das
Gateway nicht dem Internet aus. Mehr — [`docs/de/security.md`](docs/de/security.md).

## Support / Donat

- **Donat:** [https://taps.uz/open_deck_fs](https://taps.uz/open_deck_fs)
- **Autor:** Viktor Krasnikov
- **Repository:** [https://github.com/meferspb/open-deck](https://github.com/meferspb/open-deck)

## Lizenz

Das Projekt wird unter der **GNU Affero General Public License v3.0 (AGPL-3.0)**
mit zusätzlichen Bedingungen gemäß **Abschnitt 7** vertrieben.

* Sie dürfen diesen Code frei verwenden, studieren, ändern und verbreiten,
  sofern dieselbe Lizenz (AGPL-3.0) beibehalten und der Quellcode jeglicher
  Änderungen verfügbar gemacht wird (einschließlich der Nutzung auf einem Server /
  über ein Netzwerk gemäß Abschnitt 13).
* **Zwingende Bedingung (Abschnitt 7(b) & Abschnitt 5(d)):** In allen Forks,
  Builds und modifizierten Versionen ist es **strengstens verboten**, den
  Hinweis auf den ursprünglichen Autor (**Viktor Krasnikov**,
  [https://github.com/meferspb/open-deck](https://github.com/meferspb/open-deck))
  und die aktiven Links zur Unterstützungs- (Spenden-)Seite des Entwicklers in
  der Benutzeroberfläche und Dokumentation des Programms zu entfernen, zu
  verbergen oder zu verändern: [Donat — https://taps.uz/open_deck_fs](https://taps.uz/open_deck_fs).

Der ausführliche Rechtstext der zusätzlichen Bedingungen findet sich in der
Datei [COPYING.ADDITIONAL](./COPYING.ADDITIONAL). Der vollständige Text der
Basislizenz steht in der Datei [LICENSE](./LICENSE).
