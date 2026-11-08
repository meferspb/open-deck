# 🛠️ Entwicklung und internes Design

Ein Dokument für diejenigen, die den Code ändern: was wo liegt, wie man eine
Variable, ein Instrument, ein Profil, einen Provider oder eine Seite hinzufügt
und wie man testet und veröffentlicht. Die Benutzerdokumentation steht in
[service.md](service.md), das Protokoll in [protocol.md](protocol.md).

## 1. Anforderungen

- Windows 10/11 (das Gateway verwendet `ctypes` für SimConnect; der Rest ist
  plattformübergreifend).
- Python **3.11+**; es gibt keine Drittanbieter-Abhängigkeiten — nur die
  Standardbibliothek.
- Node.js **20+** — für Web-Client-Tests (der Client selbst benötigt keinen
  Build).
- JDK 17 + Android SDK + Gradle 8.x — nur für den APK-Build.
- PyInstaller und NSIS — nur für den Installer.

## 2. Code-Karte

```
msfs_gateway/
  app.py            Dependency-Assembly, Lebenszyklus, CLI-Modi
  settings.py       CLI-Argumente, Pfade, Standardwerte
  telemetry.py      Variablenregister (Schlüssel, Typen, SimVars, Ereignisse)
  hub.py            Bus: Frame, Abonnements, Befehle, Flugzeug-Autoerkennung
  http_api.py       HTTP: statische Dateien, REST, WebSocket-Upgrade, Autorisierung
  websocket.py      RFC 6455: Frames, Ping/Pong, Close, Sendewarteschlange
  auth.py           Passwort, PBKDF2, Sitzungen, QR-Token, Versuchsbegrenzung
  assist.py         Roll- und Lande-Assistent (10 Hz)
  profiles.py       Validierung, Speicherung, atomares Speichern von Profilen
  legacy.py         Adapter für das alte v0-Profilformat
  integrity.py      SHA-256-Manifest kritischer Dateien
  discovery.py      Autoerkennungs-UDP-Beacon
  qr.py             QR-Generator (SVG) auf stdlib
  android_build.py  Einstellungen, Tool-Suche, Gradle-Start
  docsgen.py        Generierung von docs/telemetry.md und docs/widgets.md
  sim/              Provider: mock, simconnect, client_data, wasm_bridge
web/                Panel, Editor, Anmeldung, Assistent (vanilla ES-Module)
profiles/           JSON-Profile der Flugzeuge
android/            Kotlin-Client (WebView + UDP-Erkennung)
packaging/windows/  PyInstaller + NSIS
scripts/            build-installer.ps1, check.ps1, verify_qr.py
tests/              unittest (Python) und node:test (JS)
docs/               diese und weitere Dokumentation
```

## 3. Wie man eine Telemetrie-Variable hinzufügt

1. Öffnen Sie `msfs_gateway/telemetry.py` und fügen Sie ein `Variable(...)` zu
   `_VARIABLES` hinzu: Schlüssel, Typ, Label, `sim_var`/`sim_unit` und
   gegebenenfalls `sim_event`, `sim_event_param`, `sim_event_scale`.
2. Prüfen Sie den SimVar-Namen anhand der MSFS-SDK-Dokumentation (Groß-/
   Kleinschreibung und Einheiten sind wichtig).
3. Aktualisieren Sie den Katalog: `python -m msfs_gateway.docsgen --write`.
4. Führen Sie `python -m unittest tests.test_telemetry` und die vollständige
   Testsuite aus.
5. Wenn die Variable eine Steuerung ist — stellen Sie sicher, dass das Ereignis
   den Zustand tatsächlich ändert (der `bool`-Vergleich verwendet den aktuellen
   Wert).

## 4. Wie man ein Instrument hinzufügt

1. Erstellen Sie `web/js/widgets/my-widget.js`: eine Klasse mit `update(state)`
   und `destroy()` (siehe `base.js` und benachbarte Instrumente). Rendering —
   Canvas oder DOM.
2. Registrieren Sie den Typ in `web/js/widgets/registry.js`.
3. Fügen Sie den Typ zu `WIDGET_TYPES`, die erforderlichen Rollen zu
   `REQUIRED_BINDINGS` und bei Bedarf Optionsprüfungen in
   `msfs_gateway/profiles.py` hinzu.
4. Beschreiben Sie das Instrument in `msfs_gateway/docsgen.py` (`WIDGET_ORDER`,
   `WIDGET_TITLES`, `WIDGET_DESCRIPTIONS`, `WIDGET_OPTIONS`, Beispiel) und
   führen Sie `python -m msfs_gateway.docsgen --write` aus.
5. Prüfen Sie es auf allen drei Formfaktoren (Smartphone/kleines/großes Tablet)
   und im Editor; fügen Sie einen Geometrietest in `tests/web/` hinzu.

## 5. Wie man ein Flugzeugprofil hinzufügt

1. Kopieren Sie ein ähnliches Profil aus `profiles/` und ändern Sie `id`, `name`,
   `icao`, `sim.match` (Glob über `TITLE`/`ATC MODEL`).
2. Prüfen Sie die Validierung: `python -m unittest tests.test_profiles`.
3. Erstellen Sie die `base`-Layouts + Unterschiede für die Formfaktoren; stellen
   Sie sicher, dass die Rechtecke nicht über `0..1` hinausgehen.
4. Prüfen Sie im Editor `/editor.html` und in einem echten Flugzeug (falls MSFS
   verfügbar ist).
5. Fügen Sie das Profil zum README (Liste) und zum CHANGELOG hinzu.

## 6. Wie man einen Telemetrie-Provider hinzufügt

1. Leiten Sie von `SimProvider` (`sim/base.py`) ab und implementieren Sie
   `start`, `stop`, `read`, `apply_command`, `connected`; bei Bedarf —
   `select_aircraft`, `aircraft_title`, `atc_model`.
2. Registrieren Sie die Auswahl in `sim/__init__.py:create_sim()` und fügen Sie
   den Wert zu `SIM_CHOICES` (`settings.py`) hinzu.
3. Thread-Sicherheit: `read()` und `apply_command()` können aus verschiedenen
   Threads aufgerufen werden — verwenden Sie ein Lock.
4. Fügen Sie Tests mit einem Fake-Transport hinzu (siehe
   `tests/test_mock_sim.py`).

## 7. Wie man einen Endpunkt hinzufügt

1. Behandeln Sie den Pfad in `_handle_api_get/post/put` (`http_api.py`).
2. Entscheiden Sie, ob er öffentlich oder sitzungsgeschützt ist: öffentlich —
   nur in `PUBLIC_API_PATHS`; alles andere ist automatisch geschlossen.
3. Antworten Sie über `_send_json`/`ApiError`; Fehler tragen einen
   maschinenlesbaren `code`.
4. Dokumentieren Sie den Endpunkt in `docs/protocol.md` (Tabelle + Beispiel) und
   in `docs/service.md` (API-Abschnitt).
5. Fügen Sie einen Test in `tests/` hinzu (Unit + HTTP-Integration bei Bedarf).

## 8. Wie man eine Seite hinzufügt

1. Legen Sie das HTML in `web/`, JS in `web/js/`, Styles in `web/css/` ab.
2. Die Seite ist standardmäßig **geschlossen** (außer `/login.html` und ihren
   Dateien); ohne Sitzung gibt der Server `302` zur Anmeldung zurück.
3. Fügen Sie den Link in die Panel-Kopfzeile (`web/index.html`) ein und bauen
   Sie dann das Manifest neu: `python -m msfs_gateway.integrity --write`.
4. Prüfen Sie auf einem Smartphone (`?device=phone`) und im Kiosk-Modus.

## 9. Tests und Prüfungen

```powershell
pwsh -File scripts/check.ps1       # ruff + format + 248 Python + 35 JS
python -m unittest discover -s tests
node --test "tests/web/*.test.mjs"
python -m msfs_gateway.docsgen --check
python -m msfs_gateway.integrity
```

Teststrategie:

- **Reine Logik** (Validierung, Profile, QR, Assistent-Regler, Authentifizierung)
  — Unit-Tests ohne Netzwerk oder MSFS.
- **HTTP/WebSocket** — starten Sie `GatewayApplication.start_background()` auf
  `127.0.0.1:0` und verwenden Sie `http.client`/Rohsockets.
- **SimConnect/WASM** — eine Fake-DLL/ein Fake-Transport; ein Live-Flug wird
  manuell verifiziert.
- **Web** — `node:test` für reine Funktionen (Layout, `isConnectionStale`).

## 10. Dokumentation

- `docs/telemetry.md` und `docs/widgets.md` werden **aus dem Code generiert**;
  manuelle Änderungen werden überschrieben. Ändern Sie `docsgen.py` und führen
  Sie `--write` aus.
- Die anderen Dokumente sind manuell; wenn sich das Verhalten ändert,
  aktualisieren Sie `service.md`, `protocol.md`, `profile-schema.md` und
  `CHANGELOG.md`.
- Die Aktualitätsprüfung ist in `scripts/check.ps1` integriert (docsgen
  --check).
- Index — [README.md](README.md).

## 11. Build und Release

1. Aktualisieren Sie die Version (`msfs_gateway/__init__.py`,
   `config/android-build.json`, `packaging/windows/README.md`).
2. `python -m msfs_gateway.integrity --write` (falls kritische Dateien geändert
   wurden).
3. `pwsh -File scripts/build-installer.ps1 -Version <x.y.z> -NsisPath <NSIS>`.
4. Prüfen Sie Installation/Deinstallation und `--set-password` auf einer
   sauberen Maschine.
5. Bauen Sie die APK (`android/gradle assembleDebug`) und legen Sie sie in
   `android/dist` ab.
6. Aktualisieren Sie `CHANGELOG.md`, committen Sie und taggen Sie `v<x.y.z>`.

## 12. Konventionen

- Python: nur stdlib, Formatierung mit `ruff format`, Zeilenlänge 100.
- JS: ES-Module, kein CDN und kein Build-Schritt; `node --check` und
  `node:test`.
- Kotlin: nur SDK und stdlib, kein AndroidX.
- Kommentare und Dokumentation — auf Englisch; Bezeichner — auf Englisch.
- Fügen Sie keine externen Abhängigkeiten hinzu, es sei denn, es ist absolut
  notwendig: Das Projekt ist für air-gapped Installation ausgelegt.
