# 🔌 Open Deck for MSFS Netzwerkprotokoll

Die gesamte Kommunikation läuft über einen einzigen TCP-Port (`8760` standardmäßig):

- **HTTP-Statikdateien** — Dateien aus `web/` (Panel, Editor, Anmeldung,
  Assistent);
- **REST-API** — Profile, Telemetrie, Befehle, Assistent, APK-Build;
- **WebSocket `/ws`** — Telemetriestream und Befehlsbestätigungen.

## 0. Konventionen

- Basis-URL: `http://<host>:<port>`; alle Pfade sind relativ.
- JSON ist UTF-8, `Content-Type: application/json; charset=utf-8`.
- API-Antworten: `Cache-Control: no-store`; statische Dateien: `no-cache`.
- **CORS ist absichtlich deaktiviert**: Die API ist für Same-Origin-Clients
  ausgelegt, und eine Drittseite kann die Antworten nicht lesen.
- **Same-Origin-Schutz**: Wenn der Browser `Origin` sendet, müssen dessen Host
  und effektiver Port zu `Host` passen. Andernfalls erhalten `POST`/`PUT`- und
  WebSocket-Anfragen `403` `origin_not_allowed`. Clients ohne `Origin` (Android,
  curl) sind erlaubt.
- **Host-Allowlist**: `Host` muss auf localhost, den Rechnernamen, FQDN, eine
  lokale IP oder einen Namen aus `--allow-host` zeigen; andernfalls
  `403 host_not_allowed`. Dies ist ein Schutz gegen DNS-Rebinding.
- Body-Limit der Anfrage — **2 MiB**; unbekannter `Content-Length` → `411`.
- Das Passwort (falls aktiviert) und die Sitzungen werden in Abschnitt 2
  beschrieben.
- Die Protokollversion im Autoerkennungs-Beacon ist `protocol: 1`.

---

## 1. Zugriff: öffentlich und unter einer Sitzung

Wenn kein Passwort konfiguriert ist, ist alles verfügbar. Wenn eines
konfiguriert ist, sind ohne Sitzung nur die Anmeldeseite, ihre Dateien und die
von der Lizenz geforderten Dienstdaten offen:

| Pfad | Zugriff | Zweck |
| --- | --- | --- |
| `/login.html`, `/js/login.js`, `/css/*`, `/img/*` | öffentlich | Anmeldeseite und Styling |
| `/api/auth/status`, `/api/auth/login`, `/api/auth/logout` | öffentlich | Anmeldung/Abmeldung |
| `/api/health` | öffentlich | „Ist das das Gateway?", Version, Passwort-Flag |
| `/api/integrity` | öffentlich | UI-SHA-256-Prüfung |
| `/api/donation` | öffentlich | Autoren-Supportblock |
| `/license` | öffentlich | Lizenztext |
| alles andere | Sitzung erforderlich | Profile, Telemetrie, Befehle, QR, APK, Assistent, `/ws` |

Ohne Sitzung:

- antwortet die API mit `401` und `{"error","code":"unauthorized"}`, plus
  `WWW-Authenticate: Bearer realm="open-deck"`;
- antworten HTML-Seiten mit `302` auf `/login.html?next=<path>`;
- wird der WebSocket-Handshake mit `401` abgewiesen (der Browser zeigt einen
  Verbindungsfehler an).

---

## 2. Authentifizierung

Das Passwort hat mindestens 6 Zeichen und wird als PBKDF2-Hash in
`config/auth.json` gespeichert (210.000 Iterationen, zufälliges Salt). Eine
Sitzung besteht aus 32 Zufallsbytes mit einer TTL von 12 Stunden, die beim
Zugriff verlängert wird.

Das Token wird auf drei Weisen akzeptiert:

| Methode | Wo | Für wen |
| --- | --- | --- |
| Cookie `open_deck_session` | `HttpOnly; SameSite=Lax` | Browser und Android-WebView |
| `Authorization: Bearer <token>` | Header | native Clients |
| `?token=<token>` | nur `/ws` | WebSocket ohne Cookie |

### `GET /api/auth/status`

```json
{ "required": true, "authenticated": false }
```

### `POST /api/auth/login`

```json
{ "password": "secret" }
```

Erfolg — `200`, Cookie und Token:

```json
{ "ok": true, "required": true, "token": "<43 characters>", "expiresIn": 43200 }
```

Fehler:

| Status | `code` | Wann |
| --- | --- | --- |
| `400` | `missing_password` | kein `password` |
| `401` | `bad_password` | falsches Passwort |
| `429` | `rate_limited` | nach 5 Fehlschlägen von einer Adresse; enthält `Retry-After` |

Wenn kein Passwort konfiguriert ist, lautet die Antwort
`{"ok":true,"required":false}`.

### `POST /api/auth/logout`

Widerruft die aktuelle Sitzung und löscht das Cookie: `{"ok": true}`.

### `POST /api/pair`

Sitzung erforderlich. Einmaliges Token für die Anmeldung vom Smartphone:

```json
{ "url": "http://192.168.1.10:8760/?pair=…", "token": "…", "expiresIn": 600, "required": true }
```

Das Aufrufen von `url` tauscht das Token gegen eine reguläre Sitzung (Cookie)
und leitet auf `/` weiter; eine erneute Verwendung liefert
`/login.html?error=pair`.

---

## 3. REST-API

Im Folgenden ist `{id}` ein Profilbezeichner (`[a-z0-9][a-z0-9-]{1,63}`).

### `GET /api/health`

```json
{
  "status": "ok",
  "version": "0.1.0",
  "uptimeSec": 42.1,
  "clients": 1,
  "telemetryHz": 30.0,
  "authRequired": true,
  "sim": {
    "provider": "simconnect",
    "connected": true,
    "aircraftTitle": "Cessna Skyhawk G1000 Asobo",
    "profileId": "cessna-172-g1000"
  }
}
```

### `GET /api/profiles`

```json
{ "profiles": [
  { "id": "cessna-172-skyhawk", "name": "Cessna 172S Skyhawk", "icao": "C172",
    "revision": 3, "widgetCount": 11 }
] }
```

### `GET /api/profiles/{id}`

Das vollständige Profil (siehe [profile-schema.md](profile-schema.md)).
`404 not_found` — keine Datei; `422 invalid_profile` — Validierung
fehlgeschlagen.

### `PUT /api/profiles/{id}`

Der Body ist ein vollständiges JSON-Profil; die `id` im Body muss zur URL passen
(`400 id_mismatch`). Antwort `{"ok": true, "profile": {…}}`.

### `GET /api/telemetry`

Der neueste Frame (dasselbe Format wie `telemetry` über WebSocket). `seq` wächst;
`values` enthält alle Registerschlüssel.

### `GET /api/telemetry/variables`

Variablenkatalog:

```json
{ "variables": [
  { "key": "speed.iasKt", "label": "Indicated airspeed", "kind": "number",
    "unit": "KT", "writable": false, "simVar": "AIRSPEED INDICATED", "simEvent": null }
] }
```

Der vollständige menschenlesbare Katalog steht in [telemetry.md](telemetry.md).

### `GET /api/integrity`

```json
{ "verified": true, "checkedAt": "2026-11-01T…", "manifestPresent": true,
  "files": { "web/index.html": "<sha256>" }, "errors": [] }
```

### `GET /api/donation`

Autoren-Supportdaten aus `config/donation.json` (die einzige Quelle ist die
Host-Konfiguration). Autor — Viktor Krasnikov, Donat —
[`https://taps.uz/open_deck_fs`](https://taps.uz/open_deck_fs).

### `GET /api/connect`

Adressen für Smartphone/Tablet:

```json
{
  "host": "FLIGHTSIM-PC",
  "primaryUrl": "http://192.168.1.10:8760/",
  "phoneUrl": "http://192.168.1.10:8760/?device=phone",
  "urls": [
    { "url": "http://192.168.1.10:8760/", "host": "192.168.1.10",
      "private": true, "loopback": false, "linkLocal": false }
  ],
  "devicePresets": ["phone", "tablet-sm", "tablet-lg"],
  "qr": { "scale": 6, "border": 4, "maxTextLength": 512 }
}
```

Sortierung: `192.168.*`, dann `10.*`, `172.16–31.*`, Link-Local, Loopback.

### `GET /api/qr.svg?text=…&scale=6&border=4`

Ein SVG mit einem QR-Code (bis zu 512 Zeichen; auf dem Host generiert, ohne
Bibliotheken). `400 missing_text` — kein `text`; `400` (`code` = `error`) —
`scale`/`border` sind keine Zahlen; `422 qr_too_long` — der Text passt nicht in
die unterstützten QR-Versionen.

### `POST /api/sim/command`

```json
{ "key": "power.batteryMaster", "value": true }
```

Erfolg — `200` mit `{"type":"ack","id":…,"key":…,"ok":true,"value":…}`.
Fehler: `400` mit `code` = `invalid_key`, `not_writable`, `invalid_value`,
`rate_limited` oder `sim_error`; `409 sim_rejected` — der Simulator hat den
Befehl abgewiesen. Bei Variablen mit einem Parameterereignis wird der Wert
skaliert (Prozent → 0..16383).

### `POST /api/sim/aircraft`

```json
{ "profileId": "cessna-172-sixpack" }
```

Antwort: `{"ok": true, "profileId": "…", "aircraftTitle": "…", "pinned": false}`.
`pinned: true` — der Provider kann das Flugzeug nicht wechseln (SimConnect), daher
bleibt die Auswahl fixiert, bis sich das Flugzeug im Simulator ändert. `404` —
kein solches Profil.

### Assistent

`GET /api/assist` — Zustand der Regelung:

```json
{
  "telemetry": {
    "onGround": true, "radioAltitudeFt": 0, "groundSpeedKt": 12.3,
    "iasKt": 0, "headingDeg": 274, "localizerDeg": 0.0,
    "glideSlopeDeg": 0.0, "locValid": false, "gsValid": false,
    "autopilotMaster": false, "approach": false,
    "throttlePct": 18.4, "rudderPct": -3.2, "parkingBrake": false
  },
  "taxi": { "engaged": true, "targetSpeedKt": 12, "targetHeadingDeg": 274,
            "throttlePct": 18.4, "rudderPct": -3.2, "message": "…" },
  "landing": { "phase": "off", "message": "…", "throttlePct": 0, "active": false },
  "limits": { "taxiSpeedMinKt": 3, "taxiSpeedMaxKt": 25,
              "flareStartFt": 60, "flareIdleFt": 15 }
}
```

`POST /api/assist/taxi`:

| `action` | Felder | Bedeutung |
| --- | --- | --- |
| `engage` | — | Geschwindigkeits-/Kurshaltung aktivieren (nur am Boden) |
| `disengage` | — | deaktivieren |
| `stop` | — | Schub 0, Parkbremse |
| `speed` | `value` (3…25) | die Rollgeschwindigkeit setzen |
| `heading` | `delta` (±) | den Zielkurs drehen |

`POST /api/assist/landing`: `action` = `arm` (AP + APR), `disarm`, `toga`.

Antwort: `{"ok": true|false, "message": "…", "status": {…}}`.
`200` — Aktion ausgeführt; `409` — abgewiesen (nicht am Boden, Geschwindigkeit zu
niedrig, keine Verbindung zu MSFS, unbekannte Aktion).

### Android-APK-Build

- `GET /api/android/settings` — `{settings, toolchain, apk, prebuiltApk}`.
- `PUT /api/android/settings` — Einstellungen speichern (Name, Package-ID,
  Version, Gateway-Adresse, Tool-Pfade). `422 invalid_settings`.
- `GET /api/android/build` — Job-Status:
  `{jobId, state, running, log, apk, error}` (`state`: `idle|running|success|failed`).
- `POST /api/android/build` — starten; `202` mit `jobId`, `409 build_running`,
  `422 invalid_settings`.
- `GET /api/android/apk` — die APK herunterladen
  (`application/vnd.android.package-archive`); wenn kein Build vorhanden ist,
  die fertige APK aus der Distribution, andernfalls `404 apk_missing`.

### Statische Dateien und Dienstseiten

- `GET /` — Panel (`index.html`), `GET /editor.html` — Editor,
  `GET /android.html` — APK-Build, `GET /assist.html` — Assistent,
  `GET /login.html` — Anmeldung.
- `GET /license` — Lizenztext.
- `HEAD` — nur statische Dateien; für `/api/*` — `405`.
- `OPTIONS` — `204` ohne CORS-Header.

---

## 4. WebSocket `/ws`

Handshake — RFC 6455, Version 13. Nur Textnachrichten; Binärnachrichten werden
mit `1002` geschlossen.

### 4.1. Autorisierung

Das Token wird aus einem Cookie, `Authorization: Bearer` oder `?token=` (für
`/ws`) entnommen. Ohne gültige Sitzung — HTTP `401`, und das Upgrade wird nicht
durchgeführt. Ein einmaliges Pairing-Token ist hier nicht gültig: Es wird nur
über `/?pair=` akzeptiert. Wenn `Origin` und `Host` nicht übereinstimmen — HTTP
`403`, und das Upgrade wird nicht durchgeführt.

### 4.2. Server → Client

#### `hello` — erste Nachricht

```json
{
  "type": "hello",
  "clientId": "a1b2c3d4",
  "server": { "name": "Open Deck for MSFS", "version": "0.1.0",
              "telemetryHz": 30.0, "uptimeSec": 1.2 },
  "profiles": [ … ],
  "state": { /* full telemetry frame */ }
}
```

#### `telemetry` — periodisch (`telemetryHz`-mal pro Sekunde)

```json
{
  "type": "telemetry",
  "seq": 1234,
  "ts": 1762340000000,
  "sim": { "provider": "mock", "connected": true,
           "aircraftTitle": "…", "profileId": "…" },
  "values": { "speed.iasKt": 108.0, "altitude.indicatedFt": 4520.0, … }
}
```

- `seq` ist monoton — es zeigt Frame-Verluste an;
- `values` enthält immer alle Registerschlüssel. `null` bedeutet „keine Daten":
  Die SimVar wurde von SimConnect nicht akzeptiert oder die Telemetrie ist
  veraltet. Der Client zeigt einen Strich, statt Null einzusetzen.

#### `aircraft`

```json
{ "type": "aircraft", "profileId": "cessna-172-sixpack", "aircraftTitle": "…" }
```

Kommt nach einem Flugzeugwechsel/einer Autoerkennung, damit der Client die
Profile wechselt.

#### `ack`

```json
{ "type": "ack", "id": "c1", "key": "power.batteryMaster", "ok": true, "value": true }
{ "type": "ack", "id": "c1", "key": "…", "ok": false, "code": "not_writable", "error": "…" }
```

#### `pong`

Antwort auf `ping`: `{ "type": "pong", "t": <echo>, "ts": <unix ms> }`.

#### `error`

`{ "type": "error", "code": "bad_json"|"unknown_type", "error": "…" }`.

### 4.3. Client → Server

```json
{ "type": "ping", "t": 12345.6 }
{ "type": "command", "id": "c1", "key": "power.batteryMaster", "value": true }
```

`id` ist beliebig; der Server gibt sie im `ack` zurück.

### 4.4. `ack`-Codes

| `code` | Bedeutung |
| --- | --- |
| `invalid_key` | leerer/unbekannter Schlüssel |
| `not_writable` | schreibgeschützte Variable |
| `invalid_value` | Wert kann nicht in den Typ umgewandelt werden |
| `rate_limited` | mehr als 30 Befehle pro Sekunde von einem WebSocket-Client oder einer IP für REST |
| `sim_rejected` | der Simulator hat den Befehl abgewiesen |
| `sim_error` | interner Provider-Fehler |

### 4.5. Limits und Verhalten

- Maximale Nachrichtengröße — 256 KiB; größere — `1002`.
- Pro Client — eine Warteschlange von 8 Telemetrie-Frames; bei Überlauf werden
  die ältesten verworfen (ein langsamer Client bremst die anderen nicht).
- Steuerframes (ping/pong/close) werden nicht fragmentiert und sind ≤125 Byte.
- Lese-Idle-Timeout — 90 s; der Client sendet alle 20 s `ping`.
- Close: `1000` — normal, `1002` — Protokollverletzung.

### 4.6. Client-Empfehlungen

- Der visuelle Zustand kommt aus `telemetry.values`, nicht aus `ack`.
- Wiederverbinden mit Backoff (500 ms → 8 s, Jitter); wenn 45 s lang keine
  Nachrichten eintreffen — die Verbindung als „halb-offen" behandeln und neu
  verbinden.
- Die UI nicht blockieren: „Warten" anzeigen, bei `ok:false`/Timeout
  zurückrollen.

---

## 5. QR-Anmeldung (Pairing)

```
Phone (no session)                      Gateway
        │  GET /?pair=<one-time token>   │
        ├───────────────────────────────►│
        │                                │ token check (10 min, once)
        │  302 / + Set-Cookie open_deck_session  │
        │◄───────────────────────────────┤
        │  GET / (with cookie)           │
        └───────────────────────────────►│ panel
```

Der QR-Code wird vom Gateway selbst gezeichnet (`/api/qr.svg`); das Token wird
von `POST /api/pair` erstellt (Sitzung erforderlich). So meldet sich das
Smartphone ohne Passworteingabe an. Das Token ist einmalig und keine Sitzung:
Ein Versuch, es als Cookie oder Bearer-Token zu verwenden, liefert `401`, und
seine TTL wird nicht verlängert.

---

## 6. Autoerkennung (UDP-Broadcast)

Der Host sendet alle 3 Sekunden einen JSON-Beacon an UDP-Port `8761` (für
Android und native Clients; Browser unterstützen kein UDP).

```json
{
  "type": "open-deck-msfs",
  "protocol": 1,
  "name": "FLIGHTSIM-PC",
  "version": "0.1.0",
  "httpPort": 8760,
  "telemetryHz": 30.0,
  "profiles": ["cessna-172-skyhawk", "piper-pa28-archer-ii"],
  "auth": true,
  "ts": 1762340000
}
```

| Feld | Beschreibung |
| --- | --- |
| `type` | immer `open-deck-msfs` |
| `protocol` | Schemaversion des Beacons |
| `name` | Hostname |
| `httpPort` | HTTP/WebSocket-Port |
| `telemetryHz` | Telemetrierate |
| `profiles` | verfügbare Profile |
| `auth` | nur vorhanden, wenn ein Passwort aktiviert ist (`true`) |
| `ts` | Unix-Zeit |

Manuelle Prüfung:

```powershell
python -m msfs_gateway.discovery --listen
```

---

## 7. HTTP-Fehler

Format: `{"error": "text", "code": "machine_code"}`.

| Status | Typische Codes |
| --- | --- |
| `400` | `bad_request`, `bad_json`, `invalid_value`, `id_mismatch`, `missing_password` |
| `401` | `unauthorized`, `bad_password` |
| `404` | `not_found`, `apk_missing` |
| `409` | `build_running`, `sim_rejected`, Assistent-Abweisungen |
| `411` | `length_required` |
| `413` | `too_large` |
| `422` | `invalid_profile`, `invalid_settings`, `qr_too_long` |
| `429` | `rate_limited` |
| `501` | nicht unterstützte HTTP-Methode (stdlib) |

---

## 8. Beispiele

### Anmeldung und Profilanfrage

```bash
curl -c cookies.txt -H "Content-Type: application/json" \
     -d '{"password":"secret"}' http://127.0.0.1:8760/api/auth/login

curl -b cookies.txt http://127.0.0.1:8760/api/profiles
```

### Bearer statt Cookie

```bash
TOKEN=$(curl -s -H "Content-Type: application/json" \
  -d '{"password":"secret"}' http://127.0.0.1:8760/api/auth/login | jq -r .token)

curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8760/api/telemetry
```

### Befehl

```bash
curl -b cookies.txt -H "Content-Type: application/json" \
     -d '{"key":"power.batteryMaster","value":true}' \
     http://127.0.0.1:8760/api/sim/command
```

### WebSocket (Python, ohne Bibliotheken)

```python
import json, socket, base64, os
sock = socket.create_connection(("127.0.0.1", 8760))
key = base64.b64encode(os.urandom(16)).decode()
sock.sendall((
    "GET /ws HTTP/1.1\r\nHost: 127.0.0.1\r\nUpgrade: websocket\r\n"
    f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
    "Sec-WebSocket-Version: 13\r\n"
    "Cookie: open_deck_session=<token>\r\n\r\n"
).encode())
# dann RFC-6455-Frames lesen (siehe msfs_gateway/websocket.py)
```

---

## 9. Kompatibilität

- Profil-Schema — `schemaVersion: 1`; das alte `v0`-Format wird beim Lesen von
  `legacy.py` angepasst.
- Beacon — `protocol: 1`; Clients müssen neue optionale Felder (`auth`)
  ignorieren.
- Die API ist nicht in der URL versioniert: Breaking Changes nur in einer neuen
  Hauptversion des Gateways.
