# 🔌 Open Deck for MSFS Network Protocol

All communication goes over a single TCP port (`8760` by default):

- **HTTP static files** — files from `web/` (panel, editor, login, assist);
- **REST API** — profiles, telemetry, commands, assist, APK build;
- **WebSocket `/ws`** — telemetry stream and command acknowledgements.

## 0. Conventions

- Base URL: `http://<host>:<port>`; all paths are relative.
- JSON is UTF-8, `Content-Type: application/json; charset=utf-8`.
- API responses: `Cache-Control: no-store`; static files: `no-cache`.
- **CORS is intentionally disabled**: the API is designed for same-origin
  clients, and a third-party page cannot read the responses.
- **Same-origin protection**: if the browser sends `Origin`, its host and
  effective port must match `Host`. Otherwise `POST`/`PUT` and WebSocket
  requests receive `403` `origin_not_allowed`. Clients without `Origin`
  (Android, curl) are allowed.
- **Host allowlist**: `Host` must point to localhost, the machine name, FQDN,
  a local IP, or a name from `--allow-host`; otherwise `403 host_not_allowed`.
  This is protection against DNS rebinding.
- Request body limit — **2 MiB**; unknown `Content-Length` → `411`.
- The password (if enabled) and sessions are described in section 2.
- The protocol version in the autodiscovery beacon is `protocol: 1`.

---

## 1. Access: public and under a session

If no password is configured, everything is available. If one is configured,
only the login page, its files, and the service data required by the license are
open without a session:

| Path | Access | Purpose |
| --- | --- | --- |
| `/login.html`, `/js/login.js`, `/css/*`, `/img/*` | public | login page and styling |
| `/api/auth/status`, `/api/auth/login`, `/api/auth/logout` | public | login/logout |
| `/api/health` | public | "is this the gateway?", version, password flag |
| `/api/integrity` | public | UI SHA-256 check |
| `/api/donation` | public | author support block |
| `/license` | public | license text |
| everything else | session required | profiles, telemetry, commands, QR, APK, assist, `/ws` |

Without a session:

- the API responds with `401` and `{"error","code":"unauthorized"}`, plus
  `WWW-Authenticate: Bearer realm="open-deck"`;
- HTML pages respond with `302` to `/login.html?next=<path>`;
- the WebSocket handshake is rejected with `401` (the browser will show a
  connection error).

---

## 2. Authentication

The password is at least 6 characters and is stored as a PBKDF2 hash in
`config/auth.json` (210,000 iterations, random salt). A session is 32 random
bytes with a 12-hour TTL, extended on access.

The token is accepted in three ways:

| Method | Where | For whom |
| --- | --- | --- |
| Cookie `open_deck_session` | `HttpOnly; SameSite=Lax` | browser and Android WebView |
| `Authorization: Bearer <token>` | header | native clients |
| `?token=<token>` | `/ws` only | WebSocket without a cookie |

### `GET /api/auth/status`

```json
{ "required": true, "authenticated": false }
```

### `POST /api/auth/login`

```json
{ "password": "secret" }
```

Success — `200`, cookie, and token:

```json
{ "ok": true, "required": true, "token": "<43 characters>", "expiresIn": 43200 }
```

Errors:

| Status | `code` | When |
| --- | --- | --- |
| `400` | `missing_password` | no `password` |
| `401` | `bad_password` | incorrect password |
| `429` | `rate_limited` | after 5 failures from an address; includes `Retry-After` |

If no password is configured, the response is `{"ok":true,"required":false}`.

### `POST /api/auth/logout`

Revokes the current session and clears the cookie: `{"ok": true}`.

### `POST /api/pair`

Session required. One-time token for login from a phone:

```json
{ "url": "http://192.168.1.10:8760/?pair=…", "token": "…", "expiresIn": 600, "required": true }
```

Following `url` exchanges the token for a regular session (cookie) and redirects
to `/`; reusing it returns `/login.html?error=pair`.

---

## 3. REST API

Below, `{id}` is a profile identifier (`[a-z0-9][a-z0-9-]{1,63}`).

### `GET /api/health`

```json
{
  "status": "ok",
  "version": "0.1.0",
  "uptimeSec": 42.1,
  "clients": 1,
  "telemetryHz": 30.0,
  "profileId": "cessna-172-g1000",
  "authRequired": true,
  "sim": {
    "provider": "simconnect",
    "connected": true,
    "aircraftTitle": "Cessna Skyhawk G1000 Asobo",
    "profileId": "cessna-172-g1000"
  },
  "wasm": {
    "enabled": true,
    "available": true,
    "state": "connected",
    "lastError": null
  }
}
```

### `GET /api/diagnostics`

Session required. Returns recent SimConnect exceptions (`simconnect`),
WASM transport/probe status (`wasm`), and the current health snapshot
(`health`). Useful for diagnosing `NAME_UNRECOGNIZED` and Client Data timeouts.

### `GET /api/profiles`

```json
{ "profiles": [
  { "id": "cessna-172-skyhawk", "name": "Cessna 172S Skyhawk", "icao": "C172",
    "revision": 3, "widgetCount": 11 }
] }
```

### `GET /api/profiles/{id}`

The full profile (see [profile-schema.md](profile-schema.md)).
`404 not_found` — no file; `422 invalid_profile` — validation failed.

### `PUT /api/profiles/{id}`

The body is a complete JSON profile; the `id` in the body must match the URL
(`400 id_mismatch`). Response `{"ok": true, "profile": {…}}`.

### `GET /api/telemetry`

The latest frame (the same format as `telemetry` over WebSocket).
`seq` grows; `values` contains all registry keys.

### `GET /api/telemetry/variables`

Variable catalog:

```json
{ "variables": [
  { "key": "speed.iasKt", "label": "Indicated airspeed", "kind": "number",
    "unit": "KT", "writable": false, "simVar": "AIRSPEED INDICATED", "simEvent": null }
] }
```

The complete human-readable catalog is in [telemetry.md](telemetry.md).

### `GET /api/integrity`

```json
{ "verified": true, "checkedAt": "2026-11-01T…", "manifestPresent": true,
  "files": { "web/index.html": "<sha256>" }, "errors": [] }
```

### `GET /api/donation`

Author support details from `config/donation.json` (the only source is the host
configuration). Author — Viktor Krasnikov, Donat —
[`https://taps.uz/open_deck_fs`](https://taps.uz/open_deck_fs).

### `GET /api/connect`

Addresses for phone/tablet:

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

Sorting: `192.168.*`, then `10.*`, `172.16–31.*`, link-local, loopback.

### `GET /api/qr.svg?text=…&scale=6&border=4`

An SVG with a QR code (up to 512 characters; generated on the host, without
libraries). `400 missing_text` — no `text`; `400` (`code` = `error`) —
`scale`/`border` are not numbers; `422 qr_too_long` — the text does not fit into
the supported QR versions.

### `POST /api/sim/command`

```json
{ "key": "power.batteryMaster", "value": true }
```

Success — `200` with `{"type":"ack","id":…,"key":…,"ok":true,"value":…}`.
Errors: `400` with `code` = `invalid_key`, `not_writable`, `invalid_value`,
`rate_limited`, or `sim_error`; `409 sim_rejected` — the simulator rejected it.
For variables with a parameter event, the value is scaled
(percent → 0..16383).

### `POST /api/sim/aircraft`

```json
{ "profileId": "cessna-172-sixpack" }
```

Response: `{"ok": true, "profileId": "…", "aircraftTitle": "…", "pinned": false}`.
`pinned: true` — the provider cannot switch aircraft (SimConnect), so the
selection is pinned until the aircraft changes in the simulator. `404` — no such
profile.

### Assist

`GET /api/assist` — loop state:

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

| `action` | Fields | Meaning |
| --- | --- | --- |
| `engage` | — | enable speed/heading hold (ground only) |
| `disengage` | — | disable |
| `stop` | — | throttle 0, parking brake |
| `speed` | `value` (3…25) | set the taxi speed |
| `heading` | `delta` (±) | turn the target heading |

`POST /api/assist/landing`: `action` = `arm` (AP + APR), `disarm`, `toga`.

Response: `{"ok": true|false, "message": "…", "status": {…}}`.
`200` — action performed; `409` — rejected (not on the ground, speed too low,
no connection to MSFS, unknown action).

### Android APK build

- `GET /api/android/settings` — `{settings, toolchain, apk, prebuiltApk}`.
- `PUT /api/android/settings` — save settings (name, package id, version,
  gateway address, tool paths). `422 invalid_settings`.
- `GET /api/android/build` — job status:
  `{jobId, state, running, log, apk, error}` (`state`: `idle|running|success|failed`).
- `POST /api/android/build` — start; `202` with `jobId`, `409 build_running`,
  `422 invalid_settings`.
- `GET /api/android/apk` — download the APK (`application/vnd.android.package-archive`);
  if there is no build, the ready APK from the distribution, otherwise
  `404 apk_missing`.

### Static files and service pages

- `GET /` — panel (`index.html`), `GET /editor.html` — editor,
  `GET /android.html` — APK build, `GET /assist.html` — assist,
  `GET /login.html` — login.
- `GET /license` — license text.
- `HEAD` — static files only; for `/api/*` — `405`.
- `OPTIONS` — `204` without CORS headers.

---

## 4. WebSocket `/ws`

Handshake — RFC 6455, version 13. Text messages only; binary messages are
closed with `1002`.

### 4.1. Authorization

The token is taken from a cookie, `Authorization: Bearer`, or `?token=` (for
`/ws`). Without a valid session — HTTP `401`, and the upgrade is not performed.
A one-time pairing token is not valid here: it is accepted only through
`/?pair=`. If `Origin` and `Host` do not match — HTTP `403`, and the upgrade is
not performed.

### 4.2. Server → client

#### `hello` — first message

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

#### `telemetry` — periodically (`telemetryHz` times per second)

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

- `seq` is monotonic — it reveals frame loss;
- `values` always contains all registry keys. `null` means "no data":
  the SimVar was not accepted by SimConnect or the telemetry is stale. The client
  shows a dash rather than substituting zero.

#### `aircraft`

```json
{ "type": "aircraft", "profileId": "cessna-172-sixpack", "aircraftTitle": "…" }
```

Arrives after an aircraft change/autodetection so the client switches profiles.

#### `ack`

```json
{ "type": "ack", "id": "c1", "key": "power.batteryMaster", "ok": true, "value": true }
{ "type": "ack", "id": "c1", "key": "…", "ok": false, "code": "not_writable", "error": "…" }
```

#### `pong`

Response to `ping`: `{ "type": "pong", "t": <echo>, "ts": <unix ms> }`.

#### `error`

`{ "type": "error", "code": "bad_json"|"unknown_type", "error": "…" }`.

### 4.3. Client → server

```json
{ "type": "ping", "t": 12345.6 }
{ "type": "command", "id": "c1", "key": "power.batteryMaster", "value": true }
```

`id` is arbitrary; the server returns it in the `ack`.

### 4.4. `ack` codes

| `code` | Meaning |
| --- | --- |
| `invalid_key` | empty/unknown key |
| `not_writable` | read-only variable |
| `invalid_value` | value cannot be coerced to the type |
| `rate_limited` | more than 30 commands per second from a WebSocket client or IP for REST |
| `sim_rejected` | the simulator rejected the command |
| `sim_error` | internal provider error |

### 4.5. Limits and behavior

- Maximum message size — 256 KiB; larger — `1002`.
- Per client — a queue of 8 telemetry frames; on overflow the oldest are
  dropped (a slow client does not slow down the others).
- Control frames (ping/pong/close) are not fragmented and are ≤125 bytes.
- Read idle timeout — 90 s; the client sends `ping` every 20 s.
- Close: `1000` — normal, `1002` — protocol violation.

### 4.6. Client recommendations

- Visual state comes from `telemetry.values`, not from `ack`.
- Reconnect with backoff (500 ms → 8 s, jitter); if no messages arrive for 45 s —
  treat the connection as "half-open" and reconnect.
- Do not block the UI: show "waiting", roll back on `ok:false`/timeout.

---

## 5. QR login (pairing)

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

The QR code is drawn by the gateway itself (`/api/qr.svg`); the token is created
by `POST /api/pair` (session required). This way the phone logs in without
entering a password. The token is one-time and is not a session: an attempt to
use it as a cookie or Bearer token returns `401`, and its TTL is not extended.

---

## 6. Autodiscovery (UDP broadcast)

The host sends a JSON beacon to UDP port `8761` every 3 seconds (for Android and
native clients; browsers do not support UDP).

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

| Field | Description |
| --- | --- |
| `type` | always `open-deck-msfs` |
| `protocol` | beacon schema version |
| `name` | host name |
| `httpPort` | HTTP/WebSocket port |
| `telemetryHz` | telemetry rate |
| `profiles` | available profiles |
| `auth` | present only when a password is enabled (`true`) |
| `ts` | Unix time |

Manual check:

```powershell
python -m msfs_gateway.discovery --listen
```

---

## 7. HTTP errors

Format: `{"error": "text", "code": "machine_code"}`.

| Status | Typical codes |
| --- | --- |
| `400` | `bad_request`, `bad_json`, `invalid_value`, `id_mismatch`, `missing_password` |
| `401` | `unauthorized`, `bad_password` |
| `404` | `not_found`, `apk_missing` |
| `409` | `build_running`, `sim_rejected`, assist rejections |
| `411` | `length_required` |
| `413` | `too_large` |
| `422` | `invalid_profile`, `invalid_settings`, `qr_too_long` |
| `429` | `rate_limited` |
| `501` | unsupported HTTP method (stdlib) |

---

## 8. Examples

### Login and profile request

```bash
curl -c cookies.txt -H "Content-Type: application/json" \
     -d '{"password":"secret"}' http://127.0.0.1:8760/api/auth/login

curl -b cookies.txt http://127.0.0.1:8760/api/profiles
```

### Bearer instead of a cookie

```bash
TOKEN=$(curl -s -H "Content-Type: application/json" \
  -d '{"password":"secret"}' http://127.0.0.1:8760/api/auth/login | jq -r .token)

curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8760/api/telemetry
```

### Command

```bash
curl -b cookies.txt -H "Content-Type: application/json" \
     -d '{"key":"power.batteryMaster","value":true}' \
     http://127.0.0.1:8760/api/sim/command
```

### WebSocket (Python, no libraries)

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
# then read RFC 6455 frames (see msfs_gateway/websocket.py)
```

---

## 9. Compatibility

- Profile schema — `schemaVersion: 1`; the old `v0` format is adapted by
  `legacy.py` on read.
- Beacon — `protocol: 1`; clients must ignore new optional fields (`auth`).
- The API is not versioned in the URL: breaking changes only in a new major
  gateway version.
