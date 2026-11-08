# Open Deck for MSFS — service description

This document describes what the gateway does, what it consists of, how clients
interact with it, and how to enable password login. It is intended for pilots
who set up the panel "for themselves" and for developers who need to understand
the internal design.

- Version: 0.1.0
- Host platform: Windows 10/11
- Clients: browser (PC, phone, tablet), Android 8+
- License: [GNU AGPL-3.0](../LICENSE) + additional terms Section 7

## 1. Purpose

Open Deck for MSFS turns a phone or tablet into an instrument panel for Microsoft
Flight Simulator 2020/2024. The gateway runs on the same computer as the
simulator, reads telemetry through SimConnect, serves it over the local network,
and accepts commands (switches, rotary selectors, buttons). Panels are described
by aircraft JSON profiles and edited right in the browser.

Key properties:

- **Offline**: no external CDN, font, API, or telemetry. Everything
  works on an isolated network and on a machine without internet.
- **One port**: static files, REST, and WebSocket on a single TCP port (8760 by
  default) — a single firewall rule is enough.
- **No dependencies**: the host is Python 3.11+ and the standard library; the
  client is vanilla ES modules; Android is Kotlin without AndroidX.
- **Optional password**: access to the API and telemetry can be closed with a
  password of at least 6 characters, with sessions, QR login, and brute-force
  protection.

## 2. Operating model

```
┌──────────────────┐   SimConnect / WASM    ┌─────────────────────────────┐
│  MSFS 2020/2024  │◄──────────────────────►│ Open Deck for MSFS (Windows)│
│  aircraft, LVAR  │   SimVar, TITLE, ATC   │                             │
└──────────────────┘   Client Data Area     │  ┌───────────────────────┐  │
                                             │  │ SimProvider           │  │
┌──────────────────┐        HTTP/WS          │  │  auto / mock / simconn│  │
│  PC browser      │◄───────────────────────►│  └──────────┬────────────┘  │
│  panel, editor   │   8760, static + API    │             │               │
└──────────────────┘                         │  ┌──────────▼────────────┐  │
┌──────────────────┐        HTTP/WS          │  │ Hub: telemetry 30 Hz  │  │
│  Phone/tablet    │◄───────────────────────►│  │ commands, sessions    │  │
└──────────────────┘                         │  └──────────┬────────────┘  │
┌──────────────────┐   HTTP (WebView)        │             │               │
│  Android client  │◄───────────────────────►│  Profiles, integrity,     │
└──────────────────┘   UDP beacon 8761       │  authentication, APK      │
                                             └─────────────────────────────┘
```

Data flow:

1. The telemetry provider (`simconnect`, `mock`, or `auto`) reads variable
   values once per tick.
2. The bus (`Hub`) assembles a frame, adds service fields, and broadcasts it to
   all WebSocket clients at the configured rate (30 Hz by default, 60 maximum).
3. The client draws instruments; commands go back to the bus, are validated,
   and are applied by the provider.
4. When the aircraft changes, the gateway selects a matching profile by
   name/ATC model and notifies clients about it.

## 3. Components

| Component | Files | Responsibility |
| --- | --- | --- |
| Entry point | `msfs_gateway/app.py` | Dependency assembly, lifecycle, banner, `--set-password` / `--build-apk` modes |
| Settings | `msfs_gateway/settings.py` | CLI arguments, paths, defaults |
| HTTP/WebSocket | `msfs_gateway/http_api.py`, `websocket.py` | Static files, REST, RFC 6455 handshake and frames, authentication |
| Bus | `msfs_gateway/hub.py` | Telemetry frame, subscriptions, commands, command limiting, aircraft autodetection |
| Providers | `msfs_gateway/sim/` | `mock`, `simconnect`, Client Data Area, LVAR/RPN WASM bridge |
| Profiles | `msfs_gateway/profiles.py` | Reading/validation/atomic saving of JSON profiles |
| Telemetry | `msfs_gateway/telemetry.py` | Variable catalog, types, value coercion |
| Authentication | `msfs_gateway/auth.py` | PBKDF2 hash, sessions, QR tokens, attempt limiting |
| Autodiscovery | `msfs_gateway/discovery.py` | UDP beacon with name, version, and password flag |
| Integrity | `msfs_gateway/integrity.py` | SHA-256 of critical UI files |
| QR | `msfs_gateway/qr.py` | Built-in QR generator (SVG), no dependencies |
| APK build | `msfs_gateway/android_build.py` | Settings, JDK/SDK/Gradle lookup, Gradle launch, APK delivery |
| Assist | `msfs_gateway/assist.py` | Taxi (speed/heading) and landing (APR, retard, TOGA) loops |
| Documentation generator | `msfs_gateway/docsgen.py` | `docs/telemetry.md` and `docs/widgets.md` from code registries |
| Web client | `web/` | Panel, editor, login, assist, APK build page |
| Android | `android/` | WebView shell, UDP discovery, integrity check, login cookie |
| Build and checks | `scripts/`, `packaging/` | Installer, `check.ps1`, QR verification |

## 4. Telemetry

### 4.1. Frame

A frame is a JSON object that arrives over WebSocket immediately after
connection and then at the gateway's rate:

```json
{
  "type": "telemetry",
  "seq": 421,
  "ts": 1793541762842,
  "sim": {
    "provider": "simconnect",
    "connected": true,
    "aircraftTitle": "Cessna Skyhawk G1000 Asobo",
    "profileId": "cessna-172-g1000"
  },
  "values": {
    "attitude.pitchDeg": 2.4,
    "attitude.bankDeg": -6.1,
    "speed.iasKt": 108.2,
    "altitude.indicatedFt": 4520.0,
    "heading.magneticDeg": 274.0,
    "verticalSpeed.fpm": 120.0,
    "engine.rpm": 2380.0,
    "power.batteryMaster": true,
    "custom.lvar.apuBleed": 0.0
  }
}
```

`seq` grows monotonically, `ts` is Unix milliseconds. The client detects dropped
frames by `seq` and simply keeps drawing (this does not matter for needles).

### 4.2. Variables

The complete catalog with types, units, SimVars, and events is in
[telemetry.md](telemetry.md). Only the categories are listed below.

The variable catalog is the single source of truth (`telemetry.py`). Each entry
has a type (`number`, `bool`, `string`), a "commands accepted" flag, and a
description. The client can retrieve the catalog through
`GET /api/telemetry/variables`.

Categories:

- attitude, altitude, speed, heading, VSI;
- engine (RPM, manifold/torque, N1, ITT, fuel);
- electrical, flaps, autopilot;
- `custom.<...>` — LVAR/RPN from the active profile.

### 4.3. Providers

| Provider | When used | Features |
| --- | --- | --- |
| `simconnect` | real flight | `ctypes` + `SimConnect.dll`; string datums `TITLE`, `ATC MODEL`; Client Data Area for LVAR/RPN. If the standard `SimConnect.cfg` does not work, the gateway itself tries TCP `127.0.0.1:19999` (the MSFS 2020/2024 port) through a temporary config |
| `mock` | demo, development, tests | Procedural flight model, initial LVAR values from the profile |
| `auto` | default | Tries to connect SimConnect and falls back to mock on failure |

If the WASM module is not installed, the `custom.*` keys are simply absent and
the panel shows "--" — the rest of the telemetry keeps working. After two
consecutive timeouts, the Client Data circuit breaker pauses polling for 30
seconds so it does not block the telemetry broadcast thread.

### 4.4. Delivery and resilience

- Each WebSocket client has its own queue (8 frames) and sender thread:
  a slow tablet does not slow down the others, and old frames are dropped.
- Client reconnection uses exponential backoff; if no messages arrive for more
  than 45 seconds, the client considers the connection "half-open" and
  reconnects.
- A session may expire during flight — the client checks the status once a
  minute and redirects to the login page.

## 5. Aircraft profiles

A profile is a JSON file in `profiles/`. The detailed schema is in
[`profile-schema.md`](profile-schema.md). In brief:

```json
{
  "schemaVersion": 1,
  "id": "cessna-172-skyhawk",
  "name": "Cessna 172S Skyhawk",
  "icao": "C172",
  "revision": 3,
  "sim": { "match": { "title": "*Cessna*172*", "atcModel": "C172" } },
  "panel": { "background": "#0b1117", "gridSize": 8, "footer": "C172S" },
  "widgets": [
    {
      "id": "attitude",
      "type": "attitude",
      "label": "Attitude indicator",
      "bindings": { "pitch": "attitude.pitchDeg", "bank": "attitude.bankDeg" },
      "layout": {
        "base": { "x": 0.02, "y": 0.03, "w": 0.36, "h": 0.62 },
        "phone": { "x": 0.03, "y": 0.015, "w": 0.94, "h": 0.3 }
      }
    }
  ]
}
```

- `sim.match` — templates (glob) for the aircraft title and ATC model; the
  gateway switches the profile itself.
- `layout` — coordinates in panel fractions (0..1); `base` and the overrides
  `phone`, `tablet-sm`, `tablet-lg`.
- `revision` — grows on every save from the editor.
- Saving is atomic: temporary file → `fsync` → `os.replace`.

## 6. Clients

### 6.1. Web panel

- Three form factors with automatic selection by screen width; the manual
  choice is remembered.
- Instruments: attitude indicator, round gauges, readouts, switches, rotary
  selector, VSI, altimeter, heading indicator; animation through
  `requestAnimationFrame`.
- Comfort: brightness 100/72/45 % (`B`), kiosk mode (`F`, exit with `Esc`).
- The phone button shows a QR code for quick login.

### 6.2. Editor

`/editor.html`: drag-and-drop, resizing, 1 % grid, undo/redo, copying layouts
between form factors, saving to the host.

### 6.3. Android

WebView shell: finds the host via the UDP beacon or accepts a manual address,
checks the UI integrity, and opens the panel. If a password is enabled on the
gateway, the WebView shows the login page; the session is stored in a WebView
cookie and survives an app restart. Password-protected hosts are marked with a
lock.

### 6.4. Login page

`/login.html` is the only page available without login (along with its styling).
It shows a password field, errors, the author support block, and a "Log out"
button if a session is already active. The password is sent only to its own
gateway, over HTTP on the local network (see the "Security" section).

## 7. Network and connection

| What | Port | Protocol |
| --- | --- | --- |
| Static files, REST, WebSocket | 8760 (configurable via `--port`) | TCP/HTTP + WS |
| Autodiscovery | 8761 | UDP broadcast |

- The gateway listens on `0.0.0.0` and prints all its addresses at startup.
- Android finds the host via the beacon: PC name, version, profile count,
  password flag.
- The QR code on the panel contains the address and a one-time token: the phone
  logs in with a single scan, without entering a password (the token lives for
  10 minutes and is used once).
- Manual address entry: `192.168.1.10`, `192.168.1.10:8760`, or a full URL.

## 8. Password authentication

### 8.1. How to enable

Any of the following ways:

```powershell
# 1. Save the password to config/auth.json (persistently)
OpenDeck.exe --set-password
#    or without a prompt:
OpenDeck.exe --set-password "my-password"

# 2. Pass the password for this run only (not written to disk)
OpenDeck.exe --password "my-password"

# 3. Environment variable
$env:OPEN_DECK_PASSWORD = "my-password"
```

In the installed app there is a "Set password" shortcut in the Start menu for
this. The file `config/auth.json` stores **only the PBKDF2 hash** (random salt,
210,000 iterations); delete the file and login becomes free again. The
`--no-auth` flag ignores the file and the password (trusted network only).

The password from `--password` is not written to disk but is visible in the
process list (`Get-Process` / Task Manager). For permanent use, prefer
`--set-password`: it is hashed once in memory at startup.

The minimum password length is **6 characters**; limits: no more than 256
characters, no control characters, no leading or trailing spaces.

### 8.2. How login works

1. The client opens `/login.html` and enters the password.
2. `POST /api/auth/login` verifies the PBKDF2 hash; on success a session is
   created (32 random bytes, 12-hour TTL, extended on activity).
3. The server sets the `open_deck_session` cookie with `HttpOnly`, `SameSite=Lax` —
   JavaScript cannot see it, and the browser sends it automatically.
4. For native clients the JSON response returns a `token`; it can be passed as
   `Authorization: Bearer <token>` or `?token=` for WebSocket.
5. `POST /api/auth/logout` revokes the session and clears the cookie.

Only the following are publicly accessible:

| Path | Why |
| --- | --- |
| `/login.html`, `/js/login.js`, `/css/*`, `/img/*` | the login page and its styling |
| `/api/auth/status`, `/api/auth/login`, `/api/auth/logout` | login itself |
| `/api/health` | "is this the gateway?" check and the password flag |
| `/api/integrity` | UI integrity check (license condition) |
| `/api/donation` | author support block (license condition) |
| `/license` | license text |

Everything else — profiles, telemetry, commands, Android settings, APK build,
QR, `WS /ws` — requires a session. Pages without a session respond with a
redirect to `/login.html?next=…`.

### 8.3. Brute-force protection

- 5 failed attempts from one IP within 60 seconds → blocked for 60 seconds
  (response `429` with `Retry-After`).
- Hash comparison uses `hmac.compare_digest` (constant time).
- Failed attempts are logged with the address but without the password.

### 8.4. QR login from a phone

The "phone" button on the panel requests `POST /api/pair` (a session is
required). The gateway issues a one-time token for 10 minutes; the QR encodes
`http://<address>:<port>/?pair=<token>`. The phone opens the link, the gateway
exchanges the token for a regular session, sets the cookie, and redirects to `/`.
The pairing token itself is not a session: as a cookie or Bearer token it
returns `401`, so the link cannot be reused after the exchange.
Reusing the token is rejected.

## 9. Landing and taxi assist

The page `/assist.html` and the API `/api/assist*` add two auxiliary loops.
This is **not a certified autopilot**: the pilot controls the flight and can
disable the assist at any time.

### 9.1. Taxi

- Enabled only on the ground, with the parking brake released and speed below
  35 kt.
- Holds the target ground speed (3–25 kt) with a PI throttle controller and the
  heading with a P rudder controller; the pilot changes heading with the
  ±1°/±5° buttons.
- "STOP": throttle 0, rudder 0, parking brake.
- Automatically disengages if the aircraft lifts off, the parking brake is
  engaged, or the speed exceeds 35 kt.

### 9.2. Landing

- ARM: enables `AP_MASTER` and `AP_APR_HOLD` (ILS approach). Requires a speed
  of at least 40 kt and the aircraft in the air.
- At 60–15 ft radio altitude the assist linearly reduces throttle from 45 % to 0.
- On touchdown: throttle 0, autopilot off; after slowing below 5 kt —
  "rollout complete".
- TOGA: full throttle, AP and APR off (go-around).
- The assist does not touch the elevator: the approach and flare remain with the
  autopilot/pilot.

State and setpoints: `GET /api/assist`; actions — `POST /api/assist/taxi`
(`engage`, `disengage`, `stop`, `speed`, `heading`) and `POST /api/assist/landing`
(`arm`, `disarm`, `toga`). All requests require a session.

## 10. API

Base URL: `http://<host>:<port>`. All responses are JSON; errors have the form
`{"error": "…", "code": "…"}`.

| Method | Path | Access | Description |
| --- | --- | --- | --- |
| GET | `/api/health` | public | Status, version, rate, password flag |
| GET | `/api/auth/status` | public | `{required, authenticated}` |
| POST | `/api/auth/login` | public | `{password}` → session + cookie |
| POST | `/api/auth/logout` | public | Revoke the current session |
| POST | `/api/pair` | session required | One-time QR token |
| GET | `/api/profiles` | session required | Profile list |
| GET | `/api/profiles/{id}` | session required | Full profile |
| PUT | `/api/profiles/{id}` | session required | Save a profile (id in body = id in URL) |
| GET | `/api/telemetry` | session required | Latest frame |
| GET | `/api/telemetry/variables` | session required | Variable catalog |
| POST | `/api/sim/command` | session required | `{key, value}` → confirmation |
| POST | `/api/sim/aircraft` | session required | `{profileId}` — manual aircraft selection |
| GET | `/api/integrity` | public | SHA-256 check result |
| GET | `/api/donation` | public | Author support details |
| GET | `/api/connect` | session required | Gateway addresses for QR/hints |
| GET | `/api/qr.svg?text=…` | session required | SVG with a QR code |
| GET/PUT | `/api/android/settings` | session required | APK build settings |
| GET/POST | `/api/android/build` | session required | Start/status of the APK build |
| GET | `/api/android/apk` | session required | Download the APK |
| GET | `/api/assist` | session required | Assist state and telemetry |
| POST | `/api/assist/taxi` | session required | Taxi assist control |
| POST | `/api/assist/landing` | session required | ARM / DISARM / TOGA |
| WS | `/ws` | session required | Telemetry and commands |

Login and request example:

```bash
curl -c cookies.txt -H "Content-Type: application/json" \
     -d '{"password":"my-password"}' http://127.0.0.1:8760/api/auth/login

curl -b cookies.txt http://127.0.0.1:8760/api/profiles
```

Command:

```json
{"type": "command", "id": "c17", "key": "power.batteryMaster", "value": true}
```

Response: `{"type": "ack", "id": "c17", "ok": true, "value": true}` or `ok:false`
with an error code. Commands are limited to ~20 per second per client.

## 11. Installation and startup

### 11.1. Windows installer

`OpenDeck-Setup-<version>.exe` — per-user installation without administrator
rights, Python not required. Shortcuts are created for: starting the gateway,
the panel in the browser, the APK build page, "Set password", and uninstall.

### 11.2. From source

```powershell
python -m msfs_gateway --sim auto          # real flight
python -m msfs_gateway --sim mock          # demo without the simulator
python -m msfs_gateway --password "secret123"
```

| Parameter | Default | Purpose |
| --- | --- | --- |
| `--host` / `--port` | `0.0.0.0` / `8760` | address and port |
| `--allow-host NAME` | — | additional DNS name for Host (if the panel is opened by name) |
| `--sim` | `auto` | `auto`, `mock`, `simconnect` |
| `--telemetry-hz` | `30` | frame rate, 1..60 |
| `--simconnect-dll` | auto-detect | path to `SimConnect.dll` |
| `--simconnect-host` | `127.0.0.1` | SimConnect address (remote simulator) |
| `--simconnect-port` | `19999` | SimConnect TCP port |
| `--profile-dir` | `profiles/` | profile directory |
| `--password` | — | password for this run |
| `--set-password [PWD]` | — | save the hash and exit |
| `--auth-file` | `config/auth.json` | hash file |
| `--web-dir` / `--profile-dir` | `web/` / `profiles/` | static and profile directories |
| `--donation-config` | `config/donation.json` | author support details |
| `--log-level` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `--discovery-port` / `--discovery-interval` | `8761` / `3` | UDP beacon: port and period |
| `--no-auth` | — | ignore the password |
| `--no-wasm` | — | no LVAR/RPN |
| `--no-discovery` | — | no UDP beacon |
| `--build-apk [CONFIG]` | — | build the APK and exit |

### 11.3. Android APK

The installation contains the Android sources; the ready APK is built to
`android/dist/OpenDeck-Android-<version>.apk`. The page `/android.html` (login
required) lets you change the name, package id, version, and default gateway
address and build the APK in place. JDK 17, Android SDK, and Gradle 8.x are
required; in the release distribution the APK is already attached.

## 12. Diagnostics

| Symptom | What to check |
| --- | --- |
| The panel does not open from the phone | same Wi-Fi, the address from the banner, Windows firewall (port 8760), `--host 0.0.0.0` |
| "Password login required" | a password is set; enter it on `/login.html`; the QR token lives for 10 minutes |
| "Incorrect password" | keyboard layout/case; reset: delete `config/auth.json` or use `--no-auth` |
| Instruments show "--" | no SimConnect/WASM, mock selected, aircraft has no profile, the simulator is still in the main menu |
| The profile does not switch | `sim.match` does not match the name/model; select it manually |
| The APK build does not start | JDK/SDK/Gradle not found; specify the paths on `/android.html` |
| "Integrity violated" | critical files were modified; `python -m msfs_gateway.integrity --write` |
| `SimConnect_Open … 0x80004005` | the gateway itself tries TCP `127.0.0.1:19999`; if that did not help — check `%APPDATA%\Microsoft Flight Simulator\SimConnect.cfg` (it overrides the settings) and that a flight is loaded; for a remote simulator set `--simconnect-host/--simconnect-port` |

Logs: the gateway console (`--log-level DEBUG`), the browser's "Network" tab,
and `adb logcat` for Android (tag `OpenDeckDiscovery`).

## 13. Security

- The password protects the API and telemetry from a "Wi-Fi neighbor", but
  **traffic goes over HTTP without TLS**. In a trusted home network this is
  acceptable; for guest networks, use a separate VLAN or a reverse proxy with
  TLS.
- The session cookie is `HttpOnly` + `SameSite=Lax`; the CSRF risk is reduced.
  URL tokens are used only for WebSocket (`?token=`) and the one-time QR
  (`?pair=`). The QR token is accepted only through `/?pair=` and is not a
  session.
- `Origin` checking for browser POST/PUT and WebSocket: a request with a foreign
  `Origin` receives `403`; clients without `Origin` are allowed.
- `Host` checking against local names/IPs: an unknown Host receives `403`
  (protection against DNS rebinding).
- Login attempts are limited to 5 per minute per address.
- CORS is intentionally disabled: a third-party page cannot read API responses.
- If no password is set, the gateway explicitly warns in the console that the
  panel and commands are available to everyone on the local network.
- The UDP beacon is unsigned: any host on the network can impersonate the
  gateway. Do not expose the gateway to the internet.
- Android: WebView navigation allow-list, access to `file:`/`content:` is
  forbidden, mixed content is forbidden.

## 14. Limitations

- A live run of SimConnect/WASM requires MSFS to be installed; in the repository
  the logic is verified by emulation.
- The APK is signed with a debug key; release signing is not automated yet.
- No mDNS: only the UDP beacon.
- One active gateway per port; profiles are files, without a database.

## 15. Glossary

| Term | Meaning |
| --- | --- |
| **Gateway** | The process on the PC with the simulator: reads telemetry and serves it to clients |
| **Host** | The machine where the gateway runs (in the Android client — the discovered PC) |
| **Profile** | A JSON file with instruments and layouts for a specific aircraft |
| **Instrument / widget** | A panel element: attitude indicator, gauge, switch, etc. |
| **Form factor** | A screen class: `phone`, `tablet-sm`, `tablet-lg` |
| **Aircraft** | A specific aircraft in the simulator; the profile is selected by `TITLE`/`ATC MODEL` |
| **Telemetry** | The stream of SimVar and `custom.*` values in a JSON frame |
| **Frame** | A single `telemetry` message with `seq`, `ts`, `sim`, `values` |
| **LVAR** | A local aircraft variable (PMDG, Fenix, FBW, etc.) |
| **RPN** | Reverse Polish notation — a script for computing a value in MSFS |
| **WASM bridge** | LVAR/RPN exchange through the Client Data Area of the MobiFlight/SimBridge module |
| **Client Data Area** | A named SimConnect area for exchanging data blocks |
| **AP / APR / AT** | Autopilot / ILS approach mode / autothrottle |
| **Retard** | Smooth throttle reduction during the flare (landing assist) |
| **TOGA** | Take Off / Go Around: full throttle and go-around |
| **Pairing** | Login from a phone using a one-time QR token |
| **Session** | An active login: a token in a cookie/Bearer, TTL 12 hours |
| **Integrity** | Comparison of the SHA-256 of critical UI files with the manifest |
| **Air-gapped** | A network without internet access; all resources are local |

## 16. Feedback and support

- **Author:** Viktor Krasnikov — [github.com/meferspb/open-deck](https://github.com/meferspb/open-deck).
- **Donat:** [https://taps.uz/open_deck_fs](https://taps.uz/open_deck_fs).
- Bugs and suggestions — through GitHub issue templates (see `.github/`).
- Vulnerabilities — privately, according to [SECURITY.md](../SECURITY.md).
- Setup questions — Discussions (if enabled) or an issue using the
  "Bug" template.
- License and the mandatory author support block — [LICENSE](../LICENSE).

## 17. License

[GNU Affero General Public License v3.0](../LICENSE) and
[additional terms Section 7](../COPYING.ADDITIONAL): the source code is open,
modifications are distributed under AGPL; the author support block and integrity
checking are mandatory and cannot be removed.
