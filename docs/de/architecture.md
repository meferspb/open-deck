# 🏗️ Open Deck for MSFS Architektur

Dieses Dokument beschreibt die Komponenten, Datenflüsse und zentralen
Designentscheidungen. Das Profilformat wird in [profile-schema.md](profile-schema.md)
behandelt, das Netzwerkprotokoll in [protocol.md](protocol.md).

---

## 1. Übersichtsdiagramm

```
┌───────────────────────────── Windows Host (Core Gateway) ─────────────────────────────┐
│                                                                                       │
│  ┌───────────────┐   ┌───────────────┐   ┌───────────────┐   ┌────────────────────┐   │
│  │  SimProvider  │──▶│      Hub      │──▶│ WebSocket /ws │──▶│  Web client (JS)   │   │
│  │  (mock /      │   │  (broadcast,  │   │               │   │  Android client    │   │
│  │   SimConnect) │   │   commands)   │   ├───────────────┤   └────────────────────┘   │
│  └──────▲────────┘   └──────▲────────┘   │  HTTP /api    │                            │
│         │                   │            │  HTTP / (static)│                          │
│         │ read()            │ profiles   └───────┬───────┘                            │
│         │ apply_command()   │ list/get/save      │                                    │
│  ┌──────┴────────┐   ┌──────┴────────┐          │                                    │
│  │  telemetry.py │   │  profiles.py  │          │  REST + WebSocket on ONE port      │
│  │ (SimVar reg.) │   │  (validation) │          └────────────────────────────────────┘
│  └───────────────┘   └───────────────┘                                               │
│                                                                                       │
└───────────────────────────────────────────────────────────────────────────────────────┘
        ▲
        │ SimConnect API (native, ctypes) — or mock without MSFS
        │
┌───────┴────────┐
│  MSFS 2020/24  │
└────────────────┘
```

---

## 2. Komponenten und Zuständigkeiten

### 2.1. `telemetry.py` — kanonisches Variablenregister

Die einzige Quelle der Wahrheit über Größen: Schlüsselname, Typ, Einheit,
SimVar-Bindung (`sim_var`/`sim_unit`) und Schreibereignis (`sim_event`). Profile
verweisen nur auf diese Schlüssel, sodass das Umbenennen einer SimVar eine
Änderung an einer einzigen Stelle ist.

```python
Variable("power.batteryMaster", "bool", "Master battery",
         sim_var="ELECTRICAL MASTER BATTERY", sim_unit="bool",
         sim_event="TOGGLE_MASTER_BATTERY")
```

### 2.2. `sim/` — Telemetriequellen (Provider)

Gemeinsame Schnittstelle `SimProvider`:

| Methode | Zweck |
| --- | --- |
| `connected` | ob eine aktive Verbindung zum Simulator besteht |
| `start()` / `stop()` | der Hintergrundthread des Providers |
| `read()` | ein Schnappschuss der Werte `dict[key, value]` |
| `apply_command(key, value)` | einen Client-Befehl anwenden |
| `select_aircraft(profile_id)` | das Flugzeug wechseln (nur von Mock unterstützt) |

Implementierungen:

- **`MockSim`** — ein prozeduraler Flug: Roll-/Nickwinkel/Kurs/Geschwindigkeit/
  Höhe ändern sich entlang glatter Sinuskurven, Kraftstoff wird verbraucht.
  Benötigt für Entwicklung ohne MSFS, Demos und automatisierte Tests.
- **`SimConnectSim`** — natives SimConnect über `ctypes`. Abonniert einen Block
  numerischer Datums (`AddToDataDefinition` + `RequestDataOnSimObject`),
  separat die Zeichenketten `TITLE`/`ATC MODEL`, cacht Werte in `read()` und
  sendet Befehle als Ereignisse (`MapClientEventToSimEvent` +
  `TransmitClientEvent`). SimConnect-Aufrufe, einschließlich Befehle, erfolgen im
  Dispatch-Thread (`run_on_dispatch`), da die API nicht für Multithread-Aufrufe
  ausgelegt ist. Wenn die Benutzer-`SimConnect.cfg` auf einen nicht existierenden
  Kanal zeigt, wird die Verbindung über TCP `127.0.0.1:19999` mit einer
  temporären Konfiguration erneut versucht (der MSFS-2020/2024-Port). Die
  Verbindung zu einem laufenden MSFS 2020 wurde verifiziert; der Live-Austausch
  numerischer Daten, das WASM-Modul und der Assistent im Flug sind der nächste
  Validierungsschritt.

Die Fabrik `create_sim()` wählt einen Provider anhand der Einstellung `--sim`:

- `mock` → immer Mock;
- `simconnect` → nur SimConnect, Beenden bei Fehler;
- `auto` → SimConnect mit Rückfall auf Mock bei Fehlschlag (das Gateway startet
  immer).

### 2.3. `hub.py` — Telemetrie-Bus

- ein einzelner „Ticker"-Thread mit der Rate `--telemetry-hz` sammelt
  `sim.read()` und sendet den Frame an alle WebSocket-Clients;
- jeder Client hat seine eigene Warteschlange (8 Frames) und seinen eigenen
  Sender-Thread: Ein langsames Tablet stoppt die Zustellung an die anderen nicht,
  und alte Frames werden verworfen;
- **Befehlsratenbegrenzung** (≤30/s pro Client) — Schutz gegen ein hängendes
  Touch-Ereignis;
- `build_message()` normalisiert Werte (Runden auf 3 Nachkommastellen, die
  vollständige Schlüsselmenge) und fügt `seq`, `ts` und `sim`-Metadaten hinzu.

### 2.4. `profiles.py` + `legacy.py` — Flugzeugprofile

- `validate_profile()` — strikte Strukturprüfung (Instrumententypen, Bindungen,
  Befehle, Rechtecke, Skalenbereiche);
- `ProfileStore` — threadsicheres atomares Speichern (tmp + `fsync` +
  `os.replace`);
- `legacy.adapt()` — wandelt das „Pixel"-v0-Format aus der Spezifikation in das
  interne Format um (Koordinaten in 0..1-Bruchteilen), damit alte Panels
  unverändert geladen werden.

### 2.5. `http_api.py` + `websocket.py` — Netzwerk

- `ThreadingHTTPServer` liefert statische Dateien aus `web/` und die REST-API und
  führt das WebSocket-Upgrade auf einem Port durch — eine einzige Firewall-Regel;
- `websocket.py` — eine minimale RFC-6455-Implementierung (Text, Ping/Pong,
  Close) auf Basis der Standardbibliothek;
- `auth.py` — optionale Passwortanmeldung: PBKDF2-Hash, In-Memory-Sitzungen,
  `HttpOnly`-Cookie, Bearer-Token, einmalige QR-Token, Versuchsbegrenzung;
- Sicherheitsheader: CSP `default-src 'self'`, `X-Content-Type-Options`,
  `Referrer-Policy`; statische Dateien ohne Caching (Live-Entwicklung);
- `/api/connect` + `qr.py` — schnelle Smartphone-Verbindung: Der Host listet
  seine Netzwerkadressen auf (zuerst `192.168.x`, dann `10.x`, `172.16-31.x`),
  und der QR-Code wird von einem eigenen stdlib-Generator gezeichnet (Byte-Modus,
  EC L, Versionen 1–10, alle Masken), ohne externe Bibliotheken oder Internet.

### 2.5a. `auth.py` — Passwortanmeldung

- Das Passwort wird nur als PBKDF2-Hash gespeichert (`config/auth.json`) und mit
  `hmac.compare_digest` geprüft; 5 Fehlschläge pro Minute von einer Adresse →
  Sperrung.
- Sitzungen liegen im Prozessspeicher (32 Byte, 12 Stunden TTL, bei Aktivität
  verlängert); der Browser erhält ein `open_deck_session`-Cookie (`HttpOnly`,
  `SameSite=Lax`), native Clients verwenden Bearer oder `?token=` für
  WebSocket.
- Einmalige QR-Token (`POST /api/pair`, 10 Minuten) ermöglichen einem
  Smartphone die Anmeldung ohne Passworteingabe. Ein solches Token wird nur
  über `/?pair=` akzeptiert: `SessionStore.validate` weist `pairing`-Sitzungen
  ab, sodass es nicht als Cookie oder Bearer-Token verwendet werden kann.
- Browser-POST/PUT- und WebSocket-Anfragen, deren `Origin` nicht zu `Host`
  passt, werden mit `403` abgewiesen (Schutz gegen Cross-Site-WebSocket-
  Hijacking und CSRF); Clients ohne `Origin` (Android, curl) sind erlaubt.
- Der `Host`-Header wird zusätzlich gegen localhost, den Rechnernamen, FQDN und
  lokale IPs geprüft. Das schließt DNS-Rebinding, bei dem sowohl `Origin` als
  auch `Host` zur Domain des Angreifers gehören.
- Nur Anmeldung, `/api/health`, `/api/integrity`, `/api/donation` und `/license`
  sind öffentlich zugänglich; alles andere ist geschlossen.

### 2.5b. `assist.py` — Lande- und Roll-Assistenten

- **Rollen**: ein PI-Schubregler nach Geschwindigkeit über Grund und ein
  P-Seitenruderregler nach Kurs; nur am Boden aktiv, deaktiviert beim Abheben/
  Bremsen/Geschwindigkeit über 35 kt; „STOP" liefert Nullschub und die
  Parkbremse.
- **Landen**: ARM aktiviert AP und APR, zwischen 60–15 ft reduziert er den Schub
  linear, und bei der Landung koppelt er den AP ab; TOGA — Vollschub. Er
  berührt das Höhenruder nicht.
- Ein 10-Hz-Thread liest `sim.read()` und sendet Befehle über
  `Hub.apply_assist_command` (ohne Ratenbegrenzung oder zusätzliche Reads).
- Dies ist eine Hilfsregelung: Die endgültige Entscheidung und Kontrolle
  verbleiben beim Piloten.

### 2.6. `integrity.py` — Spendenschutz (Lizenzbedingung)

Vergleicht den SHA-256-Wert von fünf kritischen Dateien (darunter
`web/js/ui/donation.js`, `web/css/donation.css`, `config/donation.json`) mit dem
Manifest `integrity/manifest.json`. Der Host blockiert den Start bei Abweichung;
der Client (`web/js/ui/integrity.js`) überwacht zusätzlich die Sichtbarkeit des
Blocks im DOM. Autor — Viktor Krasnikov
([github.com/meferspb/open-deck](https://github.com/meferspb/open-deck)),
Donat — [https://taps.uz/open_deck_fs](https://taps.uz/open_deck_fs).

### 2.7. `discovery.py` — Host-Autoerkennung (UDP-Broadcast)

Ein Hintergrundthread sendet alle N Sekunden einen JSON-Beacon (Hostname,
Version, `httpPort`, Frequenz, Profilliste) über UDP-Broadcast
(`255.255.255.255` + gerichteter Broadcast jeder Schnittstelle).
`listen_once()` ist der Empfänger für native Clients und Tests. Browser
unterstützen kein UDP, daher benötigt der Web-Client es nicht (er startet ohnehin
vom Host selbst).

### 2.8. `web/editor.*` — visueller Panel-Editor

`/editor.html` + `web/js/editor.js` — ein Drag-and-drop-Editor: Verschieben und
Größenändern von Instrumenten, Konfigurieren von Bindungen (Dropdown-Listen aus
dem Katalog `GET /api/telemetry/variables` plus im Profil deklarierte
`custom.*`), Optionen (Skalen, Einheiten, Farbtöne), Hinzufügen aus einer
Typ-Palette und Löschen. Das Speichern erfolgt über `PUT /api/profiles/{id}`.
Die Vorschau zeichnet echte Instrumente (über das Register
`widgets/registry.js`) mit Demo-Werten. Formfaktor-Überschreibungen werden im
aktiven Formfaktor bearbeitet: Wenn es keine Überschreibung gibt, geht die
Änderung in `layout.base`. Eine Bearbeitungshistorie (Schnappschüsse von
`widgets` vor einer Änderung) ermöglicht Rückgängig und Wiederholen für
Ziehen, Größenändern, Eigenschaften, Hinzufügen und Löschen; außerdem gibt es
ein 1-%-Raster-Einrasten (Shift deaktiviert es vorübergehend) und das Kopieren
der Geometrie auf andere Formfaktoren mit einer Schaltfläche.

### 2.8a. Automatische Flugzeugerkennung

`SimConnectSim` liest `TITLE` und `ATC MODEL` als separate String-Datums
(`SIMCONNECT_DATATYPE_STRING256`) und speichert sie in `aircraft.title` /
`aircraft.atcModel`. `hub.py` hält die Regeln `sim.match.title` / `atcModel`
(Glob, ohne Groß-/Kleinschreibung) und wählt bei jedem Frame ein Profil aus,
wenn der Provider nicht selbst eines setzt. Der Client beobachtet
`sim.profileId` in der Telemetrie und lädt das Panel neu, wenn das Flugzeug
wechselt; die manuelle Auswahl aus der Liste wird für 5 Sekunden fixiert, damit
sie nicht mit einem noch nicht eingetroffenen Frame kollidiert.

### 2.8b. `web/js/ui/comfort.js` — Helligkeit und Kiosk

Die Panel-Helligkeit hat drei Stufen (100/72/45 %), wird in `localStorage`
gespeichert und über das Attribut `data-brightness` auf `<html>` angewendet:
CSS dimmt nur die Instrumentenszene, während die UI lesbar bleibt. Der
Kiosk-Modus blendet die obere Leiste und die Statusleiste aus, schaltet die
Szene in den Vollbildmodus und lässt eine kleine Beenden-Schaltfläche übrig;
`Esc` stellt die UI wieder her. Tastenkürzel: `B` — Helligkeit, `F` und `Esc` —
Kiosk.

### 2.9. WASM-Bridge: LVAR/RPN über Client Data Area

Komplexe Flugzeuge (PMDG, Fenix, FlyByWire, iniBuilds) halten ihren Zustand in
eigenen Variablen. Ein Profil deklariert sie im Block `variables` (`source: lvar`
oder `rpn`), und die Bridge liest/schreibt sie über **SimConnect Client Data
Area** — das WASM-Modul (MobiFlight / SimBridge) veröffentlicht dort Daten.

```
hub.build_message()
   └─ hub._custom_values(profile_id)        # 0.25 s cache
        └─ WasmBridge.read_specs(specs)      # wasm_bridge.py
             ├─ read_lvars(names)            # block: name 128 B + double 8 B
             └─ execute_rpn(script)          # Command → Response
                  └─ ClientDataChannel.read_area / write_area   # client_data.py
                       └─ SimConnectClientDataBackend            # simconnect.py
                            └─ run_on_dispatch(...)  # calls on the SimConnect thread
```

Schichten:

- **`sim/client_data.py`** — das Protokoll in synchroner Form:
  Anfragekorrelation über `request_id`, Timeouts, erneute Registrierung einer
  Area, wenn ihre Größe wächst, und Zurücksetzen ausstehender Anfragen bei
  Trennung. Der Transport ist abstrahiert (`ClientDataBackend`), sodass das
  Protokoll ohne MSFS getestet wird; `LoopbackClientDataBackend` ist eine
  In-Memory-Implementierung für Tests und Demos.
- **`sim/simconnect.py`** — `SimConnectClientDataBackend`: `MapClientDataNameToID`,
  `AddToClientDataDefinition`, `RequestClientData`, `SetClientData`. Alle
  Aufrufe erfolgen im Dispatch-Thread über `run_on_dispatch` (SimConnect ist
  nicht für Multithread-Aufrufe ausgelegt), und Antworten treffen in
  `SIMCONNECT_RECV_ID_CLIENT_DATA` ein.
- **`sim/wasm_bridge.py`** — das LVAR-Blocklayout, RPN-Befehle und
  LVAR-Schreibzugriffe über `(<value>) (>L:NAME, number)`.

Standard-Areas: `MobiFlight.LVars`, `MobiFlight.Command`,
`MobiFlight.Response`; für eine andere Modulversion werden sie durch Konstanten
in `wasm_bridge.py` überschrieben.

Es wird automatisch für den Provider `simconnect` aktiviert (das Flag
`--no-wasm` deaktiviert es). Wenn das WASM-Modul nicht installiert ist, treffen
keine Antworten ein: Nach zwei aufeinanderfolgenden Timeouts stoppt der
Circuit Breaker von `ClientDataChannel` das Polling vorübergehend (30 s), damit
der Telemetriestream nicht bei jedem Frame blockiert wird. Die `custom.*`-
Schlüssel fehlen dann einfach im Frame — die Instrumente zeigen ehrlich „--",
und die SimVar-Telemetrie funktioniert weiter. Der LVAR-Block ist auf 56
Elemente (7616 Byte) begrenzt, damit er in `MaxRecvData`/`MaxSendData` = 8192
passt. Im Mock-Modus werden Werte aus `initial` des Profils übernommen.
Eingebaute SimVars, die in der akzeptierten SimConnect-Definition fehlen oder
veraltet sind, werden als `null` statt `0` zurückgegeben: Das Panel zeigt „--",
und der Assistent verwechselt sie nicht mit echten Nullen.

**Verifizierungsstatus:** Protokoll und Area-Abrechnung sind durch Tests
abgedeckt (MobiFlight-Emulation über einen In-Memory-Transport), und Build und
Start wurden verifiziert; ein Live-Flug mit MSFS + WASM-Modul wurde noch nicht
durchgeführt — dies ist der einzige Schritt, der einen installierten Simulator
erfordert.

### 2.10. `android_build.py` — Android-APK aus der Distribution bauen

Die installierte App enthält die Android-Quellen (`android/`), und nach einem
Build liegt die fertige APK in `android/dist`. Die Seite `/android.html` und die
API `/api/android/*` ermöglichen das Ändern von App-Name, Package-ID, Version und
standardmäßiger Gateway-Adresse, das Ausführen von `gradle assembleDebug` und
das Herunterladen der frischen APK. Einstellungen liegen in
`config/android-build.json`; dieselben Werte werden als `-P…` an den Build
übergeben und landen in `BuildConfig`/dem Android-Manifest.

Tool-Suche: Einstellungen → `JAVA_HOME` / `ANDROID_HOME` → typische Pfade.
Wenn das Benutzerprofil nicht beschreibbar ist (strikte Richtlinien, Sandboxes),
werden Gradle-Cache, `TMP` und der Debug-Keystore automatisch in das
Distributionsverzeichnis umgeleitet (`.gradle-home`, `.tmp`, `.android-home`) —
der Build funktioniert weiter. CLI ohne Browser:
`OpenDeck.exe --build-apk [config.json]`.

---

## 3. Datenfluss

### 3.1. Telemetrie (Push)

```
MockSim/SimConnectSim._loop()
   └─ sim.read()                        # snapshot of values
        └─ hub.build_message()          # normalization + seq/ts/sim
             └─ hub._broadcast_text()   # JSON into each WebSocket queue
                  └─ web: handleMessage('telemetry') → store → panel-view → widgets
```

### 3.2. Befehl (Anfrage/Bestätigung)

```
web: toggle-switch.onClick()
   └─ socket.command(key, value)        # {type:'command', id, key, value}
        └─ hub.handle_command()         # validation + rate limit
             └─ sim.apply_command()     # mock / SimConnect
                  └─ ack {type:'ack', id, ok, value}   (over WebSocket)
                       └─ client waits for confirmation via telemetry
```

### 3.3. Profil (Pull)

```
web: api.listProfiles() → GET /api/profiles
   └─ api.getProfile(id) → GET /api/profiles/{id}
        └─ profiles.load_profile_file() → legacy.adapt_if_needed() → ensure_valid()
             └─ panel-view.mount(profile) → createWidgetInstance() by type
```

### 3.4. Autoerkennung (UDP-Push)

```
DiscoveryBeacon._loop()                      # daemon thread
   └─ payload() {name, version, httpPort, profiles, auth?, ts}
        └─ sendto(255.255.255.255:8761) + directed broadcasts
             └─ Android/native client: listen_once() → http://<ip>:<port>/
```

---

## 4. Zentrale Designentscheidungen

| Entscheidung | Warum |
| --- | --- |
| Nur Python-Standardbibliothek | air-gapped: `pip install` ist nicht verfügbar; ein Interpreter ist bereits installiert |
| Ein Port für HTTP+WS | eine Firewall-Regel, einfachere Diagnose |
| WebSocket ohne externe Bibliothek | Kontrolle über das Protokoll, keine Abhängigkeiten |
| Profil verwendet 0..1-Koordinaten, keine Pixel | ein Profil für alle Formfaktoren |
| `layout.base` + Überschreibungen | Smartphone/Tablet geben nur die Unterschiede an |
| Kanonisches SimVar-Register | entkoppelt Profile von einer bestimmten Bridge |
| Clientseitige Glättung (Smoother) | 60-fps-Animation über ein 20–30-Hz-Netzwerk |
| Widget zeichnet Canvas nach `clientWidth` | ehrliche HiDPI-Skalierung in der Vorschau |
| `auto`-Provider | das Gateway startet ohne MSFS und ohne Konfigurationsänderungen |
| UDP-Autoerkennungs-Beacon | Android findet den Host ohne manuelle IP; Browser benötigen es nicht |

---

## 5. MVP-Grenzen und nächste Schritte

Was **bereits existiert**: ein stdlib-Gateway, WebSocket mit Warteschlangen pro
Client, Mock/SimConnect (+ TCP-Rückfall), LVAR/RPN-WASM-Bridge, 9
Instrumententypen, 3 Formfaktoren, Profile mit Validierung und atomarem
Speichern, ein Editor mit Rückgängig/Wiederholen und Layout-Kopieren,
UDP-Autoerkennung, ein Android-Client, ein APK-Builder in der Distribution, ein
Windows-Installer, Passwortanmeldung mit QR, Lande- und Roll-Assistent,
Integritätsprüfung, 252 Python- und 41 JS-Tests.

Nächste Schritte (siehe README „Roadmap"):

- Live-Flugvalidierung: SimConnect/WASM in einem echten Flugzeug, Assistent in
  der Luft und am Boden;
- Release-Signierung der APK (Keystore in den Builder-Einstellungen);
- mDNS (Bonjour) als Alternative zum UDP-Beacon;
- Rollführung anhand von Flughafenkarten (derzeit hält der Assistent nur
  Geschwindigkeit und Kurs);
- Telemetrie-Aufzeichnung/Wiedergabe für Demos und Profiling.
